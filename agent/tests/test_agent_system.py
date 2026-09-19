"""
GTOPagos Agent System - Unit & Integration Test Suite
Valida:
1. Skills financieras (MSI, Cashflow, DueDate, Categorizer) con precisión de centavos.
2. Contratos y validaciones Pydantic v2 (SDD).
3. Servidor MCP (listado de herramientas, llamada de herramientas, JSON-RPC 2.0).
4. Guardrails de seguridad (inmutabilidad de estados PAGADO).
"""
import unittest
import json
from decimal import Decimal
from datetime import date, timedelta
from pydantic import ValidationError

from agent.specs.schemas import (
    MSICalculatorInput,
    CashflowForecastInput,
    DueDatePriorityInput,
    CategorizerInput,
    PendingObligation,
    DueDateItem,
    UpdateRecordStatusToolInput,
    AuditRecordItem,
    AuditGoalItem,
    SystemAuditInput,
)
from agent.skills.msi_calculator import calculate_msi_projection
from agent.skills.cashflow_forecast import forecast_cashflow
from agent.skills.due_date_priority import prioritize_due_dates
from agent.skills.categorizer import categorize_expense
from agent.skills.financial_auditor import audit_financial_system
from agent.mcp_server.server import GTOPagosMCPServer


class TestMSICalculatorSkill(unittest.TestCase):
    def test_standard_msi_calculation(self):
        payload = MSICalculatorInput(
            total_amount=Decimal('12000.00'),
            total_installments=12,
            current_installment=4
        )
        result = calculate_msi_projection(payload)
        self.assertEqual(result.monthly_installment, Decimal('1000.00'))
        self.assertEqual(result.biweekly_installment, Decimal('500.00'))
        self.assertEqual(result.amount_paid_so_far, Decimal('3000.00'))  # Cuotas 1, 2, 3 pagadas
        self.assertEqual(result.remaining_balance, Decimal('9000.00'))
        self.assertEqual(result.remaining_installments, 9)
        self.assertFalse(result.is_fully_paid)
        self.assertEqual(len(result.schedule), 12)

    def test_rounding_penny_adjustment(self):
        # $100 en 3 meses -> 33.33 * 2 + 33.34 = 100.00
        payload = MSICalculatorInput(
            total_amount=Decimal('100.00'),
            total_installments=3,
            current_installment=1
        )
        result = calculate_msi_projection(payload)
        total_schedule = sum(item.amount for item in result.schedule)
        self.assertEqual(total_schedule, Decimal('100.00'))

    def test_validation_guards(self):
        # Total amount must be positive
        with self.assertRaises(ValidationError):
            MSICalculatorInput(total_amount=Decimal('-500.00'), total_installments=6)

        # Total installments must be >= 2
        with self.assertRaises(ValidationError):
            MSICalculatorInput(total_amount=Decimal('500.00'), total_installments=0)


class TestCashflowForecastSkill(unittest.TestCase):
    def test_low_risk_cashflow(self):
        items = [
            PendingObligation(description="CFE", amount=Decimal('500.00'), due_date=date(2026, 9, 10)),
            PendingObligation(description="Internet", amount=Decimal('600.00'), due_date=date(2026, 9, 12)),
        ]
        payload = CashflowForecastInput(
            salary=Decimal('20000.00'),  # Quincenal = 10000
            cutoff_day=15,
            obligations=items
        )
        result = forecast_cashflow(payload)
        self.assertEqual(result.total_committed, Decimal('1100.00'))
        self.assertEqual(result.available_margin, Decimal('8900.00'))
        self.assertEqual(result.risk_level, "BAJO")
        self.assertIsNone(result.risk_alert)

    def test_critical_risk_cashflow(self):
        items = [
            PendingObligation(description="Renta", amount=Decimal('9500.00'), due_date=date(2026, 9, 14)),
        ]
        payload = CashflowForecastInput(
            salary=Decimal('18000.00'),  # Quincenal = 9000
            cutoff_day=15,
            obligations=items
        )
        result = forecast_cashflow(payload)
        self.assertTrue(result.compromised_percentage > Decimal('90.00'))
        self.assertEqual(result.risk_level, "CRÍTICO")
        self.assertIsNotNone(result.risk_alert)


