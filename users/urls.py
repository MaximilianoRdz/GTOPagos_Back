from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CurrencyViewSet, TokenValidateView, UserLoginView, UserRegisterView, LogoutView, IncomeFrequencyViewSet, UserProfileView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()
router.register(r'currencies', CurrencyViewSet)
router.register(r'income-frequencies', IncomeFrequencyViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('token/validate/', TokenValidateView.as_view(), name='token-validate'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('register/', UserRegisterView.as_view(), name='user-register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='user-logout'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
]