from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import Currency
from .serializers import CurrencySerializer

class CurrencyViewSet(viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = [AllowAny] 