class TestDueDatePrioritySkill(unittest.TestCase):
    def test_urgency_classification(self):
        today = date(2026, 9, 18)
        items = [
            DueDateItem(id=1, concept="Tarjeta BBVA", amount=Decimal('1500.00'), due_date=today + timedelta(days=2)),
            DueDateItem(id=2, concept="Luz", amount=Decimal('400.00'), due_date=today + timedelta(days=5)),
            DueDateItem(id=3, concept="Netflix", amount=Decimal('200.00'), due_date=today + timedelta(days=12)),
            DueDateItem(id=4, concept="Préstamo", amount=Decimal('3000.00'), due_date=today - timedelta(days=1)),
            DueDateItem(id=5, concept="Gym (Pagado)", amount=Decimal('600.00'), due_date=today, is_paid=True),
        ]
        payload = DueDatePriorityInput(reference_date=today, items=items)
        result = prioritize_due_dates(payload)

        self.assertEqual(len(result.prioritized_list), 4)  # Ignora el pagado
        # Primero debe ser el vencido
        self.assertEqual(result.prioritized_list[0].priority, "VENCIDO")
        self.assertEqual(result.prioritized_list[1].priority, "CRÍTICO")
        self.assertEqual(result.prioritized_list[2].priority, "URGENTE")
        self.assertEqual(result.prioritized_list[3].priority, "PRÓXIMO")
        self.assertEqual(result.critical_count, 2)  # Vencido + Crítico


class TestSmartCategorizerSkill(unittest.TestCase):
    def test_expense_categorization(self):
        res1 = categorize_expense(CategorizerInput(description="Pago GASOLINA PEMEX Estacion"))
        self.assertEqual(res1.suggested_category, "Transporte & Combustible")
        self.assertEqual(res1.behavior, "EXPENSE")

        res2 = categorize_expense(CategorizerInput(description="Suscripción NETFLIX mensual"))
        self.assertEqual(res2.suggested_category, "Entretenimiento & Suscripciones")
        self.assertEqual(res2.behavior, "EXPENSE")

        res3 = categorize_expense(CategorizerInput(description="Compra semanal WALMART Super"))
        self.assertEqual(res3.suggested_category, "Alimentos & Supermercado")

    def test_income_categorization(self):
        res = categorize_expense(CategorizerInput(description="Deposito de NOMINA quincenal"))
        self.assertEqual(res.suggested_category, "Sueldos & Salarios")
        self.assertEqual(res.behavior, "INCOME")


class TestSystemAuditSkill(unittest.TestCase):
    def test_holistic_audit(self):
        records = [
            AuditRecordItem(description="Nómina", amount=Decimal('25000.00'), behavior="INCOME", record_date=date(2026, 9, 15), category_name="Sueldos"),
            AuditRecordItem(description="Renta", amount=Decimal('7000.00'), behavior="EXPENSE", record_date=date(2026, 9, 5), category_name="Vivienda", is_recurrent=True),
            AuditRecordItem(description="Supermercado", amount=Decimal('3500.00'), behavior="EXPENSE", record_date=date(2026, 9, 10), category_name="Alimentos"),
            AuditRecordItem(description="MacBook MSI", amount=Decimal('2000.00'), behavior="EXPENSE", record_date=date(2026, 9, 12), category_name="Tecnología", total_installments=12, current_installment=3),
        ]
        goals = [
            AuditGoalItem(name="Fondo Emergencia", target_amount=Decimal('50000.00'), saved_amount=Decimal('20000.00'), target_date=date(2027, 3, 1))
        ]
        payload = SystemAuditInput(
            user_name="Carlos",
            salary=Decimal('25000.00'),
            records=records,
            goals=goals
        )
        result = audit_financial_system(payload)
        self.assertEqual(result.total_income, Decimal('25000.00'))
        self.assertEqual(result.total_expenses, Decimal('12500.00'))
        self.assertEqual(result.net_savings, Decimal('12500.00'))
        self.assertEqual(result.savings_rate, Decimal('50.00'))
        self.assertEqual(result.health_score, 75)
        self.assertEqual(result.health_status, "SALUDABLE")
        self.assertTrue(len(result.top_categories) > 0)
        self.assertTrue(len(result.goals_feasibility) == 1)
        self.assertTrue(result.goals_feasibility[0].is_viable)


