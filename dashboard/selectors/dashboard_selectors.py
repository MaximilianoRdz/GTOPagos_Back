from datetime import date
from django.utils import timezone
from django.db.models import Sum, Count, Case, When, DecimalField
from finance.models import FinancialRecord
from dashboard.serializers import FinancialRecordLiteSerializer


def calculate_period_date_range(today: date, period_type: str = "month") -> tuple[date, date]:
    """Calcula las fechas de inicio y fin para un tipo de período (month, q1, q2, year)."""
    if period_type == "year":
        start = date(today.year, 1, 1)
        end = date(today.year + 1, 1, 1)
    elif period_type == "q1":
        start = date(today.year, today.month, 1)
        end = date(today.year, today.month, 16)
    elif period_type == "q2":
        start = date(today.year, today.month, 16)
        if today.month == 12:
            end = date(today.year + 1, 1, 1)
        else:
            end = date(today.year, today.month + 1, 1)
    else:  # month por defecto
        start = date(today.year, today.month, 1)
        if today.month == 12:
            end = date(today.year + 1, 1, 1)
        else:
            end = date(today.year, today.month + 1, 1)
    return start, end


def build_behavior_financial_summary(qs, behavior: str) -> dict:
    """Agrega totales, conteos y desglose por categoría para un comportamiento (INCOME o EXPENSE)."""
    base_qs = qs.filter(record_type__behavior=behavior)

    totals = base_qs.aggregate(
        total_amount=Sum('amount'),
        total_records=Count('id'),
        paid_amount=Sum(
            Case(When(payment_status__code__iexact='paid', then='amount'), default=0, output_field=DecimalField())
        ),
        paid_records=Count(Case(When(payment_status__code__iexact='paid', then=1))),
        pending_amount=Sum(
            Case(When(payment_status__code__iexact='pending', then='amount'), default=0, output_field=DecimalField())
        ),
        pending_records=Count(Case(When(payment_status__code__iexact='pending', then=1))),
    )

    categories_data = base_qs.values('category__name').annotate(
        total_amount=Sum('amount'),
        total_records=Count('id'),
        paid_records=Count(Case(When(payment_status__code__iexact='paid', then=1))),
        pending_amount=Sum(
            Case(When(payment_status__code__iexact='pending', then='amount'), default=0, output_field=DecimalField())
        )
    ).order_by('-total_amount')

    categories = [
        {
            "name": cat['category__name'] or "Sin Categoría",
            "total_amount": cat['total_amount'] or 0,
            "total_records": cat['total_records'] or 0,
            "paid_records": cat['paid_records'] or 0,
            "pending_amount": cat['pending_amount'] or 0
        }
        for cat in categories_data
    ]

    return {
        "total_amount": totals['total_amount'] or 0,
        "total_records": totals['total_records'] or 0,
        "paid_amount": totals['paid_amount'] or 0,
        "paid_records": totals['paid_records'] or 0,
        "pending_amount": totals['pending_amount'] or 0,
        "pending_records": totals['pending_records'] or 0,
        "categories": categories
    }


def get_dashboard_current_summary(user, dashboard, period_type: str = "month") -> dict:
    """Construye el resumen financiero completo para el dashboard del usuario en el período indicado."""
    today = timezone.now().date()
    start, end = calculate_period_date_range(today, period_type)

    # Sincronizar recurrencias activas
    from finance.services.recurrence_service import sync_recurrent_records_for_user
    sync_recurrent_records_for_user(user, target_date=today, dashboard_id=dashboard.id)

    qs = FinancialRecord.objects.select_related("payment_status", "record_type", "category").filter(
        user=user,
        dashboard=dashboard,
        dashboard__is_active=True,
        record_date__gte=start,
        record_date__lt=end,
        is_active=True,
    )

    pend = qs.filter(payment_status__code__iexact="pending")
    expense_summary = build_behavior_financial_summary(qs, 'EXPENSE')
    income_summary = build_behavior_financial_summary(qs, 'INCOME')

    total_income = income_summary['total_amount']
    total_expense = expense_summary['total_amount']

    return {
        "period_type": period_type,
        "period_start": start,
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": total_income - total_expense,
        "expense_summary": expense_summary,
        "income_summary": income_summary,
        "pending_to_pay": FinancialRecordLiteSerializer(pend, many=True).data,
    }


def get_user_dashboards_with_aggregations(user):
    """Retorna los dashboards activos del usuario anotados con conteo de movimientos e ingresos/gastos del mes actual."""
    from dashboard.models import UserFinanceDashboard
    from django.db.models import Q

    today = timezone.now().date()
    start = date(today.year, today.month, 1)
    if today.month == 12:
        end = date(today.year + 1, 1, 1)
    else:
        end = date(today.year, today.month + 1, 1)

    month_active_filter = Q(
        financial_records__is_active=True,
        financial_records__record_date__gte=start,
        financial_records__record_date__lt=end,
    )

    return UserFinanceDashboard.objects.filter(user=user, is_active=True).annotate(
        records_count=Count('financial_records', filter=month_active_filter, distinct=True),
        total_income=Sum(
            Case(
                When(
                    month_active_filter & Q(financial_records__record_type__behavior='INCOME'),
                    then='financial_records__amount'
                ),
                default=0,
                output_field=DecimalField()
            )
        ),
        total_expense=Sum(
            Case(
                When(
                    month_active_filter & Q(financial_records__record_type__behavior='EXPENSE'),
                    then='financial_records__amount'
                ),
                default=0,
                output_field=DecimalField()
            )
        )
    ).order_by("-updated_at")
