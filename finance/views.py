from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from .models import FinancialRecord, Category, FinancialRecordType
from .serializers import FinancialRecordSerializer, CategorySerializer, FinancialRecordTypeSerializer


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
        qs = FinancialRecord.objects.filter(user=self.request.user).select_related(
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
class FinanceCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.select_related("record_type").all()
    serializer_class = CategorySerializer
    permission_classes = []

    def get_queryset(self):
        qs = super().get_queryset()
        record_type_id = self.request.query_params.get("record_type_id")
        if record_type_id:
            qs = qs.filter(record_type_id=record_type_id)
        return qs


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
