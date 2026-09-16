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
        fields = ["id", "amount", "description", "record_date", "category", "payment_status", "record_type", "is_recurrent", "current_installment", "total_installments"]

class CategorySummarySerializer(serializers.Serializer):
    name = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_records = serializers.IntegerField()
    paid_records = serializers.IntegerField()
    pending_amount = serializers.DecimalField(max_digits=15, decimal_places=2)

class BehaviorSummarySerializer(serializers.Serializer):
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_records = serializers.IntegerField()
    paid_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    paid_records = serializers.IntegerField()
    pending_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_records = serializers.IntegerField()
    categories = CategorySummarySerializer(many=True)


class CurrentPeriodSummarySerializer(serializers.Serializer):
    period_type = serializers.CharField()
    period_start = serializers.DateField()
    total_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_expense = serializers.DecimalField(max_digits=15, decimal_places=2)
    balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    expense_summary = BehaviorSummarySerializer()
    income_summary = BehaviorSummarySerializer()
    pending_to_pay = FinancialRecordLiteSerializer(many=True)


class DashboardSerializer(serializers.ModelSerializer):
    currency_id = serializers.PrimaryKeyRelatedField(
        source="currency",
        queryset=Currency.objects.all(),
        required=False,
        allow_null=True
    )
    name = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    dashboard_type = serializers.ChoiceField(
        choices=UserFinanceDashboard.DASHBOARD_TYPE_CHOICES,
        default='BOTH',
        required=False
    )
    total_income = serializers.SerializerMethodField()
    total_expense = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    records_count = serializers.SerializerMethodField()

    def get_total_income(self, obj):
        # Lee el valor anotado por la vista, o calcula si no existe
        return getattr(obj, 'total_income', 0) or 0

    def get_total_expense(self, obj):
        return getattr(obj, 'total_expense', 0) or 0

    def get_balance(self, obj):
        income = getattr(obj, 'total_income', 0) or 0
        expense = getattr(obj, 'total_expense', 0) or 0
        return income - expense

    def get_records_count(self, obj):
        return getattr(obj, 'records_count', 0) or 0

    class Meta:
        model = UserFinanceDashboard
        fields = [
            "id",
            "name",
            "description",
            "monthly_budget",
            "currency_id",
            "dashboard_type",
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
