from rest_framework import serializers
from finance.models import FinancialRecord
from .models import UserFinanceDashboard


class FinancialRecordLiteSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.name", default=None)
    payment_status = serializers.CharField(source="payment_status.status", default=None)
    record_type = serializers.CharField(source="record_type.name")

    class Meta:
        model = FinancialRecord
        fields = ["id", "amount", "description", "record_date", "category", "payment_status", "record_type"]


class DashboardSerializer(serializers.ModelSerializer):
    pending_to_pay = FinancialRecordLiteSerializer(many=True)

    class Meta:
        model = UserFinanceDashboard
        fields = [
            "period_type",
            "period_start",
            "total_income",
            "total_expense",
            "balance",
            "pending_to_pay",
        ]

