from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CurrencyViewSet, TokenValidateView, UserLoginView, UserRegisterView

router = DefaultRouter()
router.register(r'currencies', CurrencyViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('token/validate/', TokenValidateView.as_view(), name='token-validate'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('register/', UserRegisterView.as_view(), name='user-register'),
] 