"""
GTOPagos MCP (Model Context Protocol) Server
Servidor estándar JSON-RPC para exponer Tools y Resources financieros a LLMs y Runtimes de IA.
Compatible con el protocolo de Anthropic y clientes MCP.
"""
import json
import sys
from decimal import Decimal
from datetime import date
from typing import Dict, Any, List, Optional

from agent.specs.schemas import (
    MSICalculatorInput,
    CashflowForecastInput,
    DueDatePriorityInput,
    CategorizerInput,
    CreateRecordToolInput,
    UpdateRecordStatusToolInput,
    SystemAuditInput,
    AgentActionResponse
)
from agent.skills.msi_calculator import calculate_msi_projection
from agent.skills.cashflow_forecast import forecast_cashflow
from agent.skills.due_date_priority import prioritize_due_dates
from agent.skills.categorizer import categorize_expense
from agent.skills.financial_auditor import audit_financial_system


class GTOPagosMCPServer:
    """
    Servidor MCP desacoplado que expone herramientas financieras y recursos
    con validación de contratos (SDD) y guardrails de seguridad.
    """

    def __init__(self):
        self.server_name = "gtopagos-financial-mcp"
        self.version = "1.0.0"
        self._tools = {}
        self._resources = {}
        self._register_default_tools()
        self._register_default_resources()

    def _register_default_tools(self):
        # 1. Herramienta de cálculo de cuotas MSI
        self.register_tool(
            name="calculate_msi_projection",
            description="Calcula tabla de amortización, cuotas mensuales/quincenales y saldo pendiente para compras a Meses Sin Intereses (MSI).",
            handler=self._handle_msi_projection
        )

        # 2. Herramienta de proyección de flujo de caja
        self.register_tool(
            name="forecast_cashflow",
            description="Evalúa solvencia y porcentaje de ingresos comprometidos para la quincena (corte 15 o 30) frente al salario.",
            handler=self._handle_cashflow_forecast
        )

        # 3. Herramienta de priorización de vencimientos
        self.register_tool(
            name="prioritize_due_dates",
            description="Clasifica deudas y compromisos pendientes con semáforo de urgencia (<=3 días crítico, etc.).",
            handler=self._handle_due_date_priority
        )

        # 4. Herramienta de categorización inteligente
        self.register_tool(
            name="categorize_expense",
            description="Determina la categoría sugerida y tipo de movimiento a partir de una descripción o concepto.",
            handler=self._handle_categorize
        )

        # 5. Herramienta de actualización de estado de pago (con Guardrail)
        self.register_tool(
            name="update_record_status",
            description="Actualiza el estado de un compromiso financiero a PAGADO o CANCELADO respetando la regla de inmutabilidad.",
            handler=self._handle_update_status
        )

        # 6. Herramienta de auditoría integral y diagnóstico 360°
        self.register_tool(
            name="audit_financial_system",
            description="Audita integralmente ingresos, gastos por categoría, compras a meses y viabilidad de metas de ahorro, calculando el Financial Health Score (0-100).",
            handler=self._handle_system_audit
        )

        # 7. Herramienta de creación de registro financiero
        self.register_tool(
            name="create_record",
            description="Crea un nuevo registro de ingreso, gasto o transferencia en el dashboard del usuario.",
            handler=self._handle_create_record
        )

    def _register_default_resources(self):
        self.register_resource(
            uri="finance://standards/rules",
            name="Reglas de Negocio del Sistema",
            mime_type="application/yaml",
            reader=lambda: "agent_spec.yaml (Reglas de negocio y guardrails de GTOPagos)"
        )

    def register_tool(self, name: str, description: str, handler):
        self._tools[name] = {
            "name": name,
            "description": description,
            "handler": handler
        }

    def register_resource(self, uri: str, name: str, mime_type: str, reader):
        self._resources[uri] = {
            "uri": uri,
            "name": name,
            "mime_type": mime_type,
            "reader": reader
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {"name": t["name"], "description": t["description"]}
            for t in self._tools.values()
        ]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> AgentActionResponse:
        if name not in self._tools:
            return AgentActionResponse(
                success=False,
                thought=f"Herramienta '{name}' no encontrada.",
                action_type="ALERT",
                data={},
                user_message=f"Error: La herramienta '{name}' no está registrada en el servidor MCP."
            )

        try:
            return self._tools[name]["handler"](arguments)
        except Exception as e:
            return AgentActionResponse(
                success=False,
                thought=f"Excepción en ejecución de herramienta: {str(e)}",
                action_type="ALERT",
                data={"error": str(e)},
                user_message=f"Ocurrió un error al procesar la operación: {str(e)}"
            )

    # --- Handlers de Herramientas ---

    def _handle_msi_projection(self, args: Dict[str, Any]) -> AgentActionResponse:
        validated_input = MSICalculatorInput(**args)
        result = calculate_msi_projection(validated_input)
        
        user_msg = (
            f"Tu compra de ${result.total_amount:,.2f} a {result.total_installments} MSI "
            f"tiene una cuota mensual de ${result.monthly_installment:,.2f} (${result.biweekly_installment:,.2f} quincenal). "
            f"Llevas pagados ${result.amount_paid_so_far:,.2f} y te resta un saldo de ${result.remaining_balance:,.2f} "
            f"en {result.remaining_installments} cuotas restantes."
        )

        return AgentActionResponse(
            success=True,
            thought=f"Cálculo MSI completado. Cuota mensual: ${result.monthly_installment}",
            action_type="CALCULATION",
            data=result.model_dump(mode='json'),
            user_message=user_msg
        )

    def _handle_cashflow_forecast(self, args: Dict[str, Any]) -> AgentActionResponse:
        validated_input = CashflowForecastInput(**args)
        result = forecast_cashflow(validated_input)

        alert_text = f" {result.risk_alert}" if result.risk_alert else ""
        user_msg = (
            f"Para el corte del día {result.cutoff_day}: Tienes un ingreso quincenal de ${result.total_income:,.2f} "
            f"y compromisos por ${result.total_committed:,.2f} ({result.compromised_percentage}% comprometido). "
            f"Tu margen libre estimado es de ${result.available_margin:,.2f} (Nivel de riesgo: {result.risk_level}).{alert_text}"
        )

        return AgentActionResponse(
            success=True,
            thought=f"Flujo de caja analizado. Margen libre: ${result.available_margin}, Riesgo: {result.risk_level}",
            action_type="ALERT" if result.risk_level in ["ALTO", "CRÍTICO"] else "CALCULATION",
            data=result.model_dump(mode='json'),
            user_message=user_msg
        )

    def _handle_due_date_priority(self, args: Dict[str, Any]) -> AgentActionResponse:
        validated_input = DueDatePriorityInput(**args)
        result = prioritize_due_dates(validated_input)

        crit_count = result.critical_count
        user_msg = (
            f"Se analizaron {len(result.prioritized_list)} compromisos pendientes por un total de ${result.total_pending_amount:,.2f}. "
            f"Tienes {crit_count} pagos en estado crítico o vencido que requieren atención inmediata."
        )

        return AgentActionResponse(
            success=True,
            thought=f"Vencimientos priorizados. Total críticos: {crit_count}",
            action_type="READ_ONLY",
            data=result.model_dump(mode='json'),
            user_message=user_msg
        )

    def _handle_categorize(self, args: Dict[str, Any]) -> AgentActionResponse:
        validated_input = CategorizerInput(**args)
        result = categorize_expense(validated_input)

        user_msg = (
            f"El concepto '{result.original_text}' fue clasificado como '{result.suggested_category}' "
            f"({result.behavior}) con confianza del {int(result.confidence * 100)}%."
        )

        return AgentActionResponse(
            success=True,
            thought=f"Categorización semántica completada: {result.suggested_category}",
            action_type="READ_ONLY",
            data=result.model_dump(mode='json'),
            user_message=user_msg
        )

    def _handle_update_status(self, args: Dict[str, Any]) -> AgentActionResponse:
        validated_input = UpdateRecordStatusToolInput(**args)
        rec_id = validated_input.record_id
        target = validated_input.target_status.upper()

        # Simulación de verificación de Guardrail (IMMUTABLE_PAID_STATUS)
        # En producción se consulta `FinancialRecord.objects.get(id=rec_id)`
        if args.get("current_status") == "PAGADO":
            return AgentActionResponse(
                success=False,
                thought="Violación de Guardrail: El registro ya está marcado como PAGADO y es inmutable.",
                action_type="ALERT",
                data={"record_id": rec_id, "guardrail_triggered": "IMMUTABLE_PAID_STATUS"},
                user_message="⚠️ Acción bloqueada por regla de seguridad: Los registros con estado PAGADO no pueden ser modificados."
            )

        return AgentActionResponse(
            success=True,
            thought=f"Registro #{rec_id} actualizado a estado {target}.",
            action_type="MUTATION",
            data={"record_id": rec_id, "new_status": target},
            user_message=f"Listo, el registro #{rec_id} ha sido marcado como {target} exitosamente."
        )

    def _handle_system_audit(self, args: Dict[str, Any]) -> AgentActionResponse:
        validated_input = SystemAuditInput(**args)
        result = audit_financial_system(validated_input)
        data = result.model_dump(mode='json')
        data["widget_type"] = "system_audit"

        return AgentActionResponse(
            success=True,
            thought=f"Diagnóstico 360° completado. Score: {result.health_score}/100 ({result.health_status}).",
            action_type="READ_ONLY",
            data=data,
            user_message=result.summary_text
        )

    def _handle_create_record(self, args: Dict[str, Any]) -> AgentActionResponse:
        validated_input = CreateRecordToolInput(**args)
        
        try:
            from finance.models import FinancialRecord, FinancialRecordType, Category
            from dashboard.models import UserFinanceDashboard
            from payments.models import PaymentStatus, PaymentMethod

            dashboard = UserFinanceDashboard.objects.filter(id=validated_input.dashboard_id).first()
            if not dashboard:
                return AgentActionResponse(
                    success=False,
                    thought="Dashboard no encontrado para crear registro.",
                    action_type="ALERT",
                    data={"error": "DASHBOARD_NOT_FOUND"},
                    user_message="No se encontró el espacio de trabajo o dashboard especificado."
                )

            user = dashboard.user

            # Resolver record_type
            record_type = FinancialRecordType.objects.filter(behavior=validated_input.record_type).first()
            if not record_type:
                record_type = FinancialRecordType.objects.first()

            # Resolver categoría
            category = None
            if validated_input.category_id:
                category = Category.objects.filter(id=validated_input.category_id).first()
            elif validated_input.category_name:
                category = Category.objects.filter(name__iexact=validated_input.category_name, record_type=record_type).first()
                if not category:
                    category = Category.objects.filter(name__icontains=validated_input.category_name, record_type=record_type).first()
            
            if not category and record_type:
                category = Category.objects.filter(record_type=record_type).first()

            # Resolver payment_status
            status_code = validated_input.payment_status_code or "PAID"
            payment_status = PaymentStatus.objects.filter(code__iexact=status_code).first()
            if not payment_status:
                payment_status = PaymentStatus.objects.filter(status__icontains="pagado").first() or PaymentStatus.objects.first()

            # Resolver payment_method
            payment_method = None
            if validated_input.payment_method_id:
                payment_method = PaymentMethod.objects.filter(id=validated_input.payment_method_id).first()
            else:
                payment_method = PaymentMethod.objects.first()

            rec = FinancialRecord.objects.create(
                user=user,
                dashboard=dashboard,
                record_type=record_type,
                category=category,
                payment_method=payment_method,
                payment_status=payment_status,
                amount=validated_input.amount,
                description=validated_input.description,
                record_date=validated_input.record_date,
                is_recurrent=validated_input.is_recurrent,
                total_installments=validated_input.total_installments,
                current_installment=validated_input.current_installment,
                is_active=True
            )

            tipo_str = "Ingreso" if validated_input.record_type == "INCOME" else "Gasto"
            cat_str = f" en categoría **{category.name}**" if category else ""

            return AgentActionResponse(
                success=True,
                thought=f"Registro #{rec.id} creado exitosamente en dashboard '{dashboard.name}'.",
                action_type="MUTATION",
                data={
                    "record_id": rec.id,
                    "amount": str(rec.amount),
                    "behavior": validated_input.record_type,
                    "description": rec.description,
                    "category_name": category.name if category else "General",
                    "dashboard_id": dashboard.id,
                    "dashboard_name": dashboard.name,
                    "record_date": str(rec.record_date)
                },
                user_message=f"✅ **{tipo_str} registrado con éxito:** ${rec.amount:,.2f} MXN por *\"{rec.description}\"*{cat_str} en tu espacio **{dashboard.name}**."
            )
        except Exception as e:
            return AgentActionResponse(
                success=False,
                thought=f"Error creando registro: {str(e)}",
                action_type="ALERT",
                data={"error": str(e)},
                user_message=f"Ocurrió un error al registrar el movimiento: {str(e)}"
            )

    # --- Dispatcher JSON-RPC 2.0 ---
    def handle_json_rpc(self, request_str: str) -> str:
        try:
            req = json.loads(request_str)
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            if method == "tools/list":
                res_data = {"tools": self.list_tools()}
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                action_res = self.call_tool(tool_name, tool_args)
                res_data = action_res.model_dump(mode='json')
            else:
                return json.dumps({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Método '{method}' no soportado."}
                })

            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": res_data
            })
        except Exception as e:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": f"Error interno JSON-RPC: {str(e)}"}
            })


# Instancia singleton del servidor MCP
mcp_server = GTOPagosMCPServer()

if __name__ == "__main__":
    # Modo stdio interactivo para clientes MCP estándar
    print(f"[{mcp_server.server_name} v{mcp_server.version}] Servidor MCP iniciado.", file=sys.stderr)
    for line in sys.stdin:
        if line.strip():
            sys.stdout.write(mcp_server.handle_json_rpc(line) + "\n")
            sys.stdout.flush()
