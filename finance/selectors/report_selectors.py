from finance.models import FinancialRecord


def get_report_records(user, dashboard_id: int, start_date: str = None, end_date: str = None):
    """Obtiene el conjunto de registros filtrados para el reporte financiero."""
    qs = FinancialRecord.objects.filter(
        user=user,
        dashboard_id=dashboard_id,
        is_active=True
    ).select_related('category', 'record_type')

    if start_date:
        qs = qs.filter(record_date__gte=start_date)
    if end_date:
        qs = qs.filter(record_date__lte=end_date)

    return qs.order_by('-record_date', '-created_at')


def calculate_report_summary(records) -> dict:
    """Calcula total_income, total_expense y balance neto a partir de una lista o queryset de registros."""
    total_income = sum(r.amount for r in records if r.record_type.behavior == 'INCOME')
    total_expense = sum(r.amount for r in records if r.record_type.behavior == 'EXPENSE')
    balance = total_income - total_expense

    return {
        "total_income": float(total_income),
        "total_expense": float(total_expense),
        "balance": float(balance)
    }
