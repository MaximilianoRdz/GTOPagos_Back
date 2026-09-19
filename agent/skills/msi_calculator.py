"""
Skill: MSICalculatorSkill
Cálculo determinístico de cuotas, saldos y tablas de amortización para compras a Meses Sin Intereses.
"""
from decimal import Decimal, ROUND_HALF_UP
from agent.specs.schemas import MSICalculatorInput, MSICalculatorOutput, MSIInstallmentSchedule


def calculate_msi_projection(payload: MSICalculatorInput) -> MSICalculatorOutput:
    total_amount = payload.total_amount
    n = payload.total_installments
    curr = payload.current_installment

    # Cálculo base de cuota mensual con redondeo a 2 decimales
    base_installment = (total_amount / Decimal(n)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    biweekly_installment = (base_installment / Decimal(2)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Generación de la tabla de cuotas con ajuste de centavos en la última cuota si aplica
    schedule = []
    accumulated = Decimal('0.00')

    for i in range(1, n + 1):
        if i == n:
            # En la última cuota se ajusta la diferencia de redondeo exacta
            inst_amount = total_amount - accumulated
        else:
            inst_amount = base_installment
            accumulated += inst_amount

        # Se considera pagada si es estrictamente menor a la cuota actual
        status = "PAGADO" if i < curr else "PENDIENTE"
        schedule.append(MSIInstallmentSchedule(
            installment_number=i,
            amount=inst_amount,
            status=status
        ))

    # Métricas consolidadas
    paid_so_far = sum(item.amount for item in schedule if item.status == "PAGADO")
    remaining_balance = total_amount - paid_so_far
    remaining_installments = n - (curr - 1)
    is_fully_paid = (curr > n) or (remaining_balance <= Decimal('0.00'))

    return MSICalculatorOutput(
        total_amount=total_amount,
        total_installments=n,
        current_installment=curr,
        monthly_installment=base_installment,
        biweekly_installment=biweekly_installment,
        amount_paid_so_far=paid_so_far,
        remaining_balance=remaining_balance,
        remaining_installments=remaining_installments,
        is_fully_paid=is_fully_paid,
        schedule=schedule
    )
