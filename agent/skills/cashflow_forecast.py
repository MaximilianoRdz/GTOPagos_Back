"""
Skill: CashflowForecastSkill
Análisis de solvencia y proyección de flujo de caja para cortes quincenales (15 y 30) frente al salario disponible.
"""
from decimal import Decimal, ROUND_HALF_UP
from agent.specs.schemas import CashflowForecastInput, CashflowForecastOutput


def forecast_cashflow(payload: CashflowForecastInput) -> CashflowForecastOutput:
    salary = payload.salary
    cutoff = payload.cutoff_day
    obligations = payload.obligations

    # Filtramos compromisos pendientes (no pagados) dentro del periodo
    # Para corte 15: días 1 al 15. Para corte 30: días 16 al fin de mes
    pending_items = []
    for ob in obligations:
        if not ob.is_paid:
            day = ob.due_date.day
            if cutoff == 15 and day <= 15:
                pending_items.append(ob)
            elif cutoff == 30 and day > 15:
                pending_items.append(ob)
            elif len(obligations) <= 5:
                # Si son pocas obligaciones globales, se evalúan todas
                pending_items.append(ob)

    total_committed = sum((ob.amount for ob in pending_items), Decimal('0.00'))
    
    # Asumimos que el ingreso por quincena corresponde al salario quincenal (salario / 2)
    fortnight_income = (salary / Decimal('2.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    available_margin = fortnight_income - total_committed

    if fortnight_income > Decimal('0.00'):
        ratio = (total_committed / fortnight_income) * Decimal('100.00')
        compromised_percentage = ratio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        compromised_percentage = Decimal('100.00')

    # Clasificación de riesgo de liquidez
    if compromised_percentage < Decimal('50.00'):
        risk_level = "BAJO"
        risk_alert = None
    elif compromised_percentage < Decimal('75.00'):
        risk_level = "MODERADO"
        risk_alert = "Tus gastos comprometen más de la mitad de tus ingresos de esta quincena. Mantén compras no esenciales al mínimo."
    elif compromised_percentage < Decimal('90.00'):
        risk_level = "ALTO"
        risk_alert = "⚠️ Alerta de liquidez: Tus pagos superan el 75% de tu quincena. Riesgo de falta de flujo."
    else:
        risk_level = "CRÍTICO"
        risk_alert = "🚨 PELIGRO: Has comprometido más del 90% de tu dinero quincenal. No realices nuevas compras a crédito."

    return CashflowForecastOutput(
        cutoff_day=cutoff,
        total_income=fortnight_income,
        total_committed=total_committed,
        available_margin=available_margin,
        compromised_percentage=compromised_percentage,
        risk_level=risk_level,
        risk_alert=risk_alert,
        pending_items_count=len(pending_items)
    )
