from rest_framework import viewsets
from drf_spectacular.utils import extend_schema_view, extend_schema

from .models import PaymentMethod, PaymentStatus
from .serializers import PaymentMethodSerializer, PaymentStatusSerializer


@extend_schema_view(
    list=extend_schema(
        operation_id="list_payment_methods",
        description="List all active payment methods.",
        responses={200: PaymentMethodSerializer},
    ),
    retrieve=extend_schema(
        operation_id="retrieve_payment_method",
        description="Retrieve a single payment method.",
        responses={200: PaymentMethodSerializer},
    ),
)
class PaymentMethodViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentMethod.objects.filter(is_active=True).order_by("name")
    serializer_class = PaymentMethodSerializer
    permission_classes = []


@extend_schema_view(
    list=extend_schema(
        operation_id="list_payment_statuses",
        description="List all active payment statuses.",
        responses={200: PaymentStatusSerializer},
    ),
    retrieve=extend_schema(
        operation_id="retrieve_payment_status",
        description="Retrieve a single payment status.",
        responses={200: PaymentStatusSerializer},
    ),
)
class PaymentStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentStatus.objects.filter(is_active=True).order_by("status")
    serializer_class = PaymentStatusSerializer
    permission_classes = []

