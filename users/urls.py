from rest_framework.routers import DefaultRouter
from .views import CurrencyViewSet, TokenValidateView, UserLoginView
from django.urls import path

router = DefaultRouter()
router.register(r'currencies', CurrencyViewSet, basename='currency')

urlpatterns = router.urls

urlpatterns += [
    path('token/validate/', TokenValidateView.as_view(), name='token-validate'),
    path('login/', UserLoginView.as_view(), name='user-login'),
] 