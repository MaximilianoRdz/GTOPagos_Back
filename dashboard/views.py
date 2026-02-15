from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import date, timedelta
from django.db.models import Sum
from .models import UserFinanceDashboard
from finance.models import FinancialRecord
from .serializers import DashboardSerializer, FinancialRecordLiteSerializer


class CurrentDashboardView(APIView):
    permission_classes = [IsAuthenticated]

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
