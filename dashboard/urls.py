from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CurrentDashboardView, DashboardViewSet, DashboardRecordsView

router = DefaultRouter()
router.register(r'dashboards', DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('dashboard/current/', CurrentDashboardView.as_view(), name='dashboard-current'),
    path('dashboards/<int:pk>/records/', DashboardRecordsView.as_view(), name='dashboard-records'),
    path('', include(router.urls)),
]
