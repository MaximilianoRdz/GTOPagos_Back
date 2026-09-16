from io import BytesIO
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import viewsets, status, serializers
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, inline_serializer

from dashboard.models import UserFinanceDashboard
from .models import FinancialRecord, Category, FinancialRecordType, CategoryKeyword, FinancialGoal
from .serializers import (
    FinancialRecordSerializer,
    CategorySerializer,
    FinancialRecordTypeSerializer,
    FinancialGoalSerializer,
)
from .selectors.report_selectors import get_report_records, calculate_report_summary
from .services.category_detector_service import detect_category_from_description
from .services.import_engine import ImportEngine
from .services.recurrence_service import spawn_next_recurrent_instance
from .services.report_export_service import (
    generate_dashboard_excel_export,
    generate_report_excel_export,
    generate_report_pdf_export,
)


@extend_schema_view(
    list=extend_schema(
        operation_id="list_financial_records",
        description="List financial records for the authenticated user. Optionally filter by dashboard_id.",
        parameters=[
            OpenApiParameter(
                name="dashboard_id",
                type=int,
                required=False,
                description="Filter records by dashboard id",
            ),
        ],
        responses={200: FinancialRecordSerializer},
    ),
    retrieve=extend_schema(
        operation_id="retrieve_financial_record",
        description="Retrieve a single financial record with its metadata.",
        responses={200: FinancialRecordSerializer},
    ),
    create=extend_schema(
        operation_id="create_financial_record",
        description="Create a financial record with optional metadata for the authenticated user.",
        request=FinancialRecordSerializer,
        responses={201: FinancialRecordSerializer},
    ),
    update=extend_schema(
        operation_id="update_financial_record",
        description="Update a financial record and its metadata.",
        request=FinancialRecordSerializer,
        responses={200: FinancialRecordSerializer},
    ),
    partial_update=extend_schema(
        operation_id="partial_update_financial_record",
        description="Partially update a financial record and/or its metadata.",
        request=FinancialRecordSerializer,
        responses={200: FinancialRecordSerializer},
    ),
    destroy=extend_schema(
        operation_id="delete_financial_record",
        description="Delete a financial record and its metadata.",
    ),
)
class FinancialRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FinancialRecordSerializer

    def get_queryset(self):
        qs = FinancialRecord.objects.filter(user=self.request.user, is_active=True, dashboard__is_active=True).select_related(
            "dashboard",
            "record_type",
            "category",
            "payment_method",
            "payment_status",
        )
        dashboard_id = self.request.query_params.get("dashboard_id")
        if dashboard_id:
            qs = qs.filter(dashboard_id=dashboard_id)
        return qs.order_by("-record_date", "-created_at")

    def perform_update(self, serializer):
        old_instance = self.get_object()
        was_recurrent = old_instance.is_recurrent
        instance = serializer.save()

        # Si el usuario desmarcó la recurrencia, desactivarla en toda la serie para evitar zombis
        if was_recurrent and not instance.is_recurrent:
            FinancialRecord.objects.filter(
                user=self.request.user,
                dashboard=instance.dashboard,
                description__iexact=instance.description.strip(),
                category=instance.category,
                record_type=instance.record_type,
                is_recurrent=True,
            ).update(is_recurrent=False)
            return

        if instance.is_recurrent and instance.payment_status and instance.payment_status.code.lower() == 'paid':
            spawn_next_recurrent_instance(instance)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()

        # Si era un registro recurrente, desactivar recurrencia en la serie para que no reviva
        if instance.is_recurrent:
            FinancialRecord.objects.filter(
                user=self.request.user,
                dashboard=instance.dashboard,
                description__iexact=instance.description.strip(),
                category=instance.category,
                record_type=instance.record_type,
                is_recurrent=True,
            ).update(is_recurrent=False)

        return Response(status=status.HTTP_204_NO_CONTENT)

