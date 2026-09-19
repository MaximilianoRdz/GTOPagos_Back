"""
Skill: DueDatePrioritySkill
Clasificación semafórica de deudas y compromisos por urgencia de vencimiento.
"""
from decimal import Decimal
from datetime import date
from agent.specs.schemas import DueDatePriorityInput, DueDatePriorityOutput, PrioritizedObligation


def prioritize_due_dates(payload: DueDatePriorityInput) -> DueDatePriorityOutput:
    ref = payload.reference_date
    raw_items = payload.items

    prioritized = []
    critical_count = 0
    total_amount = Decimal('0.00')

    for item in raw_items:
        if item.is_paid:
            continue

        days_left = (item.due_date - ref).days
        total_amount += item.amount

        if days_left < 0:
            priority = "VENCIDO"
            color = "#991B1B"  # Rojo vino
            critical_count += 1
        elif days_left <= 3:
            priority = "CRÍTICO"
            color = "#EF4444"  # Rojo vivo
            critical_count += 1
        elif days_left <= 7:
            priority = "URGENTE"
            color = "#F59E0B"  # Ámbar
        elif days_left <= 15:
            priority = "PRÓXIMO"
            color = "#3B82F6"  # Azul
        else:
            priority = "HOLGADO"
            color = "#10B981"  # Verde esmeralda

        prioritized.append(PrioritizedObligation(
            id=item.id,
            concept=item.concept,
            amount=item.amount,
            due_date=item.due_date,
            days_left=days_left,
            priority=priority,
            color_code=color
        ))

    # Ordenar estrictamente por urgencia (menor número de días primero)
    prioritized.sort(key=lambda x: x.days_left)

    return DueDatePriorityOutput(
        reference_date=ref,
        critical_count=critical_count,
        total_pending_amount=total_amount,
        prioritized_list=prioritized
    )
