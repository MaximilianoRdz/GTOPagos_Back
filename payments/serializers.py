from rest_framework import serializers

from .models import PaymentMethod, PaymentStatus


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["id", "name", "description", "is_active"]


class PaymentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentStatus
        fields = ["id", "status", "color", "description", "is_active"]