@extend_schema_view(
    list=extend_schema(
        operation_id="list_finance_categories",
        description="List finance categories. Optionally filter by record_type_id.",
        parameters=[
            OpenApiParameter(
                name="record_type_id",
                type=int,
                required=False,
                description="Filter categories by financial record type id",
            ),
        ],
        responses={200: CategorySerializer},
    ),
    retrieve=extend_schema(
        operation_id="retrieve_finance_category",
        description="Retrieve a single finance category.",
        responses={200: CategorySerializer},
    ),
)
class FinanceCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return []
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user if self.request.user.is_authenticated else None
        if user:
            qs = Category.objects.filter(Q(user=user) | Q(user__isnull=True))
        else:
            qs = Category.objects.filter(user__isnull=True)

        record_type_id = self.request.query_params.get("record_type_id")
        if record_type_id:
            qs = qs.filter(record_type_id=record_type_id)
        return qs.select_related("record_type").prefetch_related("keywords").order_by("name")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        if instance.user is None or instance.user != self.request.user:
            raise serializers.ValidationError({"detail": "No puedes eliminar una categoría predeterminada del sistema."})
        instance.delete()

    def perform_update(self, serializer):
        if serializer.instance.user is None or serializer.instance.user != self.request.user:
            raise serializers.ValidationError({"detail": "No puedes modificar una categoría predeterminada del sistema."})
        serializer.save()


@extend_schema_view(
    list=extend_schema(
        operation_id="list_financial_record_types",
        description="List all financial record types.",
        responses={200: FinancialRecordTypeSerializer},
    ),
    retrieve=extend_schema(
        operation_id="retrieve_financial_record_type",
        description="Retrieve a single financial record type.",
        responses={200: FinancialRecordTypeSerializer},
    ),
)
class FinancialRecordTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FinancialRecordType.objects.all().order_by("name")
    serializer_class = FinancialRecordTypeSerializer
    permission_classes = []


class DetectCategoryView(APIView):
    permission_classes = []

    @extend_schema(
        operation_id="detect_category",
        description="Detect category from a transaction description using keywords.",
        request=inline_serializer(
            name="DetectCategoryRequest",
            fields={"description": serializers.CharField()}
        ),
        responses={
            200: inline_serializer(
                name="DetectCategoryResponse",
                fields={
                    "category": inline_serializer(
                        name="DetectedCategoryDetail",
                        fields={
                            "id": serializers.IntegerField(),
                            "name": serializers.CharField()
                        },
                        allow_null=True
                    ),
                    "confidence": serializers.FloatField()
                }
            )
        }
    )
    def post(self, request, *args, **kwargs):
        description = request.data.get("description", "")
        matched_category, confidence = detect_category_from_description(description)

        if matched_category:
            return Response({
                "category": {
                    "id": matched_category.id,
                    "name": matched_category.name
                },
                "confidence": confidence
            }, status=status.HTTP_200_OK)

        return Response({
            "category": None,
            "confidence": 0.0
        }, status=status.HTTP_200_OK)


