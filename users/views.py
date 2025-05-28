from rest_framework import viewsets
from .models import Currency
from .serializers import CurrencySerializer, UserLoginSerializer, UserSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.parsers import JSONParser
import time

class CurrencyViewSet(viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = []  # Permitir acceso sin autenticación
    
class TokenValidateView(APIView):
    permission_classes = []
    parser_classes = [JSONParser]
    
    def post(self, request):
        try:
            # Obtener el token del header de autorización
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return Response({
                    "detail": "Se requiere un token de acceso",
                    "code": "token_missing"
                }, status=400)
            
            # Extraer el token
            access_token = auth_header.split(' ')[1]
            
            # Validar el token
            token = AccessToken(access_token)
            
            # Verificar que el token no haya expirado
            if token['exp'] < time.time():
                return Response({
                    "detail": "El token ha expirado",
                    "code": "token_expired"
                }, status=400)
            
            # Si llegamos aquí, el token es válido
            return Response({
                "detail": "Token válido",
                "code": "token_valid",
                "user_id": token['user_id']
            })
            
        except Exception as e:
            return Response({
                "detail": "Token inválido",
                "code": "token_invalid",
                "error": str(e)
            }, status=400)

class UserRegisterView(APIView):
    permission_classes = []
    parser_classes = [JSONParser]
    
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Generar el token de acceso
            access_token = AccessToken.for_user(user)
            return Response({
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "salary": user.salary,
                    "currency": user.currency.code,
                    "income_frequency": user.income_frequency
                },
                "access_token": str(access_token)
            }, status=201)
        return Response(serializer.errors, status=400)

class UserLoginView(APIView):
    permission_classes = []
    parser_classes = [JSONParser]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            access_token = AccessToken.for_user(user)
            user_data = {
                'name': user.name,
                'email': user.email,
                'salary': user.salary,
                'currency': user.currency.code
            }
            return Response({
                'user': user_data,
                'access_token': str(access_token)
            })
        return Response(serializer.errors, status=400)
    