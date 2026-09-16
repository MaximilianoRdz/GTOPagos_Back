from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PaymentMethodViewSet, PaymentStatusViewSet

router = DefaultRouter()
router.register(r"payment-methods", PaymentMethodViewSet, basename="payment-method")
router.register(r"payment-statuses", PaymentStatusViewSet, basename="payment-status")

urlpatterns = [
    path("", include(router.urls)),
]