class ImportPreviewView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    @extend_schema(
        operation_id="import_preview",
        description="Parse an Excel/CSV file and return a preview of the records.",
        responses={200: inline_serializer(
            name="ImportPreviewResponse",
            fields={
                "records": serializers.ListField()
            }
        )}
    )
    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        dashboard_id = request.data.get('dashboard_id')
        
        if not file_obj:
            return Response({"detail": "File is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            dashboard_id = int(dashboard_id) if dashboard_id else None
            records = ImportEngine.parse_file(file_obj, request.user.id, dashboard_id)
            return Response({"records": records}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"Server error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ImportConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="import_confirm",
        description="Bulk insert confirmed records.",
        request=inline_serializer(
            name="ImportConfirmRequest",
            fields={
                "dashboard_id": serializers.IntegerField(),
                "records": serializers.ListField()
            }
        ),
        responses={201: inline_serializer(name="ConfirmResponse", fields={"inserted": serializers.IntegerField()})}
    )
    def post(self, request, *args, **kwargs):
        dashboard_id = request.data.get('dashboard_id')
        records = request.data.get('records', [])
        
        if not dashboard_id or not records:
            return Response({"detail": "dashboard_id and records are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Basic validations
        from dashboard.models import UserFinanceDashboard
        try:
            dashboard = UserFinanceDashboard.objects.get(id=dashboard_id, user=request.user, is_active=True)
        except UserFinanceDashboard.DoesNotExist:
            return Response({"detail": "Dashboard not found or not active."}, status=status.HTTP_404_NOT_FOUND)

        expense_type = FinancialRecordType.objects.get(behavior='EXPENSE')
        income_type = FinancialRecordType.objects.get(behavior='INCOME')

        objs = []
        seen_in_batch = set()
        
        for r in records:
            cat_id = r.get('category_id')
            behavior = r.get('behavior')
            amount = r.get('amount')
            desc = r.get('description')
            rec_date = r.get('record_date')
            is_recurrent = r.get('is_recurrent', False)
            occurrences = r.get('occurrences', 1)
            
            # Double check against DB and current batch
            batch_key = (rec_date, amount, desc)
            if batch_key in seen_in_batch:
                continue
            
            is_dup = ImportEngine.check_duplicate(request.user.id, dashboard.id, rec_date, amount, desc)
            if is_dup:
                continue
                
            seen_in_batch.add(batch_key)
            
            rt = expense_type if behavior == 'EXPENSE' else income_type
            
            # Simple fallback
            cat = Category.objects.filter(id=cat_id).first() if cat_id else None
            
            objs.append(FinancialRecord(
                user=request.user,
                dashboard=dashboard,
                record_type=rt,
                category=cat,
                amount=amount,
                description=desc,
                record_date=rec_date,
                is_recurrent=is_recurrent,
                total_installments=r.get('total_installments'),
                current_installment=r.get('current_installment'),
                created_by=request.user
            ))
            
        with transaction.atomic():
            FinancialRecord.objects.bulk_create(objs)

        return Response({"inserted": len(objs)}, status=status.HTTP_201_CREATED)

class ExportDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="export_dashboard",
        description="Export dashboard records to Excel.",
        parameters=[
            OpenApiParameter(name="dashboard_id", type=int, required=True)
        ],
        responses={200: bytes}
    )
    def get(self, request, *args, **kwargs):
        dashboard_id = request.query_params.get('dashboard_id')
        if not dashboard_id:
            return Response({"detail": "dashboard_id required"}, status=status.HTTP_400_BAD_REQUEST)

        records = FinancialRecord.objects.filter(
            user=request.user,
            dashboard_id=dashboard_id,
            is_active=True
        ).select_related('category', 'record_type').order_by('-record_date')

        excel_bytes = generate_dashboard_excel_export(records)

        response = HttpResponse(
            excel_bytes,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="movimientos.xlsx"'
        return response

class FinancialGoalViewSet(viewsets.ModelViewSet):
    serializer_class = FinancialGoalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FinancialGoal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ReportDataView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="report_data", responses={200: dict})
    def get(self, request, *args, **kwargs):
        dashboard_id = request.query_params.get('dashboard_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not dashboard_id:
            return Response({"detail": "dashboard_id required"}, status=status.HTTP_400_BAD_REQUEST)

        records = get_report_records(request.user, dashboard_id, start_date, end_date)
        summary = calculate_report_summary(records)
        serializer = FinancialRecordSerializer(records, many=True)

        return Response({
            "summary": summary,
            "records": serializer.data
        })


class ReportDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="report_download", responses={200: bytes})
    def get(self, request, *args, **kwargs):
        dashboard_id = request.query_params.get('dashboard_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        export_format = request.query_params.get('export_format', 'pdf')

        if not dashboard_id:
            return Response({"detail": "dashboard_id required"}, status=status.HTTP_400_BAD_REQUEST)

        records = get_report_records(request.user, dashboard_id, start_date, end_date)

        if export_format == 'excel':
            excel_bytes = generate_report_excel_export(records)
            response = HttpResponse(
                excel_bytes,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="reporte.xlsx"'
            return response

        elif export_format == 'pdf':
            dashboard = UserFinanceDashboard.objects.filter(pk=dashboard_id, user=request.user).first()
            dashboard_name = dashboard.name if dashboard else "General"
            user_name = request.user.get_full_name() or request.user.get_short_name() or request.user.email

            pdf_bytes = generate_report_pdf_export(
                records=records,
                dashboard_name=dashboard_name,
                user_name=user_name,
                start_date=start_date,
                end_date=end_date
            )
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="reporte_financiero_{dashboard_name.lower().replace(" ", "_")}.pdf"'
            return response

        return Response({"detail": "Invalid format"}, status=status.HTTP_400_BAD_REQUEST)

