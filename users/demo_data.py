from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from users.models import User, UserProfile, Currency, IncomeFrequency
from dashboard.models import UserFinanceDashboard
from payments.models import PaymentMethod, PaymentStatus
from finance.models import FinancialRecord, FinancialRecordType, Category, FinancialGoal


DEMO_EMAIL = "demo@gtopagos.com"


def ensure_demo_user_and_data():
    """
    Garantiza la existencia del usuario demo@gtopagos.com y puebla sus datos
    (dashboards, metas, transacciones y MSI) con fechas dinámicas relativas a hoy.
    """
    today = timezone.now().date()

    # 1. Moneda y Frecuencia
    currency_mxn = Currency.objects.filter(code="MXN").first()
    if not currency_mxn:
        currency_mxn = Currency.objects.create(code="MXN", name="Peso Mexicano", symbol="$", sort_order=1)

    freq_monthly = IncomeFrequency.objects.filter(name__icontains="Mensual").first()
    if not freq_monthly:
        freq_monthly = IncomeFrequency.objects.filter(is_active=True).first()

    # 2. Usuario Demo
    user, created = User.objects.get_or_create(
        email=DEMO_EMAIL,
        defaults={
            "is_active": True,
        }
    )
    if created or not user.has_usable_password():
        user.set_password("DemoUser2026!")
        user.save()

    # 3. Perfil de Usuario Demo
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.first_name = "Invitado"
    profile.last_name = "Demo"
    profile.phone = "4771234567"
    profile.salary = Decimal("38500.00")
    profile.currency = currency_mxn
    if freq_monthly:
        profile.income_frequency = freq_monthly
    profile.notification_method = "email"
    profile.budget_alerts = True
    profile.goal_reminders = True
    profile.weekly_reports = False
    profile.monthly_reports = True
    profile.transaction_alerts = True
    profile.payment_reminders = True
    profile.save()

    # 4. Métodos de Pago
    pm_credito, _ = PaymentMethod.objects.get_or_create(name="Tarjeta de Crédito", defaults={"description": "Crédito bancario"})
    pm_debito, _ = PaymentMethod.objects.get_or_create(name="Tarjeta de Débito", defaults={"description": "Débito bancario"})
    pm_spei, _ = PaymentMethod.objects.get_or_create(name="Transferencia", defaults={"description": "Transferencia SPEI"})
    pm_efectivo, _ = PaymentMethod.objects.get_or_create(name="Efectivo", defaults={"description": "Pago en efectivo"})

    # 5. Estados de Pago
    status_paid = PaymentStatus.objects.filter(code="paid").first()
    if not status_paid:
        status_paid = PaymentStatus.objects.filter(status__icontains="pagado").first()
    if not status_paid:
        status_paid, _ = PaymentStatus.objects.get_or_create(status="Pagado", defaults={"code": "paid", "color": "#10B981"})

    status_pending = PaymentStatus.objects.filter(code="pending").first()
    if not status_pending:
        status_pending = PaymentStatus.objects.filter(status__icontains="pendiente").first()
    if not status_pending:
        status_pending, _ = PaymentStatus.objects.get_or_create(status="Pendiente", defaults={"code": "pending", "color": "#F59E0B"})

    # 6. Tipos de Registro
    record_type_expense = FinancialRecordType.objects.filter(behavior="EXPENSE").first()
    if not record_type_expense:
        record_type_expense, _ = FinancialRecordType.objects.get_or_create(name="Gasto", defaults={"behavior": "EXPENSE"})

    record_type_income = FinancialRecordType.objects.filter(behavior="INCOME").first()
    if not record_type_income:
        record_type_income, _ = FinancialRecordType.objects.get_or_create(name="Ingreso", defaults={"behavior": "INCOME"})

    # 7. Categorías
    def get_or_create_cat(name, rtype, color="#059669", icon="DollarSign"):
        cat = Category.objects.filter(name__iexact=name, record_type=rtype).first()
        if not cat:
            cat = Category.objects.create(name=name, record_type=rtype, color=color, icon=icon)
        return cat

    cat_comida = get_or_create_cat("Comida", record_type_expense, "#F97316", "Utensils")
    cat_servicios = get_or_create_cat("Servicios", record_type_expense, "#06B6D4", "Zap")
    cat_internet = get_or_create_cat("Internet", record_type_expense, "#3B82F6", "Wifi")
    cat_gasolina = get_or_create_cat("Gasolina", record_type_expense, "#EF4444", "Fuel")
    cat_streaming = get_or_create_cat("Streaming", record_type_expense, "#8B5CF6", "Tv")
    cat_entretenimiento = get_or_create_cat("Entretenimiento", record_type_expense, "#EC4899", "Film")
    cat_salud = get_or_create_cat("Salud", record_type_expense, "#10B981", "HeartPulse")

    cat_nomina = get_or_create_cat("Nómina", record_type_income, "#10B981", "Briefcase")
    cat_freelance = get_or_create_cat("Freelance", record_type_income, "#06B6D4", "Laptop")
    cat_bonos = get_or_create_cat("Bonos", record_type_income, "#F59E0B", "Award")

    # 8. Dashboards / Cuentas
    dash_bbva, _ = UserFinanceDashboard.objects.get_or_create(
        user=user,
        name="Tarjeta BBVA Oro",
        defaults={
            "description": "Tarjeta principal para compras y Meses Sin Intereses",
            "monthly_budget": Decimal("15000.00"),
            "dashboard_type": "BOTH",
            "currency": currency_mxn,
            "is_active": True,
        }
    )
    if not dash_bbva.is_active or dash_bbva.monthly_budget != Decimal("15000.00"):
        dash_bbva.is_active = True
        dash_bbva.monthly_budget = Decimal("15000.00")
        dash_bbva.save()

    dash_santander, _ = UserFinanceDashboard.objects.get_or_create(
        user=user,
        name="Cuenta Santander Nómina",
        defaults={
            "description": "Depósito de nómina y pago de servicios fijos",
            "monthly_budget": Decimal("30000.00"),
            "dashboard_type": "BOTH",
            "currency": currency_mxn,
            "is_active": True,
        }
    )
    if not dash_santander.is_active:
        dash_santander.is_active = True
        dash_santander.save()

    dash_efectivo, _ = UserFinanceDashboard.objects.get_or_create(
        user=user,
        name="Efectivo / Caja Chica",
        defaults={
            "description": "Gastos menores diarios y propinas",
            "monthly_budget": Decimal("3500.00"),
            "dashboard_type": "EXPENSES",
            "currency": currency_mxn,
            "is_active": True,
        }
    )
    if not dash_efectivo.is_active:
        dash_efectivo.is_active = True
        dash_efectivo.save()

    # 9. Metas de Ahorro
    goals_data = [
        ("Fondo de Emergencia (6 Meses)", Decimal("60000.00"), Decimal("35000.00"), today + timedelta(days=120)),
        ("Vacaciones a Cancún", Decimal("25000.00"), Decimal("18500.00"), today + timedelta(days=75)),
        ("Upgrade Setup Home Office", Decimal("15000.00"), Decimal("6000.00"), today + timedelta(days=180)),
    ]
    for g_name, g_target, g_saved, g_date in goals_data:
        goal, _ = FinancialGoal.objects.get_or_create(
            user=user,
            name=g_name,
            defaults={
                "target_amount": g_target,
                "saved_amount": g_saved,
                "target_date": g_date,
            }
        )
        goal.target_amount = g_target
        goal.saved_amount = g_saved
        goal.target_date = g_date
        goal.save()

    # 10. Transacciones Financieras:
    current_month_records = FinancialRecord.objects.filter(
        user=user,
        is_active=True,
        record_date__year=today.year,
        record_date__month=today.month,
    ).count()

    if current_month_records < 8:
        # Limpiar registros previos del usuario demo para refrescar con fechas actuales
        FinancialRecord.objects.filter(user=user).delete()

        records_to_create = [
            # Ingresos
            FinancialRecord(
                user=user,
                dashboard=dash_santander,
                record_type=record_type_income,
                category=cat_nomina,
                payment_method=pm_spei,
                payment_status=status_paid,
                amount=Decimal("19250.00"),
                description="Pago de Nómina Quincenal",
                record_date=today - timedelta(days=2),
                is_recurrent=True,
                is_active=True,
                created_by=user,
            ),
            FinancialRecord(
                user=user,
                dashboard=dash_santander,
                record_type=record_type_income,
                category=cat_freelance,
                payment_method=pm_spei,
                payment_status=status_paid,
                amount=Decimal("6500.00"),
                description="Proyecto UI/UX Dashboard",
                record_date=today - timedelta(days=8),
                is_recurrent=False,
                is_active=True,
                created_by=user,
            ),
            # Gastos Contado BBVA
            FinancialRecord(
                user=user,
                dashboard=dash_bbva,
                record_type=record_type_expense,
                category=cat_comida,
                payment_method=pm_credito,
                payment_status=status_paid,
                amount=Decimal("3450.00"),
                description="Despensa Mensual (Costco & Soriana)",
                record_date=today - timedelta(days=1),
                is_recurrent=False,
                is_active=True,
                created_by=user,
            ),
            FinancialRecord(
                user=user,
                dashboard=dash_bbva,
                record_type=record_type_expense,
                category=cat_gasolina,
                payment_method=pm_credito,
                payment_status=status_paid,
                amount=Decimal("950.00"),
                description="Gasolina Premium Mobil",
                record_date=today - timedelta(days=4),
                is_recurrent=False,
                is_active=True,
                created_by=user,
            ),
            # Gastos Santander
            FinancialRecord(
                user=user,
                dashboard=dash_santander,
                record_type=record_type_expense,
                category=cat_comida,
                payment_method=pm_debito,
                payment_status=status_paid,
                amount=Decimal("820.00"),
                description="Comida Restaurante Los Morales",
                record_date=today - timedelta(days=5),
                is_recurrent=False,
                is_active=True,
                created_by=user,
            ),
            # Recurrentes
            FinancialRecord(
                user=user,
                dashboard=dash_bbva,
                record_type=record_type_expense,
                category=cat_streaming,
                payment_method=pm_credito,
                payment_status=status_paid,
                amount=Decimal("329.00"),
                description="Suscripción Netflix Premium 4K",
                record_date=today - timedelta(days=9),
                is_recurrent=True,
                is_active=True,
                created_by=user,
            ),
            FinancialRecord(
                user=user,
                dashboard=dash_santander,
                record_type=record_type_expense,
                category=cat_internet,
                payment_method=pm_spei,
                payment_status=status_pending,
                amount=Decimal("799.00"),
                description="Internet Totalplay Fibra 500MB",
                record_date=today + timedelta(days=4),
                is_recurrent=True,
                is_active=True,
                created_by=user,
            ),
            FinancialRecord(
                user=user,
                dashboard=dash_bbva,
                record_type=record_type_expense,
                category=cat_servicios,
                payment_method=pm_credito,
                payment_status=status_pending,
                amount=Decimal("620.00"),
                description="Recibo de Luz CFE Bimestral",
                record_date=today + timedelta(days=6),
                is_recurrent=False,
                is_active=True,
                created_by=user,
            ),
            # Meses Sin Intereses (MSI) - Cuota Actual (mes corriente)
            FinancialRecord(
                user=user,
                dashboard=dash_bbva,
                record_type=record_type_expense,
                category=cat_entretenimiento,
                payment_method=pm_credito,
                payment_status=status_paid,
                amount=Decimal("2650.00"),
                description="MacBook Pro M3 Apple Store (MSI)",
                record_date=today,
                is_recurrent=False,
                current_installment=4,
                total_installments=12,
                is_active=True,
                created_by=user,
            ),
            # MSI - Cuota Anterior
            FinancialRecord(
                user=user,
                dashboard=dash_bbva,
                record_type=record_type_expense,
                category=cat_entretenimiento,
                payment_method=pm_credito,
                payment_status=status_paid,
                amount=Decimal("2650.00"),
                description="MacBook Pro M3 Apple Store (MSI)",
                record_date=today - timedelta(days=30),
                is_recurrent=False,
                current_installment=3,
                total_installments=12,
                is_active=True,
                created_by=user,
            ),
            # MSI - Cuota Siguiente (Pendiente)
            FinancialRecord(
                user=user,
                dashboard=dash_bbva,
                record_type=record_type_expense,
                category=cat_entretenimiento,
                payment_method=pm_credito,
                payment_status=status_pending,
                amount=Decimal("2650.00"),
                description="MacBook Pro M3 Apple Store (MSI)",
                record_date=today + timedelta(days=30),
                is_recurrent=False,
                current_installment=5,
                total_installments=12,
                is_active=True,
                created_by=user,
            ),
            # Efectivo
            FinancialRecord(
                user=user,
                dashboard=dash_efectivo,
                record_type=record_type_expense,
                category=cat_comida,
                payment_method=pm_efectivo,
                payment_status=status_paid,
                amount=Decimal("350.00"),
                description="Cafetería y Almuerzos rápidos",
                record_date=today - timedelta(days=2),
                is_recurrent=False,
                is_active=True,
                created_by=user,
            ),
            FinancialRecord(
                user=user,
                dashboard=dash_efectivo,
                record_type=record_type_expense,
                category=cat_salud,
                payment_method=pm_efectivo,
                payment_status=status_paid,
                amount=Decimal("480.00"),
                description="Farmacia San Pablo - Medicamentos",
                record_date=today - timedelta(days=6),
                is_recurrent=False,
                is_active=True,
                created_by=user,
            ),
        ]
        FinancialRecord.objects.bulk_create(records_to_create)

    return user
