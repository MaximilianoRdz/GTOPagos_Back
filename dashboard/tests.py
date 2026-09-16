from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from users.models import User
from dashboard.models import UserFinanceDashboard
from finance.models import FinancialRecord, FinancialRecordType
import datetime

class DashboardTypeTests(APITestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(email="testuser@example.com", password="testpassword")
        self.client.force_authenticate(user=self.user)

        # Create record types
        self.income_type, _ = FinancialRecordType.objects.get_or_create(name="Ingresos", defaults={"behavior": "INCOME"})
        self.expense_type, _ = FinancialRecordType.objects.get_or_create(name="Gastos", defaults={"behavior": "EXPENSE"})

    def test_create_dashboard_default_type(self):
        url = reverse("dashboard-list")
        data = {
            "name": "Default Dashboard",
            "description": "Both expenses and income"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["dashboard_type"], "BOTH")
        
        dashboard = UserFinanceDashboard.objects.get(id=response.data["id"])
        self.assertEqual(dashboard.dashboard_type, "BOTH")

    def test_create_dashboard_specific_types(self):
        url = reverse("dashboard-list")
        
        # Test INCOME dashboard
        data = {
            "name": "Income Dashboard",
            "dashboard_type": "INCOME"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["dashboard_type"], "INCOME")

        # Test EXPENSES dashboard
        data = {
            "name": "Expenses Dashboard",
            "dashboard_type": "EXPENSES"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["dashboard_type"], "EXPENSES")

    def test_create_dashboard_invalid_type(self):
        url = reverse("dashboard-list")
        data = {
            "name": "Invalid Dashboard",
            "dashboard_type": "INVALID_TYPE"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("dashboard_type", response.data)

    def test_financial_record_validation_both(self):
        # Create dashboard of type BOTH
        dashboard = UserFinanceDashboard.objects.create(user=self.user, name="Both Dashboard", dashboard_type="BOTH")

        # Create income record - should succeed
        url = reverse("financial-record-list")
        data = {
            "dashboard_id": dashboard.id,
            "record_type_id": self.income_type.id,
            "amount": "100.00",
            "record_date": "2026-06-06"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create expense record - should succeed
        data["record_type_id"] = self.expense_type.id
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_financial_record_validation_income_only(self):
        # Create dashboard of type INCOME
        dashboard = UserFinanceDashboard.objects.create(user=self.user, name="Income Dashboard", dashboard_type="INCOME")

        # Create income record - should succeed
        url = reverse("financial-record-list")
        data = {
            "dashboard_id": dashboard.id,
            "record_type_id": self.income_type.id,
            "amount": "100.00",
            "record_date": "2026-06-06"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create expense record - should fail
        data["record_type_id"] = self.expense_type.id
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("record_type_id", response.data)
        self.assertEqual(
            response.data["record_type_id"][0],
            "No se permiten movimientos de tipo gasto en un dashboard de solo ingresos."
        )

    def test_financial_record_validation_expense_only(self):
        # Create dashboard of type EXPENSES
        dashboard = UserFinanceDashboard.objects.create(user=self.user, name="Expenses Dashboard", dashboard_type="EXPENSES")

        # Create expense record - should succeed
        url = reverse("financial-record-list")
        data = {
            "dashboard_id": dashboard.id,
            "record_type_id": self.expense_type.id,
            "amount": "100.00",
            "record_date": "2026-06-06"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create income record - should fail
        data["record_type_id"] = self.income_type.id
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("record_type_id", response.data)
        self.assertEqual(
            response.data["record_type_id"][0],
            "No se permiten movimientos de tipo ingreso en un dashboard de solo gastos."
        )