class TestMCPServer(unittest.TestCase):
    def setUp(self):
        self.server = GTOPagosMCPServer()

    def test_list_tools(self):
        tools = self.server.list_tools()
        tool_names = [t["name"] for t in tools]
        self.assertIn("calculate_msi_projection", tool_names)
        self.assertIn("forecast_cashflow", tool_names)
        self.assertIn("prioritize_due_dates", tool_names)
        self.assertIn("categorize_expense", tool_names)
        self.assertIn("update_record_status", tool_names)
        self.assertIn("audit_financial_system", tool_names)

    def test_call_tool_msi(self):
        result = self.server.call_tool("calculate_msi_projection", {
            "total_amount": 6000.0,
            "total_installments": 6,
            "current_installment": 1
        })
        self.assertTrue(result.success)
        self.assertEqual(result.data["monthly_installment"], "1000.00")

    def test_call_tool_system_audit(self):
        result = self.server.call_tool("audit_financial_system", {
            "user_name": "Ana",
            "salary": "20000.00",
            "records": [
                {"description": "Sueldo", "amount": "20000.00", "behavior": "INCOME", "category_name": "Salario", "record_date": "2026-09-01"},
                {"description": "Renta", "amount": "6000.00", "behavior": "EXPENSE", "category_name": "Vivienda", "record_date": "2026-09-02"}
            ],
            "goals": []
        })
        self.assertTrue(result.success)
        self.assertEqual(result.data.get("widget_type"), "system_audit")
        self.assertIn("health_score", result.data)

    def test_guardrail_prevent_mutating_paid_record(self):
        # Intentar modificar un registro con current_status PAGADO debe fallar por guardrail
        result = self.server.call_tool("update_record_status", {
            "record_id": 99,
            "target_status": "PENDIENTE",
            "current_status": "PAGADO"
        })
        self.assertFalse(result.success)
        self.assertEqual(result.data.get("guardrail_triggered"), "IMMUTABLE_PAID_STATUS")

    def test_jsonrpc_protocol(self):
        req = {
            "jsonrpc": "2.0",
            "id": "req-1",
            "method": "tools/list",
            "params": {}
        }
        res_str = self.server.handle_json_rpc(json.dumps(req))
        res = json.loads(res_str)
        self.assertEqual(res["id"], "req-1")
        self.assertIn("tools", res["result"])


class TestFinancialAIOrchestrator(unittest.TestCase):
    def setUp(self):
        from agent.runtime.orchestrator import FinancialAIOrchestrator
        self.orchestrator = FinancialAIOrchestrator()

    def test_msi_query_extraction_and_widget(self):
        res = self.orchestrator.process_query("Compré una laptop de $12,000 a 12 meses sin intereses")
        self.assertTrue(res.success)
        self.assertEqual(res.action_type, "CALCULATION")
        self.assertEqual(res.data.get("widget_type"), "msi_card")
        self.assertEqual(res.data.get("monthly_installment"), "1000.00")
        self.assertIn("Proyección", res.user_message)

    def test_due_date_priority_query(self):
        res = self.orchestrator.process_query("¿Cuál es mi semáforo de vencimientos y próximos pagos?")
        self.assertTrue(res.success)
        self.assertEqual(res.data.get("widget_type"), "priority_table")
        self.assertIn("prioritized_list", res.data)

    def test_cashflow_query(self):
        res = self.orchestrator.process_query("Gano 24,000 al mes, ¿cómo está mi flujo de caja para el corte 15?")
        self.assertTrue(res.success)
        self.assertEqual(res.data.get("widget_type"), "cashflow_gauge")
        self.assertIn("risk_level", res.data)

    def test_categorize_query(self):
        res = self.orchestrator.process_query("Categoriza: Gasolina Pemex 800")
        self.assertTrue(res.success)
        self.assertEqual(res.data.get("widget_type"), "category_badge")
        self.assertEqual(res.data.get("suggested_category"), "Transporte & Combustible")

    def test_financial_advice_query(self):
        res = self.orchestrator.process_query("Explícame la regla 50/30/20 para ahorrar")
        self.assertTrue(res.success)
        self.assertEqual(res.data.get("widget_type"), "financial_tips")

    def test_empty_query(self):
        res = self.orchestrator.process_query("   ")
        self.assertFalse(res.success)

    def test_greeting_query(self):
        res = self.orchestrator.process_query("Hola, buenas tardes")
        self.assertTrue(res.success)
        self.assertIn("Hola", res.user_message)
        self.assertEqual(res.thought, "Saludo cálido y bienvenida contextual.")

    def test_identity_query(self):
        res = self.orchestrator.process_query("¿Quién eres y para qué sirves?")
        self.assertTrue(res.success)
        self.assertIn("Asistente de IA Financiera", res.user_message)

    def test_emergency_fund_query(self):
        res = self.orchestrator.process_query("¿Qué es un fondo de emergencia?")
        self.assertTrue(res.success)
        self.assertIn("Fondo de Emergencia", res.user_message)
        self.assertIn("3 y 6 meses", res.user_message)

    def test_conversational_fallback_mentions_query(self):
        res = self.orchestrator.process_query("Quiero planear unas vacaciones el próximo año")
        self.assertTrue(res.success)
        self.assertIn("Quiero planear unas vacaciones", res.user_message)

    def test_system_audit_query_unauthenticated(self):
        res = self.orchestrator.process_query("Analiza todo el sistema con mis gastos e ingresos y metas")
        self.assertTrue(res.success)
        self.assertIn("inicia sesión", res.user_message)


if __name__ == "__main__":
    unittest.main()

