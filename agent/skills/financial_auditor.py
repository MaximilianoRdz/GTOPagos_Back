"""
Skill: FinancialAuditorSkill
Diagnóstico holístico integral 360° del sistema financiero del usuario.
Analiza la correlación entre Ingresos, Gastos por Categoría, Carga de Deudas/MSI y Viabilidad de Metas de Ahorro.
Calcula el Financial Health Score (0-100) con recomendaciones prescriptivas y sin alucinaciones.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import List

from agent.specs.schemas import (
    SystemAuditInput,
    SystemAuditOutput,
    CategoryBreakdownItem,
    GoalFeasibilityItem,
    AuditRecommendation
)


def audit_financial_system(payload: SystemAuditInput) -> SystemAuditOutput:
    records = payload.records
    goals = payload.goals
    profile_salary = payload.salary

    # 1. Agregación de Ingresos y Gastos
    recorded_income = Decimal('0.00')
    total_expenses = Decimal('0.00')
    fixed_commitments = Decimal('0.00')
    category_totals = {}
    category_counts = {}

    for r in records:
        if r.behavior == 'INCOME':
            recorded_income += r.amount
        elif r.behavior == 'EXPENSE':
            total_expenses += r.amount
            cat = r.category_name or "Otros"
            category_totals[cat] = category_totals.get(cat, Decimal('0.00')) + r.amount
            category_counts[cat] = category_counts.get(cat, 0) + 1

            if r.is_recurrent or (r.total_installments and r.total_installments > 1):
                fixed_commitments += r.amount

    # Usar salario de perfil si no hay ingresos en registros
    effective_income = recorded_income if recorded_income > Decimal('0.00') else profile_salary
    net_savings = effective_income - total_expenses

    # Tasa de Ahorro
    if effective_income > Decimal('0.00'):
        savings_rate = ((net_savings / effective_income) * Decimal('100.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        savings_rate = Decimal('0.00')

    # Carga de compromisos fijos / deudas sobre gastos
    if total_expenses > Decimal('0.00'):
        debt_burden_rate = ((fixed_commitments / total_expenses) * Decimal('100.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        debt_burden_rate = Decimal('0.00')

    # 2. Desglose y Ranking de Categorías (Top 5)
    top_categories: List[CategoryBreakdownItem] = []
    sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    for cat_name, amount in sorted_cats[:5]:
        pct = ((amount / total_expenses) * Decimal('100.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if total_expenses > 0 else Decimal('0.00')
        top_categories.append(CategoryBreakdownItem(
            category=cat_name,
            total_amount=amount,
            percentage_of_expenses=pct,
            count=category_counts.get(cat_name, 1)
        ))

    # 3. Viabilidad de Metas de Ahorro
    goals_feasibility: List[GoalFeasibilityItem] = []
    viable_goals_count = 0
    today = date.today()

    for g in goals:
        rem = max(Decimal('0.00'), g.target_amount - g.saved_amount)
        prog_pct = ((g.saved_amount / g.target_amount) * Decimal('100.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if g.target_amount > 0 else Decimal('0.00')

        if g.target_date:
            months = max(1, (g.target_date.year - today.year) * 12 + (g.target_date.month - today.month))
        else:
            months = 6  # Estimación estándar a 6 meses

        monthly_req = (rem / Decimal(months)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        is_viable = (monthly_req <= net_savings) if net_savings > Decimal('0.00') else False

        if rem == Decimal('0.00'):
            status = "LOGRADA"
            msg = "¡Meta cumplida al 100%! 🎉"
            viable_goals_count += 1
        elif is_viable:
            status = "VIABLE"
            msg = f"Aportando ${monthly_req:,.2f}/mes la cumplirás a tiempo."
            viable_goals_count += 1
        else:
            status = "EN RIESGO"
            msg = f"Requiere ${monthly_req:,.2f}/mes, pero tu margen libre es de ${net_savings:,.2f}/mes."

        goals_feasibility.append(GoalFeasibilityItem(
            name=g.name,
            saved_amount=g.saved_amount,
            target_amount=g.target_amount,
            progress_percentage=prog_pct,
            remaining_amount=rem,
            monthly_required=monthly_req,
            is_viable=is_viable,
            status=status,
            message=msg
        ))

    # 4. Cálculo del Financial Health Score (0 - 100)
    score = 0

    # Pilar 1: Capacidad de Ahorro (hasta 30 pts)
    if savings_rate >= Decimal('25.00'):
        score += 30
    elif savings_rate >= Decimal('15.00'):
        score += 25
    elif savings_rate >= Decimal('5.00'):
        score += 15
    elif savings_rate >= Decimal('0.00'):
        score += 8

    # Pilar 2: Control de Deuda y Cuotas fijas (hasta 30 pts)
    if debt_burden_rate <= Decimal('20.00'):
        score += 30
    elif debt_burden_rate <= Decimal('35.00'):
        score += 22
    elif debt_burden_rate <= Decimal('50.00'):
        score += 12
    else:
        score += 5

    # Pilar 3: Solvencia y Margen Libre (hasta 20 pts)
    if net_savings > Decimal('5000.00'):
        score += 20
    elif net_savings > Decimal('0.00'):
        score += 15
    elif net_savings == Decimal('0.00'):
        score += 8
    else:
        score += 0

    # Pilar 4: Alineación de Metas (hasta 20 pts)
    if goals:
        if viable_goals_count == len(goals):
            score += 20
        elif viable_goals_count > 0:
            score += 12
        else:
            score += 5
    else:
        score += 15  # Neutral si aún no tiene metas configuradas

    score = max(5, min(100, score))

    if score >= 85:
        health_status = "EXCELENTE"
    elif score >= 70:
        health_status = "SALUDABLE"
    elif score >= 50:
        health_status = "MEJORABLE"
    else:
        health_status = "CRÍTICO"

    # 5. Generación de Recomendaciones Prescriptivas
    recommendations: List[AuditRecommendation] = []

    # Recomendación sobre categoría con mayor fuga
    if top_categories and top_categories[0].percentage_of_expenses > Decimal('30.00'):
        top_cat = top_categories[0]
        potential_saving = (top_cat.total_amount * Decimal('0.15')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        recommendations.append(AuditRecommendation(
            priority="ALTA",
            title=f"Optimizar categoría '{top_cat.category}'",
            detail=f"Representa el {top_cat.percentage_of_expenses}% de tus salidas (${top_cat.total_amount:,.2f}). Un ajuste del 15% liberaría ${potential_saving:,.2f} MXN mensuales adicionales para tus metas.",
            action_type="BUDGET_OPTIMIZATION"
        ))

    # Recomendación sobre deudas o cuotas
    if debt_burden_rate > Decimal('30.00'):
        recommendations.append(AuditRecommendation(
            priority="ALTA",
            title="Pausa estratégica en nuevas compras a crédito (MSI)",
            detail=f"Tus compromisos fijos y pagos de cuotas ascienden a ${fixed_commitments:,.2f} MXN ({debt_burden_rate}% de tus gastos). Evita adquirir nuevos meses sin intereses hasta liquidar las cuotas vigentes.",
            action_type="DEBT_CONTROL"
        ))
    else:
        recommendations.append(AuditRecommendation(
            priority="OPTIMIZACIÓN",
            title="Excelente control de endeudamiento",
            detail=f"Tus compromisos fijos solo absorben el {debt_burden_rate}% de tus gastos. Tu apalancamiento es muy saludable.",
            action_type="POSITIVE_FEEDBACK"
        ))

    # Recomendación sobre metas
    at_risk_goals = [g for g in goals_feasibility if g.status == "EN RIESGO"]
    if at_risk_goals:
        first_risk = at_risk_goals[0]
        recommendations.append(AuditRecommendation(
            priority="MEDIA",
            title=f"Ajustar calendario de meta '{first_risk.name}'",
            detail=f"Requiere ${first_risk.monthly_required:,.2f}/mes pero tu margen libre es de ${net_savings:,.2f}. Sugerencia: extiende la fecha meta 2 meses para reducir la mensualidad requerida a un nivel 100% cómodo.",
            action_type="GOAL_TIMELINE_ADJUST"
        ))
    elif goals_feasibility:
        recommendations.append(AuditRecommendation(
            priority="OPTIMIZACIÓN",
            title="Tus metas de ahorro son 100% alcanzables",
            detail="Con tu ritmo de ahorro actual y tus ingresos registrados, tienes la capacidad de cubrir todas tus metas a tiempo.",
            action_type="POSITIVE_FEEDBACK"
        ))

    # Resumen narrativo ejecutivo
    summary_text = (
        f"Diagnóstico 360° completado para {payload.user_name}. "
        f"Índice de Salud Financiera: {score}/100 ({health_status}). "
        f"Ingreso efectivo: ${effective_income:,.2f} MXN, Gastos totales: ${total_expenses:,.2f} MXN, "
        f"Margen libre de ahorro: ${net_savings:,.2f} MXN ({savings_rate}% de tasa de ahorro). "
        f"Metas viables: {viable_goals_count}/{len(goals)}."
    )

    return SystemAuditOutput(
        health_score=score,
        health_status=health_status,
        total_income=effective_income,
        total_expenses=total_expenses,
        net_savings=net_savings,
        savings_rate=savings_rate,
        debt_burden_rate=debt_burden_rate,
        monthly_fixed_commitments=fixed_commitments,
        top_categories=top_categories,
        goals_feasibility=goals_feasibility,
        recommendations=recommendations,
        summary_text=summary_text
    )
