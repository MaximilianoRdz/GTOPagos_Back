"""
URL configuration for users app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CurrencyViewSet, TokenValidateView, UserLoginView, UserRegisterView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()
router.register(r'currencies', CurrencyViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('token/validate/', TokenValidateView.as_view(), name='token-validate'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('register/', UserRegisterView.as_view(), name='user-register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
] 