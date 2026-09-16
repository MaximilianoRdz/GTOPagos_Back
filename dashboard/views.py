from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status, generics
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from datetime import date, timedelta
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import UserFinanceDashboard
from finance.models import FinancialRecord
from .serializers import CurrentPeriodSummarySerializer, DashboardSerializer, FinancialRecordLiteSerializer
from finance.serializers import FinancialRecordSerializer
from finance.services.recurrence_service import sync_recurrent_records_for_user
from .selectors.dashboard_selectors import (
    get_dashboard_current_summary,
    get_user_dashboards_with_aggregations,
    calculate_period_date_range,
)


class CurrentDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="dashboard_current",
        description="Get current period dashboard summary (income, expenses, balance, and pending records) for the authenticated user.",
        parameters=[
            OpenApiParameter(
                name="dashboard_id",
                type=int,
                required=True,
                description="ID of the dashboard to filter by.",
            ),
            OpenApiParameter(
                name="period",
                type=str,
                required=False,
                description="Period type: 'month' (default) or 'year'.",
            ),
        ],
        responses={200: CurrentPeriodSummarySerializer},
    )
    def get(self, request):
        dashboard_id = request.query_params.get("dashboard_id")

        if not dashboard_id:
            return Response({"detail": "dashboard_id es requerido."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            dashboard_id = int(dashboard_id)
        except ValueError:
            return Response({"detail": "dashboard_id inválido."}, status=status.HTTP_400_BAD_REQUEST)

        dashboard = get_object_or_404(UserFinanceDashboard, user=request.user, is_active=True, pk=dashboard_id)
        period_type = request.query_params.get("period", "month")

        payload = get_dashboard_current_summary(request.user, dashboard, period_type)
        return Response(payload)


class DashboardViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DashboardSerializer

    def get_queryset(self):
        return get_user_dashboards_with_aggregations(self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        # Cascade soft delete to financial records
        instance.financial_records.filter(is_active=True).update(is_active=False)
        return Response(status=status.HTTP_204_NO_CONTENT)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class DashboardRecordsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FinancialRecordSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        operation_id="dashboard_records_list",
        description="List financial records (with metadata) for a given dashboard belonging to the authenticated user.",
        responses={200: FinancialRecordSerializer},
    )
    def get_queryset(self):
        dashboard_id = self.kwargs.get('pk')
        dashboard = get_object_or_404(
            UserFinanceDashboard.objects.filter(user=self.request.user, is_active=True),
            pk=dashboard_id,
        )
        
        period_type = self.request.query_params.get("period", "month")
        today = timezone.now().date()

        sync_recurrent_records_for_user(self.request.user, target_date=today, dashboard_id=dashboard.id)
        start, end = calculate_period_date_range(today, period_type)
            
        return FinancialRecord.objects.filter(
            dashboard=dashboard, 
            is_active=True,
            record_date__gte=start,
            record_date__lt=end
        ).select_related(
            "record_type",
            "category",
            "payment_method",
            "payment_status",
        )

class GlobalRecentTransactionsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FinancialRecordSerializer
    
    @extend_schema(
        operation_id="global_recent_transactions",
        description="List recent financial records across all active dashboards for the user.",
        responses={200: FinancialRecordSerializer(many=True)},
    )
    def get_queryset(self):
        return FinancialRecord.objects.filter(
            dashboard__user=self.request.user,
            dashboard__is_active=True,
            is_active=True
        ).select_related(
            "record_type",
            "category",
            "payment_method",
            "payment_status",
        ).order_by("-record_date", "-created_at")[:5]


class UpcomingDuePaymentsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="upcoming_due_payments",
        description="List upcoming pending expense records due within 7 days or already overdue for the user.",
    )
    def get(self, request):
        today = timezone.now().date()
        sync_recurrent_records_for_user(request.user, target_date=today)

        due_threshold = today + timedelta(days=7)
        records = FinancialRecord.objects.filter(
            dashboard__user=request.user,
            dashboard__is_active=True,
            is_active=True,
            payment_status__code__iexact="pending",
            record_type__behavior="EXPENSE",
            record_date__lte=due_threshold
        ).select_related(
            "dashboard",
            "record_type",
            "category",
            "payment_method",
            "payment_status",
        ).order_by("record_date", "created_at")

        serializer = FinancialRecordSerializer(records, many=True)
        return Response({
            "count": records.count(),
            "records": serializer.data
        })

