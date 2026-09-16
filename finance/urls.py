from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FinancialRecordViewSet, FinanceCategoryViewSet, FinancialRecordTypeViewSet, DetectCategoryView, ImportPreviewView, ImportConfirmView, ExportDashboardView, FinancialGoalViewSet, ReportDataView, ReportDownloadView

router = DefaultRouter()
router.register(r"financial-records", FinancialRecordViewSet, basename="financial-record")
router.register(r"finance-categories", FinanceCategoryViewSet, basename="finance-category")
router.register(r"categories", FinanceCategoryViewSet, basename="category")
router.register(r"financial-record-types", FinancialRecordTypeViewSet, basename="financial-record-type")
router.register(r"goals", FinancialGoalViewSet, basename="goal")

urlpatterns = [
    path("import/preview/", ImportPreviewView.as_view(), name="import-preview"),
    path("import/confirm/", ImportConfirmView.as_view(), name="import-confirm"),
    path("export/", ExportDashboardView.as_view(), name="export-dashboard"),
    path("reports/data/", ReportDataView.as_view(), name="report-data"),
    path("reports/download/", ReportDownloadView.as_view(), name="report-download"),
    path("transactions/detect-category", DetectCategoryView.as_view(), name="detect-category"),
    path("", include(router.urls)),
]

