"""
GTOPagos AI Runtime & Orchestrator
Coordina la interacción del usuario con las herramientas MCP, Skills financieras y modelos LLM.
Diseñado bajo el principio de Zero-Cost, Zero-Hallucination y Alta Inteligencia Conversacional:
- Conexión directa a los datos REALES del usuario autenticado (Saldos, Gastos, Metas, Salario).
- Detección precisa de intenciones (Saludos, Resumen de Cuentas, Metas, Pagos Pendientes, MSI, Conceptos Financieros).
- Integración plug-and-play con Google Gemini 1.5 Flash (Free Tier) u Ollama local cuando se proporciona API Key.
- Cero alucinaciones matemáticas: los cálculos se procesan en las Skills tipadas de MCP.
"""
import re
import os
import json
import logging
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
from typing import Dict, Any, Optional, List
import urllib.request
import urllib.error

from agent.specs.schemas import (
    MSICalculatorInput,
    CashflowForecastInput,
    DueDatePriorityInput,
    CategorizerInput,
    PendingObligation,
    DueDateItem,
    AuditRecordItem,
    AuditGoalItem,
    SystemAuditInput,
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
        self.version = "1.1.0"

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

        # 1. Saludos y cortesía ("hola", "buenos días", "qué tal", "cómo estás")
        if self._is_greeting(query_lower):
            return self._handle_greeting_intent(user)

        # 2. Preguntas sobre identidad o capacidades ("quién eres", "qué puedes hacer", "ayuda")
        if self._is_identity_or_help_query(query_lower):
            return self._handle_identity_intent()

        # 3. Propuesta de Creación de Movimiento / Registro (Human-in-the-Loop)
        mutation_proposal = self._match_record_creation_intent(query, user)
        if mutation_proposal:
            return mutation_proposal

        # 4. Auditoría Integral 360° del Sistema (Ingresos, Gastos, Fugas, Deudas y Metas)
        if self._is_system_audit_query(query_lower):
            return self._handle_system_audit_intent(user)

        # 4. Consultas sobre datos reales del usuario (Saldo, Gastos, Ingresos del mes)
        if self._is_user_balance_or_summary_query(query_lower):
            return self._handle_user_summary_intent(user, query_lower)

        # 4. Consultas sobre Metas de ahorro reales del usuario ("cómo van mis metas", "mis metas")
        if self._is_user_goals_query(query_lower):
            return self._handle_user_goals_intent(user)

        # 5. Meses Sin Intereses (MSI) explícitos
        msi_match = self._match_msi_query(query)
        if msi_match:
            return self._handle_msi_intent(msi_match)

        # 6. Semáforo / Priorización de Vencimientos y Deudas
        if self._is_due_date_priority_query(query_lower):
            return self._handle_due_date_priority_intent(user, query_lower)

        # 7. Flujo de caja / Proyección quincenal
        if self._is_cashflow_query(query_lower):
            return self._handle_cashflow_intent(query, user)

        # 8. Categorización de Gasto / Transacción
        cat_match = self._match_categorize_query(query)
        if cat_match:
            return self._handle_categorize_intent(cat_match)

        # 9. Conceptos de Educación Financiera y Consejos (50/30/20, Bola de nieve, etc.)
        advice_res = self._match_financial_advice(query_lower)
        if advice_res:
            return advice_res

        # 10. Si existe GEMINI_API_KEY configurada, consultar al LLM con contexto financiero
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key:
            llm_res = self._ask_gemini_llm(query, user, gemini_api_key)
            if llm_res:
                return llm_res

        # 11. Fallback Heurístico Contextual (Inteligente y conversacional)
        return self._handle_smart_conversational_fallback(query, user)

    # --------------------------------------------------------------------------
    # DETECTORES DE INTENCIÓN (INTENT CLASSIFIERS)
    # --------------------------------------------------------------------------

    def _is_greeting(self, text: str) -> bool:
        greetings = [
            "hola", "buen dia", "buenos dias", "buenas tardes", "buenas noches",
            "hey", "que tal", "qué tal", "saludos", "que onda", "qué onda", "hi", "hello"
        ]
        words = re.findall(r'\b\w+\b', text)
        return any(w in words for w in greetings) and len(words) <= 5

    def _is_identity_or_help_query(self, text: str) -> bool:
        patterns = [
            r'qui[eé]n eres',
            r'qu[eé] puedes hacer',
            r'qu[eé] haces',
            r'para qu[eé] sirves',
            r'c[oó]mo me puedes ayudar',
            r'ayuda\b',
            r'comandos\b',
            r'funciones\b'
        ]
        return any(re.search(p, text) for p in patterns)

    def _is_system_audit_query(self, text: str) -> bool:
        keywords = [
            "analiza todo", "analiza el sistema", "analiza mis finanzas", "auditoria", "auditoría",
            "diagnostico", "diagnóstico", "analisis completo", "análisis completo", "mas inteligente",
            "más inteligente", "gastos e ingresos", "gastos y metas", "360", "analisis 360",
            "análisis 360", "auditoría 360", "auditoria 360", "evalua mis finanzas",
            "evalúa mis finanzas", "estado general", "salud financiera", "como estan mis finanzas",
            "cómo están mis finanzas", "auditoría del sistema", "auditoria del sistema",
            "audita mis finanzas", "auditar mis finanzas", "audita el sistema"
        ]
        return any(k in text for k in keywords)

    def _is_user_balance_or_summary_query(self, text: str) -> bool:
        keywords = [
            "cuanto dinero tengo", "cuánto dinero tengo", "cuanto tengo", "cuánto tengo",
            "mi saldo", "saldo actual", "cuanto he gastado", "cuánto he gastado",
            "mis gastos", "mis ingresos", "resumen de mis finanzas", "como voy este mes",
            "cómo voy este mes", "estado de mis finanzas", "dinero disponible", "mi balance"
        ]
        return any(k in text for k in keywords)

    def _is_user_goals_query(self, text: str) -> bool:
        keywords = [
            "mis metas", "metas de ahorro", "como van mis metas", "cómo van mis metas",
            "mis objetivos", "mis ahorros", "cuanto he ahorrado", "cuánto he ahorrado"
        ]
        return any(k in text for k in keywords)

    def _match_msi_query(self, text: str) -> Optional[Dict[str, Any]]:
        text_lower = text.lower()
        if not any(k in text_lower for k in ["msi", "meses sin intereses", "meses", "cuotas", "parcialidades"]):
            return None

        amount_match = re.search(r'(?:\$|\bde\s+)?(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:pesos|mxn)?', text, re.IGNORECASE)
        installments_match = re.search(r'(?:a|en|de)?\s*(\d{1,2})\s*(?:msi|meses|cuotas|parcialidades)', text, re.IGNORECASE)

        if amount_match and installments_match:
            raw_amount = amount_match.group(1).replace(',', '')
            raw_inst = installments_match.group(1)
            try:
                amount = Decimal(raw_amount)
                installments = int(raw_inst)
                if amount > Decimal('0.00') and 2 <= installments <= 72:
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
            "proximos pagos", "próximos pagos", "deudas por vencer", "mis deudas",
            "pagos pendientes", "que pagos tengo"
        ]
        return any(k in text for k in keywords)

    def _is_cashflow_query(self, text: str) -> bool:
        keywords = [
            "flujo de caja", "cashflow", "quincena", "corte 15", "corte 30",
            "solvencia", "liquidez", "cuanto me queda", "cuánto me queda",
            "margen libre", "porcentaje comprometido", "me alcanza"
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

    def _match_record_creation_intent(self, text: str, user) -> Optional[AgentActionResponse]:
        """
        Detecta instrucciones en lenguaje natural para registrar ingresos o gastos
        y genera una propuesta de mutación con confirmación interactiva (Human-in-the-Loop).
        """
        text_clean = text.strip()

        patterns = [
            r'(?:registra|registrar|anota|anotar|agrega|agregar|crea|crear|guarda|guardar)\s+(?:un\s+)?(?:nuevo\s+)?(gasto|ingreso|pago)\s+(?:de\s+)?(?:\$)?(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:pesos|mxn)?\s*(?:en|de|para|por)\s*(.+)',
            r'(gast[eé]|pagu[eé])\s+(?:\$)?(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:pesos|mxn)?\s*(?:en|de|para|por)\s*(.+)',
            r'(ingres[eé]|recib[ií])\s+(?:\$)?(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:pesos|mxn)?\s*(?:en|de|para|por)\s*(.+)',
            r'(?:nuevo\s+)?(gasto|ingreso|pago)\s+(?:de\s+)?(?:\$)?(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:pesos|mxn)?\s*(?:en|de|para|por)\s*(.+)'
        ]

        for pat in patterns:
            m = re.search(pat, text_clean, re.IGNORECASE)
            if m:
                tipo_raw = m.group(1).lower()
                amount_raw = m.group(2).replace(',', '')
                concept = m.group(3).strip()

                try:
                    amount = Decimal(amount_raw)
                    if amount <= Decimal('0.00'):
                        continue
                except (InvalidOperation, ValueError):
                    continue

                if tipo_raw in ["ingreso", "ingresé", "recibí"]:
                    behavior = "INCOME"
                    tipo_label = "Ingreso"
                else:
                    behavior = "EXPENSE"
                    tipo_label = "Gasto"

                # Inferir categoría semántica mediante skill de categorización
                cat_res = self.mcp.call_tool("categorize_expense", {"description": concept})
                suggested_cat = "Otros"
                if cat_res.success and isinstance(cat_res.data, dict):
                    suggested_cat = cat_res.data.get("suggested_category", "Otros")

                # Resolver Dashboard activo del usuario
                dashboard_id = 1
                dashboard_name = "Principal"
                if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
                    try:
                        from dashboard.models import UserFinanceDashboard
                        user_dash = UserFinanceDashboard.objects.filter(user=user, is_active=True).first()
                        if user_dash:
                            dashboard_id = user_dash.id
                            dashboard_name = user_dash.name
                    except Exception:
                        pass

                return AgentActionResponse(
                    success=True,
                    thought=f"Propuesta de mutación generada para confirmación humana: {behavior} de ${amount} en '{concept}'.",
                    action_type="MUTATION_PROPOSAL",
                    data={
                        "widget_type": "action_confirmation",
                        "action": "CREATE_RECORD",
                        "behavior": behavior,
                        "record_type": behavior,
                        "amount": str(amount),
                        "description": concept,
                        "category_name": suggested_cat,
                        "dashboard_id": dashboard_id,
                        "dashboard_name": dashboard_name,
                        "record_date": str(date.today()),
                        "status": "PENDING_CONFIRMATION"
                    },
                    user_message=(
                        f"He preparado el borrador de este nuevo movimiento para ti:\n\n"
                        f"- 📝 **Tipo:** {tipo_label}\n"
                        f"- 💵 **Monto:** **${amount:,.2f} MXN**\n"
                        f"- 🏷️ **Categoría sugerida:** {suggested_cat}\n"
                        f"- 📌 **Concepto:** *\"{concept}\"*\n"
                        f"- 📂 **Espacio:** {dashboard_name}\n"
                        f"- 📅 **Fecha:** {date.today().strftime('%d/%m/%Y')}\n\n"
                        f"Por tu seguridad, **este movimiento aún no se ha guardado en tu base de datos**. Por favor verifica los datos y pulsa **Confirmar y Guardar** en la tarjeta inferior para registrarlo en tu cuenta."
                    )
                )

        return None

    # --------------------------------------------------------------------------
    # MANEJADORES DE RESPUESTAS (INTENT HANDLERS)
    # --------------------------------------------------------------------------

    def _handle_greeting_intent(self, user) -> AgentActionResponse:
        user_name = ""
        if user and hasattr(user, "get_short_name") and user.get_short_name():
            user_name = f", **{user.get_short_name()}**"
        elif user and hasattr(user, "email"):
            user_name = f", **{user.email.split('@')[0]}**"

        message = (
            f"👋 ¡Hola{user_name}! ¿Cómo estás?\n\n"
            f"Soy tu **Asistente Financiero GTOPagos**. Estoy conectado directamente con tus movimientos para ayudarte a tomar mejores decisiones.\n\n"
            f"¿Qué te gustaría revisar hoy?\n"
            f"- 📊 *\"¿Cuánto he gastado este mes?\"*\n"
            f"- 🚦 *\"¿Cuáles son mis pagos pendientes?\"*\n"
            f"- 🎯 *\"¿Cómo van mis metas de ahorro?\"*\n"
            f"- 💳 *\"Calcula una compra a meses sin intereses\"*"
        )

        return AgentActionResponse(
            success=True,
            thought="Saludo cálido y bienvenida contextual.",
            action_type="READ_ONLY",
            data={"widget_type": "assistant_capabilities", "capabilities": [
                {"title": "Resumen Financiero", "example": "¿Cuánto he gastado este mes?"},
                {"title": "Semáforo de Pagos", "example": "¿Cuáles son mis pagos más urgentes?"},
                {"title": "Metas de Ahorro", "example": "¿Cómo van mis metas de ahorro?"},
                {"title": "Cálculo de MSI", "example": "Compré una laptop de $15,000 a 12 meses sin intereses"}
            ]},
            user_message=message
        )

    def _handle_identity_intent(self) -> AgentActionResponse:
        message = (
            f"🤖 **¿Quién soy?**\n\n"
            f"Soy el **Asistente de IA Financiera de GTOPagos**, construido bajo una arquitectura de **Agentes Autónomos**, "
            f"**Spec-Driven Development (SDD)** y el protocolo estándar **Model Context Protocol (MCP)**.\n\n"
            f"A diferencia de un chat tradicional, **yo no invento cálculos matemáticos**. Cuando me pides proyecciones de cuotas, "
            f"flujo quincenal o semáforos de pago, ejecuto herramientas con precisión exacta de centavos.\n\n"
            f"¿En qué te puedo asesorar hoy?"
        )
        return AgentActionResponse(
            success=True,
            thought="Presentación de capacidades técnicas y de producto.",
            action_type="READ_ONLY",
            data={"widget_type": "assistant_capabilities", "capabilities": [
                {"title": "Cálculo de MSI", "example": "Compré una televisión de $8,000 a 6 meses"},
                {"title": "Flujo Quincenal", "example": "Gano 25,000 al mes, corte 15"},
                {"title": "Semáforo de Pagos", "example": "Semáforo de vencimientos"}
            ]},
            user_message=message
        )

    def _handle_system_audit_intent(self, user) -> AgentActionResponse:
        """
        Ejecuta una auditoría financiera 360° holística sobre todos los registros
        (ingresos, gastos, gastos recurrentes, deudas/MSI) y metas de ahorro del usuario.
        """
        if not user or not hasattr(user, "is_authenticated") or not user.is_authenticated:
            return AgentActionResponse(
                success=True,
                thought="Usuario no autenticado para auditoría integral.",
                action_type="READ_ONLY",
                data={"widget_type": "info_banner"},
                user_message="Para realizar una auditoría integral 360° de tus finanzas (ingresos, gastos fijos, cuotas y metas de ahorro), por favor inicia sesión en tu cuenta de GTOPagos."
            )

        try:
            from finance.models import FinancialRecord, FinancialGoal

            user_name = "Usuario"
            if hasattr(user, "get_short_name") and user.get_short_name():
                user_name = user.get_short_name()
            elif hasattr(user, "first_name") and user.first_name:
                user_name = user.first_name
            elif hasattr(user, "email"):
                user_name = user.email.split('@')[0]

            salary = Decimal('0.00')
            if hasattr(user, 'profile') and user.profile.salary:
                salary = user.profile.salary

            # Obtener registros activos
            records_qs = FinancialRecord.objects.filter(
                user=user,
                is_active=True
            ).select_related('record_type', 'category', 'payment_status')

            audit_records = []
            for r in records_qs:
                beh = r.record_type.behavior if r.record_type else "EXPENSE"
                cat_name = r.category.name if r.category else "Otros"
                status_name = r.payment_status.status if r.payment_status else "PAGADO"
                audit_records.append(
                    AuditRecordItem(
                        id=r.id,
                        description=r.description or (r.record_type.name if r.record_type else "Transacción"),
                        amount=r.amount,
                        behavior=beh,
                        category_name=cat_name,
                        record_date=r.record_date,
                        is_recurrent=bool(r.is_recurrent),
                        total_installments=r.total_installments,
                        current_installment=r.current_installment,
                        payment_status=status_name
                    )
                )

            # Obtener metas de ahorro
            goals_qs = FinancialGoal.objects.filter(user=user)
            audit_goals = []
            for g in goals_qs:
                audit_goals.append(
                    AuditGoalItem(
                        id=g.id,
                        name=g.name,
                        target_amount=g.target_amount,
                        saved_amount=g.saved_amount or Decimal('0.00'),
                        target_date=g.target_date
                    )
                )

            audit_input = SystemAuditInput(
                user_name=user_name,
                salary=salary,
                records=audit_records,
                goals=audit_goals
            )

            # Ejecutar herramienta en MCP Server
            response = self.mcp.call_tool("audit_financial_system", audit_input.model_dump())
            if isinstance(response.data, dict):
                response.data["widget_type"] = "system_audit"
                health_score = response.data.get("health_score", 0)
                health_status = response.data.get("health_status", "SALUDABLE")
                total_income = Decimal(str(response.data.get("total_income", "0")))
                total_expenses = Decimal(str(response.data.get("total_expenses", "0")))
                net_savings = Decimal(str(response.data.get("net_savings", "0")))
                savings_rate = response.data.get("savings_rate", "0")
                debt_burden = response.data.get("debt_burden_rate", "0")
                goals_list = response.data.get("goals_feasibility", [])
                viable_goals = sum(1 for g in goals_list if g.get("is_viable") or g.get("status") in ["VIABLE", "LOGRADA"])

                user_message = (
                    f"### 🧠 Diagnóstico Financiero 360° ({user_name})\n\n"
                    f"He auditado la totalidad de tus movimientos, cuotas recurrentes y metas registradas en el sistema:\n\n"
                    f"- 🎯 **Salud Financiera General:** **{health_score}/100 ({health_status})**\n"
                    f"- 💵 **Ingresos efectivos del periodo:** ${total_income:,.2f} MXN\n"
                    f"- 🔴 **Gastos totales consolidados:** ${total_expenses:,.2f} MXN\n"
                    f"- 🟢 **Margen de Ahorro Libre:** **${net_savings:,.2f} MXN** ({savings_rate}% de tu ingreso)\n"
                    f"- 💳 **Carga fija / cuotas comprometidas:** {debt_burden}% de tus gastos\n"
                    f"- 🏆 **Metas de Ahorro Viables:** **{viable_goals} de {len(goals_list)}** con tu margen actual\n\n"
                    f"A continuación te presento la radiografía completa de tu sistema con fugas de gasto y recomendaciones estratégicas:"
                )
                response.user_message = user_message

            return response

        except Exception as e:
            logger.error(f"Error executing 360 system audit: {e}", exc_info=True)
            return AgentActionResponse(
                success=False,
                thought=f"Error en auditoría 360°: {str(e)}",
                action_type="ALERT",
                data={"widget_type": "info_banner"},
                user_message="Ocurrió un inconveniente al auditar tus finanzas. Por favor intenta de nuevo en unos momentos."
            )

    def _handle_user_summary_intent(self, user, query: str) -> AgentActionResponse:
        """
        Consulta la base de datos real de Django para el usuario autenticado.
        """
        if not user or not hasattr(user, "is_authenticated") or not user.is_authenticated:
            return AgentActionResponse(
                success=True,
                thought="Usuario no autenticado para consultar balance.",
                action_type="READ_ONLY",
                data={"widget_type": "info_banner"},
                user_message="Para mostrarte tu saldo y resumen de gastos exactos necesitas iniciar sesión en tu cuenta de GTOPagos. Si lo deseas, puedes pedirme calcular compras a meses o simular un flujo de caja."
            )

        try:
            from finance.models import FinancialRecord
            from django.db.models import Sum

            today = date.today()
            first_day = today.replace(day=1)

            # Gastos del mes
            expenses_sum = FinancialRecord.objects.filter(
                user=user,
                is_active=True,
                record_type__behavior='EXPENSE',
                record_date__gte=first_day,
                record_date__lte=today
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            # Ingresos del mes
            incomes_sum = FinancialRecord.objects.filter(
                user=user,
                is_active=True,
                record_type__behavior='INCOME',
                record_date__gte=first_day,
                record_date__lte=today
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            balance = incomes_sum - expenses_sum

            # Salario registrado en perfil
            salary = Decimal('0.00')
            if hasattr(user, 'profile') and user.profile.salary:
                salary = user.profile.salary

            user_message = (
                f"### 📊 Resumen de tus Finanzas ({today.strftime('%B %Y').capitalize()})\n\n"
                f"- 🟢 **Ingresos registrados este mes:** ${incomes_sum:,.2f} MXN\n"
                f"- 🔴 **Gastos registrados este mes:** ${expenses_sum:,.2f} MXN\n"
                f"- ⚖️ **Balance neto:** **${balance:,.2f} MXN**\n\n"
            )

            if salary > Decimal('0.00'):
                user_message += f"- 💼 **Salario mensual base en perfil:** ${salary:,.2f} MXN\n\n"

            if balance >= Decimal('0.00'):
                user_message += "✨ Tienes un balance positivo este mes. Es un buen momento para destinar un porcentaje a tus metas de ahorro."
            else:
                user_message += "⚠️ Tus gastos superan tus ingresos este mes. Te sugiero revisar tus pagos pendientes o utilizar la regla 50/30/20 para equilibrar tu flujo."

            return AgentActionResponse(
                success=True,
                thought=f"Consulta de balance real ejecutada: Ingresos ${incomes_sum}, Gastos ${expenses_sum}, Balance ${balance}.",
                action_type="READ_ONLY",
                data={
                    "widget_type": "cashflow_gauge",
                    "total_income": str(incomes_sum),
                    "total_committed": str(expenses_sum),
                    "available_margin": str(balance),
                    "compromised_percentage": str(((expenses_sum / incomes_sum) * 100).quantize(Decimal('0.01'))) if incomes_sum > 0 else "0",
                    "risk_level": "BAJO" if balance >= 0 else "ALTO",
                    "cutoff_day": today.day
                },
                user_message=user_message
            )
        except Exception as e:
            logger.error(f"Error consulting user balance: {e}")
            return AgentActionResponse(
                success=False,
                thought=f"Error consultando balance: {str(e)}",
                action_type="ALERT",
                data={"widget_type": "info_banner"},
                user_message="Ocurrió un inconveniente al consultar tu resumen financiero. Por favor intenta de nuevo en unos momentos."
            )

    def _handle_user_goals_intent(self, user) -> AgentActionResponse:
        """
        Consulta las metas de ahorro reales del usuario en Django.
        """
        if not user or not hasattr(user, "is_authenticated") or not user.is_authenticated:
            return AgentActionResponse(
                success=True,
                thought="Usuario no autenticado para consultar metas.",
                action_type="READ_ONLY",
                data={"widget_type": "info_banner"},
                user_message="Inicia sesión para poder consultar el progreso de tus metas de ahorro registradas."
            )

        try:
            from finance.models import FinancialGoal
            goals = FinancialGoal.objects.filter(user=user).order_by('-created_at')[:5]

            if not goals.exists():
                return AgentActionResponse(
                    success=True,
                    thought="El usuario no tiene metas de ahorro registradas.",
                    action_type="READ_ONLY",
                    data={"widget_type": "info_banner"},
                    user_message="🎯 Aún no tienes metas de ahorro registradas. Puedes crear una nueva meta desde el módulo **Metas** en el menú lateral para empezar a monitorear tu progreso."
                )

            user_message = f"### 🎯 Tus Metas de Ahorro\n\n"
            breakdown = []
            for g in goals:
                pct = int((g.saved_amount / g.target_amount) * 100) if g.target_amount > 0 else 0
                user_message += (
                    f"- **{g.name}:** ${g.saved_amount:,.2f} de ${g.target_amount:,.2f} MXN (**{pct}%**)\n"
                )
                breakdown.append({
                    "pct": pct,
                    "label": g.name,
                    "desc": f"${g.saved_amount:,.2f} de ${g.target_amount:,.2f} MXN"
                })

            user_message += "\n💡 *Tip:* Para alcanzar tus metas más rápido, programa transferencias fijas en cuanto recibas tu quincena."

            return AgentActionResponse(
                success=True,
                thought=f"Se consultaron {len(breakdown)} metas del usuario.",
                action_type="READ_ONLY",
                data={
                    "widget_type": "financial_tips",
                    "breakdown": breakdown
                },
                user_message=user_message
            )
        except Exception as e:
            logger.error(f"Error consulting user goals: {e}")
            return AgentActionResponse(
                success=False,
                thought=f"Error consultando metas: {str(e)}",
                action_type="ALERT",
                data={"widget_type": "info_banner"},
                user_message="No fue posible consultar tus metas en este momento. Inténtalo de nuevo más tarde."
            )

    def _handle_due_date_priority_intent(self, user, query: str) -> AgentActionResponse:
        today = date.today()
        items = []

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

        # Si el usuario no está autenticado (modo demo/invitado), mostrar simulación interactiva
        if not items and (not user or not getattr(user, 'is_authenticated', False)):
            items = [
                DueDateItem(id=1, concept="Tarjeta de Crédito (Corte)", amount=Decimal('3450.00'), due_date=today + timedelta(days=2)),
                DueDateItem(id=2, concept="Servicio de Luz (CFE)", amount=Decimal('480.00'), due_date=today + timedelta(days=5)),
                DueDateItem(id=3, concept="Servicio de Internet", amount=Decimal('649.00'), due_date=today + timedelta(days=11)),
                DueDateItem(id=4, concept="Cuota Crédito Auto", amount=Decimal('4200.00'), due_date=today + timedelta(days=19)),
            ]

        # Si el usuario está autenticado y realmente no tiene deudas pendientes
        if not items:
            return AgentActionResponse(
                success=True,
                thought="El usuario no tiene pagos pendientes en su cuenta.",
                action_type="READ_ONLY",
                data={"widget_type": "info_banner"},
                user_message="🎉 **¡Excelente noticia!** No tienes pagos ni deudas pendientes registradas en tu cuenta en este momento.\n\nCuando registres compromisos o compras a crédito en tu Dashboard con estado **Pendiente**, aquí aparecerán clasificados por urgencia de vencimiento."
            )

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
            f"*(Consulta la tabla abajo para ver el orden de prioridad recomendado)*"
        )

        return AgentActionResponse(
            success=True,
            thought=f"Priorización ejecutada con {len(items)} registros reales.",
            action_type="READ_ONLY",
            data=data,
            user_message=user_message
        )

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

    def _handle_cashflow_intent(self, text: str, user) -> AgentActionResponse:
        salary_match = re.search(r'(?:gano|salario|ingreso|sueldo|de)\s*(?:\$)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+)', text, re.IGNORECASE)
        if salary_match:
            try:
                salary = Decimal(salary_match.group(1).replace(',', ''))
            except InvalidOperation:
                salary = Decimal('20000.00')
        elif user and hasattr(user, 'profile') and user.profile.salary:
            salary = user.profile.salary
        else:
            salary = Decimal('20000.00')

        cutoff = 30 if any(k in text for k in ["30", "segunda quincena", "fin de mes"]) else 15

        # Obtener compromisos reales del usuario si existen
        obligations = []
        if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
            try:
                from finance.models import FinancialRecord
                recs = FinancialRecord.objects.filter(
                    user=user,
                    is_active=True,
                    record_type__behavior='EXPENSE'
                ).exclude(payment_status__status__iexact='PAGADO')[:10]
                for r in recs:
                    obligations.append(PendingObligation(
                        description=r.description or f"Gasto #{r.id}",
                        amount=r.amount,
                        due_date=r.record_date
                    ))
            except Exception:
                pass

        if not obligations:
            # Si no hay compromisos registrados, calcular el margen quincenal neto
            fortnight_income = (salary / Decimal('2.00'))
            user_message = (
                f"### 📊 Proyección de Flujo de Caja (Corte {cutoff})\n\n"
                f"- **Ingreso Quincenal Estimado:** ${fortnight_income:,.2f} MXN (basado en un salario de ${salary:,.2f})\n"
                f"- **Compromisos pendientes registrados:** $0.00 MXN\n"
                f"- **Margen Libre:** **${fortnight_income:,.2f} MXN**\n\n"
                f"✨ Tu flujo está 100% libre en esta quincena. ¡Excelente momento para abonar a tus ahorros!"
            )
            return AgentActionResponse(
                success=True,
                thought="Flujo de caja calculado sin deudas pendientes registradas.",
                action_type="CALCULATION",
                data={
                    "widget_type": "cashflow_gauge",
                    "cutoff_day": cutoff,
                    "total_income": str(fortnight_income),
                    "total_committed": "0.00",
                    "available_margin": str(fortnight_income),
                    "compromised_percentage": "0.00",
                    "risk_level": "BAJO"
                },
                user_message=user_message
            )

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
            f"{data.get('risk_alert') or '✨ Tienes un flujo saludable para cubrir tus compromisos e impulsar tu ahorro.'}"
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
            f"El concepto **\"{data['original_text']}\"** corresponde a:\n\n"
            f"📂 **{data['suggested_category']}** *(Tipo: {data['behavior']})*\n"
            f"🎯 Confianza: **{confidence_pct}%**\n\n"
            f"Puedes seleccionar esta categoría directamente al crear tu movimiento en el Dashboard."
        )

        return AgentActionResponse(
            success=True,
            thought=f"Concepto '{description}' categorizado como '{data['suggested_category']}'.",
            action_type="READ_ONLY",
            data=data,
            user_message=user_message
        )

    def _match_financial_advice(self, text: str) -> Optional[AgentActionResponse]:
        """
        Respuestas educativas y detalladas para conceptos financieros comunes.
        """
        # Regla 50/30/20
        if any(k in text for k in ["50/30/20", "50-30-20", "regla 50", "como distribuir mi sueldo"]):
            return AgentActionResponse(
                success=True,
                thought="Explicación de la regla 50/30/20.",
                action_type="READ_ONLY",
                data={
                    "widget_type": "financial_tips",
                    "breakdown": [
                        {"pct": 50, "label": "Necesidades Básicas", "desc": "Renta/hipoteca, despensa, luz, agua, transporte indispensable."},
                        {"pct": 30, "label": "Deseos y Calidad de Vida", "desc": "Salidas a comer, suscripciones streaming, viajes y compras personales."},
                        {"pct": 20, "label": "Ahorro e Inversión", "desc": "Fondo de emergencia, aportaciones a retiro o liquidación acelerada de deudas."}
                    ]
                },
                user_message=(
                    f"### 💡 La Regla 50/30/20: Tu Guía de Presupuesto\n\n"
                    f"Es un método simple y efectivo para distribuir tus ingresos mensuales:\n\n"
                    f"1. **50% en Necesidades Básicas:** Lo que requieres sí o sí para vivir.\n"
                    f"2. **30% en Deseos:** Actividades recreativas y compras de confort.\n"
                    f"3. **20% en Ahorro y Deudas:** La base para tu libertad financiera futura.\n\n"
                    f"📌 *Recomendación:* Si tus deudas superan el 20%, ajusta temporalmente el rubro de 'Deseos' al 15% para liquidar pasivos más rápido."
                )
            )

        # Fondo de emergencia
        if any(k in text for k in ["fondo de emergencia", "fondo de reserva", "ahorro de emergencia"]):
            return AgentActionResponse(
                success=True,
                thought="Explicación sobre fondo de emergencia.",
                action_type="READ_ONLY",
                data={"widget_type": "info_banner"},
                user_message=(
                    f"### 🛡️ ¿Qué es un Fondo de Emergencia y cuánto necesitas?\n\n"
                    f"Un **Fondo de Emergencia** es una reserva de dinero líquido destinada únicamente a cubrir imprevistos graves (desempleo, gastos médicos, reparaciones urgentes).\n\n"
                    f"- **Monto ideal:** Entre **3 y 6 meses de tus gastos fijos indispensables**.\n"
                    f"- **¿Dónde guardarlo?** En instrumentos de alta liquidez y bajo riesgo (ej: Cetesdirecto o cuentas con rendimiento diario a la vista).\n"
                    f"- **Regla de oro:** No lo inviertas en renta variable ni lo tengas en tu tarjeta de uso diario para evitar la tentación de gastarlo."
                )
            )

        # Estrategia de pago de deudas (Avalancha vs Bola de Nieve)
        if any(k in text for k in ["salir de deudas", "pagar deudas", "bola de nieve", "metodo avalancha", "método avalancha"]):
            return AgentActionResponse(
                success=True,
                thought="Explicación de métodos de amortización de deudas.",
                action_type="READ_ONLY",
                data={"widget_type": "info_banner"},
                user_message=(
                    f"### 🚀 Las 2 Mejores Estrategias para Salir de Deudas\n\n"
                    f"1. **Método Bola de Nieve (Psicológico):**\n"
                    f"   - Pagas el mínimo en todas tus deudas y abonas todo el extra a la deuda con el **menor saldo total**.\n"
                    f"   - Al liquidarla rápido, obtienes victorias inmediatas que te motivan a continuar.\n\n"
                    f"2. **Método Avalancha (Matemático - El más eficiente):**\n"
                    f"   - Pagas el mínimo en todas tus deudas y abonas todo el extra a la deuda con la **tasa de interés (CAT) más alta**.\n"
                    f"   - Te ahorra la mayor cantidad de dinero en intereses a largo plazo."
                )
            )

        # Gastos hormiga
        if any(k in text for k in ["gastos hormiga", "gasto hormiga", "fuga de dinero"]):
            return AgentActionResponse(
                success=True,
                thought="Consejos sobre gastos hormiga.",
                action_type="READ_ONLY",
                data={"widget_type": "info_banner"},
                user_message=(
                    f"### 🐜 ¿Cómo detener los Gastos Hormiga?\n\n"
                    f"Los gastos hormiga son pequeñas compras diarias que parecen insignificantes (un café de $65, propinas, snacks, comisiones de apps) pero que pueden sumar **$1,500 a $3,500 MXN mensuales**.\n\n"
                    f"- ☕ **Prepara en casa:** Café matutino y snacks para el trabajo.\n"
                    f"- 📱 **Audita tus suscripciones:** Cancela plataformas que no hayas usado en los últimos 30 días.\n"
                    f"- ⏱️ **Regla de las 48 horas:** Si ves algo no esencial que quieres comprar, espera 48 horas antes de pagar. En la mayoría de casos el impulso desaparece."
                )
            )

        return None

    def _ask_gemini_llm(self, query: str, user, api_key: str) -> Optional[AgentActionResponse]:
        """
        Llama al modelo Gemini 1.5 Flash (Free Tier) de Google para responder de forma conversacional y profunda.
        """
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            user_ctx = ""
            if user and hasattr(user, 'email'):
                user_ctx = f"Usuario actual: {user.email}. "

            system_instruction = (
                "Eres el Asistente Financiero Inteligente y Exclusivo de la plataforma GTOPagos. "
                "Tu conocimiento está ESTRICTAMENTE LIMITADO a finanzas personales, presupuestos, contabilidad, "
                "deudas, ahorro, inversiones y la operación del sistema GTOPagos. "
                "Si el usuario pregunta sobre temas ajenos a finanzas (deportes, chismes, política, cultura pop o tareas escolares), "
                "declina cortésmente diciendo: 'Como asistente financiero de GTOPagos, solo estoy capacitado para responder dudas sobre finanzas y la plataforma GTOPagos.' "
                "Responde siempre en español de forma cortés, estructurada y profesional con Markdown y emojis. "
                "No inventes cálculos matemáticos de préstamos; si te piden calcular cuotas, diles que utilicen el formato 'Compré X a Y meses'."
            )

            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"Contexto: {system_instruction} {user_ctx}\nConsulta del usuario: {query}"}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 800,
                }
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                candidates = res_data.get('candidates', [])
                if candidates:
                    text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                    if text:
                        return AgentActionResponse(
                            success=True,
                            thought="Respuesta generada mediante Gemini 1.5 Flash.",
                            action_type="READ_ONLY",
                            data={"widget_type": "info_banner"},
                            user_message=text
                        )
        except Exception as e:
            logger.warning(f"Error calling Gemini LLM: {e}")
        return None

    def _handle_smart_conversational_fallback(self, query: str, user) -> AgentActionResponse:
        """
        Guardrail de Dominio Cerrado: Asegura que el agente solo hable de temas financieros
        y de la plataforma GTOPagos, guiando al usuario a las funciones del sistema.
        """
        user_name = ""
        if user and hasattr(user, "get_short_name") and user.get_short_name():
            user_name = f", {user.get_short_name()}"

        message = (
            f"Hola{user_name}. Como **Asistente Financiero Especializado de GTOPagos**, mi alcance está enfocado exclusivamente en la gestión de tu dinero, presupuestos y herramientas de la plataforma.\n\n"
            f"No puedo responder dudas sobre temas ajenos a finanzas, pero con gusto puedo ayudarte en:\n\n"
            f"- ➕ **Registrar Movimientos:** *\"Registra un gasto de $450 en Uber\"* o *\"Añade un ingreso de $15,000 de nómina\"*\n"
            f"- 📊 **Tus Cuentas:** *\"¿Cuánto he gastado este mes?\"* o *\"Mi balance actual\"*\n"
            f"- 🚦 **Deudas y Pagos:** *\"Semáforo de vencimientos\"* o *\"Pagos pendientes\"*\n"
            f"- 💳 **Meses Sin Intereses:** *\"Compré una laptop de $12,000 a 12 meses\"*\n"
            f"- 🎯 **Metas de Ahorro:** *\"¿Cómo van mis metas?\"*\n"
            f"- 🧠 **Diagnóstico 360°:** *\"Analiza todo el sistema con mis gastos e ingresos y metas\"*\n\n"
            f"¿Qué movimiento o consulta financiera deseas realizar?"
        )

        return AgentActionResponse(
            success=True,
            thought="Guardrail de dominio cerrado aplicado. Redirección a capacidades financieras de GTOPagos.",
            action_type="READ_ONLY",
            data={
                "widget_type": "assistant_capabilities",
                "capabilities": [
                    {"title": "Registrar Gasto", "example": "Registra un gasto de $350 en Oxxo"},
                    {"title": "Auditoría 360°", "example": "Analiza todo el sistema con mis gastos e ingresos y metas"},
                    {"title": "Semáforo de Pagos", "example": "Semáforo de vencimientos"},
                    {"title": "Cálculo de MSI", "example": "Compré una laptop de $12,000 a 12 meses"}
                ]
            },
            user_message=message
        )


# Singleton
ai_orchestrator = FinancialAIOrchestrator()
