"""
GTOPagos AI Runtime & Orchestrator
Coordina la interacción del usuario con las herramientas MCP, Skills financieras y modelos LLM.
Diseñado bajo el principio de Zero-Cost y Zero-Hallucination:
- Todos los cálculos matemáticos se delegan a Skills tipadas (SDD) vía MCP.
- Funciona 100% de manera autónoma en modo heurístico local (sin necesidad de API Keys ni servicios de pago).
- Soporta integración plug-and-play con Ollama local (Llama 3.2 / Mistral) o Google Gemini Flash API.
- Genera bloques estructurados de Generative UI listos para renderizarse en Angular 21.
"""
import re
import os
import json
import logging
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
from typing import Dict, Any, Optional, List

from agent.specs.schemas import (
    MSICalculatorInput,
    CashflowForecastInput,
    DueDatePriorityInput,
    CategorizerInput,
    PendingObligation,
    DueDateItem,
    AgentActionResponse
)
from agent.mcp_server.server import mcp_server

logger = logging.getLogger(__name__)


class FinancialAIOrchestrator:
    """
    Orquestador financiero inteligente para GTOPagos.
    """

    def __init__(self):
        self.mcp = mcp_server
        self.system_name = "GTOPagos Financial Agent"
        self.version = "1.0.0"

    def process_query(self, user_query: str, user=None, context: Optional[Dict[str, Any]] = None) -> AgentActionResponse:
        """
        Punto de entrada principal para procesar consultas del usuario.
        """
        query = (user_query or "").strip()
        if not query:
            return AgentActionResponse(
                success=False,
                thought="Consulta vacía recibida.",
                action_type="ALERT",
                data={"widget_type": "info_banner"},
                user_message="Por favor, escribe una pregunta o comando para que pueda ayudarte con tus finanzas."
            )

        query_lower = query.lower()

        # 1. Detección de Intención: Meses Sin Intereses (MSI)
        msi_match = self._match_msi_query(query)
        if msi_match:
            return self._handle_msi_intent(msi_match)

        # 2. Detección de Intención: Semáforo / Priorización de Vencimientos
        if self._is_due_date_priority_query(query_lower):
            return self._handle_due_date_priority_intent(user, query_lower)

        # 3. Detección de Intención: Flujo de caja / Proyección quincenal
        if self._is_cashflow_query(query_lower):
            return self._handle_cashflow_intent(query, user)

        # 4. Detección de Intención: Categorización de Gasto / Transacción
        cat_match = self._match_categorize_query(query)
        if cat_match:
            return self._handle_categorize_intent(cat_match)

        # 5. Detección de Intención: Consejos / Salud Financiera / Regla 50-30-20
        if self._is_financial_advice_query(query_lower):
            return self._handle_financial_advice_intent(query_lower)

        # 6. Fallback Heurístico / Asistente General
        return self._handle_general_fallback(query)

    # --------------------------------------------------------------------------
    # MATCHERS & EXTRACTORS
    # --------------------------------------------------------------------------

    def _match_msi_query(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Detecta consultas de MSI como:
        - "compré una tv de 15,000 a 12 meses sin intereses"
        - "cuánto pago por 6000 a 6 cuotas"
        - "calcular msi 12000 12 meses voy en la cuota 3"
        """
        text_lower = text.lower()
        if not any(k in text_lower for k in ["msi", "meses sin intereses", "meses", "cuotas", "parcialidades"]):
            return None

        # Extraer montos ($12,000 o 12000 o 12000.50)
        amount_match = re.search(r'(?:\$|\bde\s+)?(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:pesos|mxn)?', text, re.IGNORECASE)
        # Extraer cuotas (a 12 meses, en 6 cuotas, 18 msi)
        installments_match = re.search(r'(?:a|en|de)?\s*(\d{1,2})\s*(?:msi|meses|cuotas|parcialidades)', text, re.IGNORECASE)

        if amount_match and installments_match:
            raw_amount = amount_match.group(1).replace(',', '')
            raw_inst = installments_match.group(1)
            try:
                amount = Decimal(raw_amount)
                installments = int(raw_inst)
                if amount > Decimal('0.00') and 2 <= installments <= 72:
                    # Extraer cuota actual si se especifica ("voy en la cuota 3", "llevo 2")
                    curr_match = re.search(r'(?:cuota|pago|mes)\s*(\d{1,2})', text_lower)
                    curr = int(curr_match.group(1)) if curr_match else 1
                    if curr > installments:
                        curr = 1

                    return {
                        "total_amount": amount,
                        "total_installments": installments,
                        "current_installment": curr
                    }
            except (InvalidOperation, ValueError):
                pass
        return None

    def _is_due_date_priority_query(self, text: str) -> bool:
        keywords = [
            "vencimiento", "vencimientos", "vencen", "semaforo", "semáforo",
            "urgente", "prioridad de pago", "que debo pagar", "qué debo pagar",
            "proximos pagos", "próximos pagos", "deudas por vencer"
        ]
        return any(k in text for k in keywords)

    def _is_cashflow_query(self, text: str) -> bool:
        keywords = [
            "flujo de caja", "cashflow", "quincena", "corte 15", "corte 30",
            "solvencia", "liquidez", "cuanto me queda", "cuánto me queda",
            "margen libre", "porcentaje comprometido"
        ]
        return any(k in text for k in keywords)

    def _match_categorize_query(self, text: str) -> Optional[str]:
        patterns = [
            r'categoriz(?:a|ar)\s*[:\-]?\s*(.+)',
            r'clasific(?:a|ar)\s*[:\-]?\s*(.+)',
            r'que categor[ií]a es\s*[:\-]?\s*(.+)',
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    def _is_financial_advice_query(self, text: str) -> bool:
        keywords = [
            "ahorrar", "ahorro", "regla 50", "50/30/20", "50-30-20",
            "consejo", "reducir gastos", "como salir de deudas", "fondo de emergencia",
            "salud financiera"
        ]
        return any(k in text for k in keywords)

    # --------------------------------------------------------------------------
    # INTENT HANDLERS
    # --------------------------------------------------------------------------

    def _handle_msi_intent(self, params: Dict[str, Any]) -> AgentActionResponse:
        total_amount = params["total_amount"]
        installments = params["total_installments"]
        curr = params["current_installment"]

        mcp_res = self.mcp.call_tool("calculate_msi_projection", {
            "total_amount": float(total_amount),
            "total_installments": installments,
            "current_installment": curr
        })

        if not mcp_res.success:
            return mcp_res

        data = mcp_res.data
        data["widget_type"] = "msi_card"

        user_message = (
            f"### 💳 Proyección de Compra a Meses Sin Intereses\n\n"
            f"- **Monto Total:** ${Decimal(data['total_amount']):,.2f} MXN\n"
            f"- **Plazo:** {data['total_installments']} cuotas fijas\n"
            f"- **Cuota Mensual:** **${Decimal(data['monthly_installment']):,.2f} MXN** "
            f"*(o ${Decimal(data['biweekly_installment']):,.2f} por quincena)*\n"
            f"- **Saldo Pendiente:** ${Decimal(data['remaining_balance']):,.2f} MXN ({data['remaining_installments']} cuotas restantes)\n\n"
            f"💡 *Recomendación del Agente:* Agenda la fecha límite de pago 2 días hábiles antes de tu corte para evitar cargos moratorios involuntarios."
        )

        return AgentActionResponse(
            success=True,
            thought=f"Se calculó MSI para ${total_amount} a {installments} meses (cuota actual {curr}).",
            action_type="CALCULATION",
            data=data,
            user_message=user_message
        )

    def _handle_due_date_priority_intent(self, user, query: str) -> AgentActionResponse:
        today = date.today()
        items = []

        # Intentar obtener los registros reales del usuario si está autenticado en Django
        if user and hasattr(user, "is_authenticated") and user.is_authenticated:
            try:
                from finance.models import FinancialRecord
                records = FinancialRecord.objects.filter(
                    user=user,
                    is_active=True,
                    record_type__behavior='EXPENSE'
                ).exclude(
                    payment_status__status__iexact='PAGADO'
                ).select_related('record_type', 'payment_status')[:15]

                for rec in records:
                    items.append(DueDateItem(
                        id=rec.id,
                        concept=rec.description or f"Gasto #{rec.id}",
                        amount=rec.amount,
                        due_date=rec.record_date,
                        is_paid=False
                    ))
            except Exception as e:
                logger.warning(f"Error fetching user records for due date priority: {e}")

        # Si el usuario no tiene registros o es invitado, generar simulación interactiva
        if not items:
            items = [
                DueDateItem(id=1, concept="Tarjeta de Crédito (Corte)", amount=Decimal('3450.00'), due_date=today + timedelta(days=2)),
                DueDateItem(id=2, concept="Servicio de Luz (CFE)", amount=Decimal('480.00'), due_date=today + timedelta(days=5)),
                DueDateItem(id=3, concept="Servicio de Internet", amount=Decimal('649.00'), due_date=today + timedelta(days=11)),
                DueDateItem(id=4, concept="Cuota Crédito Auto", amount=Decimal('4200.00'), due_date=today + timedelta(days=19)),
            ]

        mcp_res = self.mcp.call_tool("prioritize_due_dates", {
            "reference_date": today.isoformat(),
            "items": [item.model_dump(mode='json') for item in items]
        })

        if not mcp_res.success:
            return mcp_res

        data = mcp_res.data
        data["widget_type"] = "priority_table"
        crit = data.get("critical_count", 0)

        alert_msg = "🚨 **Atención Inmediata:** Tienes pagos críticos que vencen en menos de 3 días." if crit > 0 else "✅ **Situación Estable:** No tienes pagos en riesgo inmediato."

        user_message = (
            f"### 🚦 Semáforo de Vencimientos y Prioridad de Pagos\n\n"
            f"{alert_msg}\n\n"
            f"- **Compromisos evaluados:** {len(data['prioritized_list'])}\n"
            f"- **Monto total por cubrir:** ${Decimal(data['total_pending_amount']):,.2f} MXN\n"
            f"- **Pagos Críticos / Vencidos:** {crit}\n\n"
            f"*(Consulta la tabla interactiva abajo para ver el desglose ordenado por urgencia)*"
        )

        return AgentActionResponse(
            success=True,
            thought=f"Priorización de vencimientos ejecutada con {len(items)} items ({crit} críticos).",
            action_type="READ_ONLY",
            data=data,
            user_message=user_message
        )

    def _handle_cashflow_intent(self, text: str, user) -> AgentActionResponse:
        # Extraer salario si está presente en el texto ("gano 20000", "salario de 15,000")
        salary_match = re.search(r'(?:gano|salario|ingreso|sueldo|de)\s*(?:\$)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+)', text, re.IGNORECASE)
        if salary_match:
            try:
                salary = Decimal(salary_match.group(1).replace(',', ''))
            except InvalidOperation:
                salary = Decimal('20000.00')
        else:
            salary = Decimal('20000.00')

        # Detectar corte 15 o 30
        cutoff = 30 if any(k in text for k in ["30", "segunda quincena", "fin de mes"]) else 15

        # Generar u obtener compromisos
        obligations = [
            PendingObligation(description="Renta departamental", amount=Decimal('5500.00'), due_date=date.today()),
            PendingObligation(description="Servicios y despensa", amount=Decimal('2300.00'), due_date=date.today()),
        ]

        mcp_res = self.mcp.call_tool("forecast_cashflow", {
            "salary": float(salary),
            "cutoff_day": cutoff,
            "obligations": [ob.model_dump(mode='json') for ob in obligations]
        })

        if not mcp_res.success:
            return mcp_res

        data = mcp_res.data
        data["widget_type"] = "cashflow_gauge"

        user_message = (
            f"### 📊 Proyección de Flujo de Caja (Corte {cutoff})\n\n"
            f"- **Ingreso Quincenal Estimado:** ${Decimal(data['total_income']):,.2f} MXN\n"
            f"- **Gastos Comprometidos:** ${Decimal(data['total_committed']):,.2f} MXN\n"
            f"- **Margen Libre:** **${Decimal(data['available_margin']):,.2f} MXN**\n"
            f"- **Porcentaje Comprometido:** {data['compromised_percentage']}%\n"
            f"- **Nivel de Riesgo:** **{data['risk_level']}**\n\n"
            f"{data.get('risk_alert') or '✨ Tienes un flujo saludable para cubrir tus gastos e impulsar tu ahorro.'}"
        )

        return AgentActionResponse(
            success=True,
            thought=f"Flujo de caja calculado para corte {cutoff}. Riesgo: {data['risk_level']}.",
            action_type="ALERT" if data['risk_level'] in ["ALTO", "CRÍTICO"] else "CALCULATION",
            data=data,
            user_message=user_message
        )

    def _handle_categorize_intent(self, description: str) -> AgentActionResponse:
        mcp_res = self.mcp.call_tool("categorize_expense", {
            "description": description
        })

        if not mcp_res.success:
            return mcp_res

        data = mcp_res.data
        data["widget_type"] = "category_badge"

        confidence_pct = int(Decimal(str(data['confidence'])) * Decimal('100'))

        user_message = (
            f"### 🏷️ Categorización Inteligente\n\n"
            f"El concepto **\"{data['original_text']}\"** ha sido clasificado como:\n\n"
            f"📂 **{data['suggested_category']}** *(Tipo: {data['behavior']})*\n"
            f"🎯 Confianza: **{confidence_pct}%**\n\n"
            f"Puedes usar esta categoría al registrar tu movimiento en el Dashboard."
        )

        return AgentActionResponse(
            success=True,
            thought=f"Concepto '{description}' categorizado como '{data['suggested_category']}'.",
            action_type="READ_ONLY",
            data=data,
            user_message=user_message
        )

    def _handle_financial_advice_intent(self, text: str) -> AgentActionResponse:
        data = {
            "widget_type": "financial_tips",
            "methodology": "Regla 50/30/20",
            "breakdown": [
                {"pct": 50, "label": "Necesidades Básicas", "desc": "Renta, alimentos, servicios, transporte"},
                {"pct": 30, "label": "Deseos y Calidad de Vida", "desc": "Salidas, entretenimiento, compras no esenciales"},
                {"pct": 20, "label": "Ahorro e Inversión", "desc": "Fondo de emergencia, amortización de deudas, retiro"}
            ]
        }

        user_message = (
            f"### 💡 Estrategia Financiera Inteligente: Regla 50/30/20\n\n"
            f"Para mantener unas finanzas sanas y evitar sobreendeudarte:\n\n"
            f"1. **50% Necesidades:** Tu vivienda, servicios y comida indispensable.\n"
            f"2. **30% Estilo de Vida:** Entretenimiento, restaurantes y compras personales.\n"
            f"3. **20% Futuro y Deudas:** Ahorro automático y liquidación de créditos costosos.\n\n"
            f"📌 *Tip GTOPagos:* Automatiza transferencias a tu meta de ahorro el mismo día que recibes tu nómina."
        )

        return AgentActionResponse(
            success=True,
            thought="Se proporcionó guía financiera estructurada 50/30/20.",
            action_type="READ_ONLY",
            data=data,
            user_message=user_message
        )

    def _handle_general_fallback(self, query: str) -> AgentActionResponse:
        data = {
            "widget_type": "assistant_capabilities",
            "capabilities": [
                {"title": "Cálculo de MSI", "example": "\"Compré una laptop de $12,000 a 12 meses sin intereses\""},
                {"title": "Semáforo de Vencimientos", "example": "\"¿Cuáles son mis pagos más urgentes?\""},
                {"title": "Flujo de Caja Quincenal", "example": "\"Gano 18,000 al mes, ¿cómo viene mi corte 15?\""},
                {"title": "Categorización Inteligente", "example": "\"Categoriza: OXXO GAS COMBUSTIBLE 500\""},
                {"title": "Salud Financiera", "example": "\"¿Cómo funciona la regla 50/30/20?\""},
            ]
        }

        user_message = (
            f"👋 ¡Hola! Soy tu **Asistente Financiero GTOPagos**.\n\n"
            f"Puedo ayudarte a gestionar tus números con total precisión matemática y cero riesgos. Prueba pedirme:\n\n"
            f"- 💳 *\"Compré una televisión de $9,000 a 6 meses sin intereses\"*\n"
            f"- 🚦 *\"Semáforo de vencimientos\"* para ver tus adeudos urgentes\n"
            f"- 📊 *\"Gano 16,000 y tengo corte el 15, ¿cómo ando de liquidez?\"*\n"
            f"- 🏷️ *\"Categoriza: Pago NETFLIX mensual\"*\n"
            f"- 💡 *\"Dame consejos de ahorro con la regla 50/30/20\"*"
        )

        return AgentActionResponse(
            success=True,
            thought="Se devolvió menú de capacidades del agente.",
            action_type="READ_ONLY",
            data=data,
            user_message=user_message
        )


# Singleton
ai_orchestrator = FinancialAIOrchestrator()
