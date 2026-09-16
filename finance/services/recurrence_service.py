import calendar
from datetime import date
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from payments.models import PaymentStatus
from finance.models import FinancialRecord


def get_next_month_date(base_date: date) -> date:
    """Calcula la fecha exacta para el mes siguiente ajustando días de fin de mes."""
    year = base_date.year + (base_date.month // 12)
    month = (base_date.month % 12) + 1
    day = min(base_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def spawn_next_recurrent_instance(record: FinancialRecord) -> FinancialRecord | None:
    """
    Crea la instancia del siguiente mes para un gasto/ingreso recurrente.
    Se ejecuta al marcar el pago como pagado o al sincronizar períodos.
    """
    if not record.is_recurrent or not record.is_active:
        return None

    # Las compras a meses sin intereses (total_installments > 1) ya tienen sus cuotas pre-generadas
    if record.total_installments and record.total_installments > 1:
        return None

    desc_clean = record.description.strip()

    # Verificar si el registro más reciente general fue cancelado o eliminado
    latest_overall = FinancialRecord.objects.filter(
        user=record.user,
        dashboard=record.dashboard,
        description__iexact=desc_clean,
        category=record.category,
        record_type=record.record_type,
    ).order_by('-record_date', '-id').first()

    if latest_overall and (not latest_overall.is_active or not latest_overall.is_recurrent):
        return None

    next_date = get_next_month_date(record.record_date)

    # Verificar si ya existe cualquier registro (activo o inactivo) para ese mes/año
    already_exists = FinancialRecord.objects.filter(
        user=record.user,
        dashboard=record.dashboard,
        description__iexact=desc_clean,
        category=record.category,
        record_type=record.record_type,
        record_date__year=next_date.year,
        record_date__month=next_date.month,
    ).exists()

    if already_exists:
        return None

    pending_status = PaymentStatus.objects.filter(code__iexact='pending').first()

    with transaction.atomic():
        new_record = FinancialRecord.objects.create(
            user=record.user,
            dashboard=record.dashboard,
            category=record.category,
            record_type=record.record_type,
            amount=record.amount,
            description=record.description,
            record_date=next_date,
            payment_status=pending_status,
            payment_method=record.payment_method,
            is_recurrent=True,
            created_by=record.user,
            is_active=True,
            total_installments=1,
            current_installment=1,
        )
        return new_record


def sync_recurrent_records_for_user(user, target_date: date = None, dashboard_id: int = None):
    """
    Verifica que todos los movimientos recurrentes activos tengan su registro correspondiente
    hasta el mes objetivo (por defecto hoy). Si falta alguno, lo autogenera como pendiente.
    """
    if not user or not user.is_authenticated:
        return

    if target_date is None:
        target_date = timezone.now().date()

    # Obtener todos los registros recurrentes activos
    qs = FinancialRecord.objects.filter(
        user=user,
        is_recurrent=True,
        is_active=True,
        dashboard__is_active=True,
    ).filter(
        Q(total_installments__isnull=True) | Q(total_installments__lte=1)
    ).select_related(
        'dashboard', 'category', 'record_type', 'payment_status', 'payment_method'
    ).order_by('record_date')

    if dashboard_id:
        qs = qs.filter(dashboard_id=dashboard_id)

    # Agrupar por serie recurrente única (dashboard, descripción, categoría, record_type)
    series_map = {}
    for r in qs:
        key = (r.dashboard_id, r.description.strip().lower(), r.category_id, r.record_type_id)
        # Guardamos el más reciente de cada serie
        if key not in series_map or r.record_date > series_map[key].record_date:
            series_map[key] = r

    pending_status = PaymentStatus.objects.filter(code__iexact='pending').first()

    # Para cada serie, avanzar mes a mes hasta cubrir el target_date
    for key, latest_record in series_map.items():
        desc_clean = latest_record.description.strip()

        # Verificar si el registro global más reciente de esta serie fue desactivado o cancelado
        latest_overall = FinancialRecord.objects.filter(
            user=user,
            dashboard_id=latest_record.dashboard_id,
            description__iexact=desc_clean,
            category_id=latest_record.category_id,
            record_type_id=latest_record.record_type_id,
        ).order_by('-record_date', '-id').first()

        if latest_overall and (not latest_overall.is_active or not latest_overall.is_recurrent):
            # La serie fue cancelada o eliminada por el usuario, desactivar recurrencia anterior
            FinancialRecord.objects.filter(
                user=user,
                dashboard_id=latest_record.dashboard_id,
                description__iexact=desc_clean,
                category_id=latest_record.category_id,
                record_type_id=latest_record.record_type_id,
                is_recurrent=True,
            ).update(is_recurrent=False)
            continue

        curr_record = latest_record

        # Avanzar mientras la fecha sea anterior al mes/año del target_date
        while (curr_record.record_date.year < target_date.year) or (
            curr_record.record_date.year == target_date.year
            and curr_record.record_date.month < target_date.month
        ):
            next_date = get_next_month_date(curr_record.record_date)

            # Buscar cualquier registro existente (activo o inactivo) para esa serie en ese mes/año
            existing = FinancialRecord.objects.filter(
                user=user,
                dashboard=curr_record.dashboard,
                description__iexact=desc_clean,
                category=curr_record.category,
                record_type=curr_record.record_type,
                record_date__year=next_date.year,
                record_date__month=next_date.month,
            ).first()

            if existing:
                # Si existe pero está inactivo o ya no es recurrente, el usuario canceló/eliminó ese mes
                if not existing.is_active or not existing.is_recurrent:
                    break
                curr_record = existing
            else:
                curr_record = FinancialRecord.objects.create(
                    user=user,
                    dashboard=curr_record.dashboard,
                    category=curr_record.category,
                    record_type=curr_record.record_type,
                    amount=curr_record.amount,
                    description=curr_record.description,
                    record_date=next_date,
                    payment_status=pending_status,
                    payment_method=curr_record.payment_method,
                    is_recurrent=True,
                    created_by=user,
                    is_active=True,
                    total_installments=1,
                    current_installment=1,
                )

        # Si el registro del mes objetivo ya fue pagado, autogenerar el del siguiente mes
        if curr_record.payment_status and curr_record.payment_status.code.lower() == 'paid':
            spawn_next_recurrent_instance(curr_record)
