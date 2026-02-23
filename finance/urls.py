from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FinancialRecordViewSet, FinanceCategoryViewSet, FinancialRecordTypeViewSet

router = DefaultRouter()
router.register(r"financial-records", FinancialRecordViewSet, basename="financial-record")
router.register(r"finance-categories", FinanceCategoryViewSet, basename="finance-category")
router.register(r"financial-record-types", FinancialRecordTypeViewSet, basename="financial-record-type")

urlpatterns = [
    path("", include(router.urls)),
]
