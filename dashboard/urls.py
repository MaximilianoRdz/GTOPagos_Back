from django.urls import path
from .views import CurrentDashboardView

urlpatterns = [
    path('dashboard/current/', CurrentDashboardView.as_view(), name='dashboard-current'),
]

