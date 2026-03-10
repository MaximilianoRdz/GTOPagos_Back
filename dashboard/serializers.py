from rest_framework import serializers
from finance.models import FinancialRecord
from .models import UserFinanceDashboard
from users.models import Currency


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
            "id",
            "name",
            "description",
            "period_type",
            "period_start",
            "total_income",
            "total_expense",
            "balance",
            "pending_to_pay",
        ]


class DashboardBasicSerializer(serializers.ModelSerializer):
    currency_id = serializers.PrimaryKeyRelatedField(
        source="currency",
        queryset=Currency.objects.all(),
        required=False,
        allow_null=True
    )
    name = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    total_income = serializers.SerializerMethodField()
    total_expense = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    records_count = serializers.SerializerMethodField()

    def _classify_totals(self, qs):
        total_income = 0
        total_expense = 0
        for rec in qs.select_related("record_type"):
            name = (rec.record_type.name or "").lower()
            if any(k in name for k in ["income", "ingres", "percep"]):
                total_income += rec.amount or 0
            elif any(k in name for k in ["expense", "egres", "deduc"]):
                total_expense += rec.amount or 0
        return total_income, total_expense

    def get_total_income(self, obj):
        qs = obj.financial_records.all()
        income, _ = self._classify_totals(qs)
        return income

    def get_total_expense(self, obj):
        qs = obj.financial_records.all()
        _, expense = self._classify_totals(qs)
        return expense

    def get_balance(self, obj):
        qs = obj.financial_records.all()
        income, expense = self._classify_totals(qs)
        return income - expense

    def get_records_count(self, obj):
        return obj.financial_records.count()

    class Meta:
        model = UserFinanceDashboard
        fields = [
            "id",
            "name",
            "description",
            "currency_id",
            "total_income",
            "total_expense",
            "balance",
            "records_count",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "total_income",
            "total_expense",
            "balance",
            "records_count",
            "updated_at",
        ]
