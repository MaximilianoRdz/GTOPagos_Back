from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status
from django.utils import timezone
from datetime import date, timedelta
from django.db.models import Sum
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import UserFinanceDashboard
from finance.models import FinancialRecord
from .serializers import DashboardSerializer, FinancialRecordLiteSerializer, DashboardBasicSerializer
from finance.serializers import FinancialRecordSerializer


class CurrentDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="dashboard_current",
        description="Get current period dashboard summary (income, expenses, balance, and pending records) for the authenticated user.",
        parameters=[
            OpenApiParameter(
                name="period",
                type=str,
                required=False,
                description="Period type: 'month' (default) or 'year'.",
            ),
        ],
        responses={200: DashboardSerializer},
    )
    def _period_range(self, today, period_type):
        if period_type == "year":
            start = date(today.year, 1, 1)
            end = date(today.year + 1, 1, 1)
        else:
            start = date(today.year, today.month, 1)
            if today.month == 12:
                end = date(today.year + 1, 1, 1)
            else:
                end = date(today.year, today.month + 1, 1)
        return start, end

    def _classify_totals(self, qs):
        total_income = 0
        total_expense = 0
        data = qs.values("record_type__name").annotate(total=Sum("amount"))
        for row in data:
            name = (row["record_type__name"] or "").lower()
            if any(k in name for k in ["income", "ingres", "percep"]):
                total_income += row["total"] or 0
            elif any(k in name for k in ["expense", "egres", "deduc"]):
                total_expense += row["total"] or 0
        return total_income, total_expense

    def get(self, request):
        user = request.user
        period_type = request.query_params.get("period", "month")
        today = timezone.now().date()
        start, end = self._period_range(today, period_type)

        dash, _ = UserFinanceDashboard.objects.get_or_create(
            user=user, period_type=period_type, period_start=start
        )

        qs = FinancialRecord.objects.select_related("payment_status", "record_type", "category").filter(
            user=user, record_date__gte=start, record_date__lt=end
        )

        pend = qs.filter(payment_status__status__iregex=r"(pend|pending|pendiente)")
        total_income, total_expense = self._classify_totals(qs)

        dash.total_income = total_income
        dash.total_expense = total_expense
        dash.save()

        payload = {
            "period_type": dash.period_type,
            "period_start": dash.period_start,
            "total_income": dash.total_income,
            "total_expense": dash.total_expense,
            "balance": dash.balance,
            "pending_to_pay": FinancialRecordLiteSerializer(pend, many=True).data,
        }
        return Response(payload)


class DashboardViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DashboardBasicSerializer

    def get_queryset(self):
        return UserFinanceDashboard.objects.filter(user=self.request.user).order_by("-updated_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(
                {"detail": "Cannot delete dashboard with linked financial records."},
                status=status.HTTP_409_CONFLICT
            )


class DashboardRecordsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="dashboard_records_list",
        description="List financial records (with metadata) for a given dashboard belonging to the authenticated user.",
        responses={200: FinancialRecordSerializer},
    )
    def get(self, request, pk):
        dashboard = get_object_or_404(
            UserFinanceDashboard.objects.filter(user=request.user),
            pk=pk,
        )
        records = FinancialRecord.objects.filter(dashboard=dashboard).select_related(
            "record_type",
            "category",
            "payment_method",
            "payment_status",
        )
        serializer = FinancialRecordSerializer(records, many=True, context={"request": request})
        return Response(serializer.data)
