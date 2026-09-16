import calendar
import datetime
from django.db import transaction
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import FinancialRecord, FinancialRecordMetadata, FinancialRecordType, Category, FinancialGoal
from dashboard.models import UserFinanceDashboard
from payments.models import PaymentMethod, PaymentStatus
from users.models import Currency


class FinancialRecordMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialRecordMetadata
        fields = [
            "id",
            "frequency_type",
            "frequency_value",
            "next_occurrence",
            "extra_notes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

class FinancialGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialGoal
        fields = [
            'id', 'name', 'target_amount', 'saved_amount', 
            'target_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CategorySerializer(serializers.ModelSerializer):
    record_type_id = serializers.PrimaryKeyRelatedField(
        source="record_type",
        queryset=FinancialRecordType.objects.all(),
    )
    record_type_behavior = serializers.CharField(
        source="record_type.behavior",
        read_only=True,
    )
    keywords = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="keyword"
    )
    is_custom = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "record_type_id", "record_type_behavior", "color", "icon", "keywords", "is_custom"]
        read_only_fields = ["id", "is_custom", "record_type_behavior"]

    def get_is_custom(self, obj):
        return obj.user_id is not None



class FinancialRecordTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialRecordType
        fields = ["id", "name", "description", "behavior"]


class FinancialRecordSerializer(serializers.ModelSerializer):
    dashboard_id = serializers.PrimaryKeyRelatedField(
        source="dashboard",
        queryset=UserFinanceDashboard.objects.all(),
    )
    record_type_id = serializers.PrimaryKeyRelatedField(
        source="record_type",
        queryset=FinancialRecordType.objects.all(),
    )
    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.all(),
        required=False,
        allow_null=True,
    )
    category_name = serializers.CharField(source="category.name", read_only=True)
    payment_method_id = serializers.PrimaryKeyRelatedField(
        source="payment_method",
        queryset=PaymentMethod.objects.all(),
        required=False,
        allow_null=True,
    )
    payment_status_id = serializers.PrimaryKeyRelatedField(
        source="payment_status",
        queryset=PaymentStatus.objects.all(),
        required=False,
        allow_null=True,
    )
    currency_id = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.all(),
        required=False,
        allow_null=True,
    )
    frequency_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    frequency_value = serializers.IntegerField(required=False, allow_null=True)
    extra_notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    metadata = FinancialRecordMetadataSerializer(read_only=True)
    payment_type = serializers.SerializerMethodField()
    record_behavior = serializers.CharField(source="record_type.behavior", read_only=True)

    class Meta:
        model = FinancialRecord
        fields = [
            "id",
            "dashboard_id",
            "record_type_id",
            "category_id",
            "category_name",
            "payment_method_id",
            "payment_status_id",
            "amount",
            "description",
            "record_date",
            "is_recurrent",
            "current_installment",
            "total_installments",
            "frequency_type",
            "frequency_value",
            "extra_notes",
            "currency_id",
            "payment_type",
            "record_behavior",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        is_recurrent = attrs.get("is_recurrent", getattr(self.instance, "is_recurrent", False))
        frequency_type = attrs.get("frequency_type", None)
        frequency_value = attrs.get("frequency_value", None)

        if is_recurrent and frequency_value is not None and not frequency_type:
            raise serializers.ValidationError(
                {"frequency_type": "frequency_type is required when frequency_value is provided"}
            )

        # Validate record behavior matches dashboard constraints
        dashboard = attrs.get("dashboard", getattr(self.instance, "dashboard", None))
        record_type = attrs.get("record_type", getattr(self.instance, "record_type", None))

        if dashboard and record_type:
            if dashboard.dashboard_type == 'INCOME' and record_type.behavior == 'EXPENSE':
                raise serializers.ValidationError(
                    {"record_type_id": "No se permiten movimientos de tipo gasto en un dashboard de solo ingresos."}
                )
            elif dashboard.dashboard_type == 'EXPENSES' and record_type.behavior == 'INCOME':
                raise serializers.ValidationError(
                    {"record_type_id": "No se permiten movimientos de tipo ingreso en un dashboard de solo gastos."}
                )

        return attrs

    def create(self, validated_data):
        frequency_type = validated_data.pop("frequency_type", None)
        frequency_value = validated_data.pop("frequency_value", None)
        extra_notes = validated_data.pop("extra_notes", None)
        currency = validated_data.pop("currency_id", None)
        user = self.context["request"].user

        total_installments = validated_data.get("total_installments") or 1
        record_date = validated_data.get("record_date")
        
        try:
            pending_status = PaymentStatus.objects.get(code__iexact='pending')
        except PaymentStatus.DoesNotExist:
            pending_status = None

        first_record = None

        try:
            with transaction.atomic():
                if total_installments > 1 and record_date:
                    for i in range(1, total_installments + 1):
                        current_data = validated_data.copy()
                        current_data["current_installment"] = i
                        
                        if i > 1:
                            months_to_add = i - 1
                            month = record_date.month - 1 + months_to_add
                            year = record_date.year + month // 12
                            month = month % 12 + 1
                            day = min(record_date.day, calendar.monthrange(year, month)[1])
                            current_data["record_date"] = datetime.date(year, month, day)
                            
                            if pending_status:
                                current_data["payment_status"] = pending_status
                                
                        record = FinancialRecord.objects.create(
                            user=user,
                            created_by=user,
                            **current_data,
                        )
                        if i == 1:
                            first_record = record
                else:
                    first_record = FinancialRecord.objects.create(
                        user=user,
                        created_by=user,
                        **validated_data,
                    )
        except DjangoValidationError as e:
            if hasattr(e, "message_dict"):
                detail = e.message_dict
            else:
                detail = {"non_field_errors": e.messages}
            raise serializers.ValidationError(detail)

        if first_record and (
            first_record.is_recurrent
            or frequency_type is not None
            or frequency_value is not None
            or extra_notes is not None
            or currency is not None
        ):
            FinancialRecordMetadata.objects.create(
                financial_record=first_record,
                frequency_type=frequency_type,
                frequency_value=frequency_value,
                extra_notes=extra_notes or "",
                is_active=bool(first_record.is_recurrent),
                currency=currency,
            )

        return first_record

    def update(self, instance, validated_data):
        frequency_type = validated_data.pop("frequency_type", None)
        frequency_value = validated_data.pop("frequency_value", None)
        extra_notes = validated_data.pop("extra_notes", None)
        currency = validated_data.pop("currency_id", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        try:
            instance.save()
        except DjangoValidationError as e:
            if hasattr(e, "message_dict"):
                detail = e.message_dict
            else:
                detail = {"non_field_errors": e.messages}
            raise serializers.ValidationError(detail)

        if frequency_type is not None or frequency_value is not None or extra_notes is not None or currency is not None:
            try:
                metadata = instance.financialrecordmetadata
            except FinancialRecordMetadata.DoesNotExist:
                metadata = FinancialRecordMetadata(financial_record=instance)

            if frequency_type is not None:
                metadata.frequency_type = frequency_type
            if frequency_value is not None:
                metadata.frequency_value = frequency_value
            if extra_notes is not None:
                metadata.extra_notes = extra_notes
            if currency is not None:
                metadata.currency = currency

            metadata.save()

        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        try:
            meta = instance.financialrecordmetadata
            data["frequency_type"] = meta.frequency_type
            data["frequency_value"] = meta.frequency_value
            data["extra_notes"] = meta.extra_notes
            data["currency_id"] = meta.currency_id
        except FinancialRecordMetadata.DoesNotExist:
            pass
        return data

    def get_payment_type(self, obj):
        if obj.total_installments and obj.total_installments > 1:
            return "CREDIT"

        return "DEBIT"

