from rest_framework import viewsets, status
from .models import Currency, User, IncomeFrequency, UserProfile
from .serializers import CurrencySerializer, UserLoginSerializer, UserSerializer, IncomeFrequencySerializer, UserProfileSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework.parsers import JSONParser
from drf_spectacular.utils import extend_schema, OpenApiResponse
from datetime import datetime
from rest_framework.permissions import IsAuthenticated

class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = []  # Permitir acceso sin autenticación

class IncomeFrequencyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IncomeFrequency.objects.filter(is_active=True)
    serializer_class = IncomeFrequencySerializer
    permission_classes = []

class TokenValidateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    
    @extend_schema(
        operation_id='validate_token',
        description='Validate JWT token',
        request=None,
        responses={
            200: UserSerializer,
            400: UserLoginSerializer
        }
    )
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
            if token['exp'] < datetime.now().timestamp():
                return Response({
                    "detail": "El token ha expirado",
                    "code": "token_expired"
                }, status=400)
            
            # Verificar que el usuario existe
            user_id = token['user_id']
            try:
                user = User.objects.select_related('profile').get(id=user_id, is_active=True)
            except User.DoesNotExist:
                return Response({
                    "detail": "Usuario no encontrado o inactivo",
                    "code": "user_not_found"
                }, status=400)
            
            # Si llegamos aquí, el token es válido
            return Response({
                "detail": "Token válido",
                "code": "token_valid",
                "user_id": user_id,
                "user": {
                    "email": user.email
                }
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
    
    @extend_schema(
        operation_id='register_user',
        description='Register a new user. Fields confirm_password and income_frequency are optional.',
        request={
            'application/json': {
                'type': 'object',
                'required': ['email', 'password'],
                'properties': {
                    'email': {'type': 'string', 'format': 'email', 'description': 'User email (must be unique)'},
                    'first_name': {'type': 'string', 'description': 'First name (optional)'},
                    'last_name': {'type': 'string', 'description': 'Last name (optional)'},
                    'phone': {'type': 'string', 'description': 'Phone number (optional)'},
                    'password': {'type': 'string', 'minLength': 8, 'description': 'User password (minimum 8 characters)'},
                    'confirm_password': {'type': 'string', 'description': 'Password confirmation (optional)'},
                    'salary': {'type': 'number', 'description': 'User salary (optional)'},
                    'currency_id': {'type': 'integer', 'description': 'ID of the user currency (optional)'},
                    'income_frequency': {
                        'type': 'string',
                        'enum': ['weekly', 'biweekly', 'monthly', 'yearly'],
                        'description': 'Frequency of income (optional)'
                    }
                }
            }
        },
        responses={
            201: UserSerializer,
            400: UserSerializer
        }
    )
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Obtener o crear perfil (ya debería haber sido creado por el serializer)
            profile, created = UserProfile.objects.get_or_create(user=user)

            # Actualizar datos personales
            profile.first_name = request.data.get("first_name", "")
            profile.last_name = request.data.get("last_name", "")
            profile.phone = request.data.get("phone", "")

            # Crear perfil si vienen datos financieros
            salary = request.data.get("salary")
            currency_id = request.data.get("currency_id")
            income_freq_input = request.data.get("income_frequency")

            if salary and currency_id:
                from .models import Currency, UserProfile, IncomeFrequency
                try:
                    currency = Currency.objects.get(id=currency_id)
                except Currency.DoesNotExist:
                    # Si no existe moneda, creamos perfil vacío o manejamos error.
                    return Response({"currency_id": "Invalid currency_id"}, status=400)

                # Resolver IncomeFrequency
                income_frequency_obj = None
                if income_freq_input:
                    if isinstance(income_freq_input, int):
                        income_frequency_obj = IncomeFrequency.objects.filter(id=income_freq_input).first()
                    else:
                        income_frequency_obj = IncomeFrequency.objects.filter(name__iexact=str(income_freq_input)).first()
                
                # Default a 'monthly' si no se encuentra
                if not income_frequency_obj:
                    income_frequency_obj = IncomeFrequency.objects.filter(name__iexact="monthly").first()

                profile.salary = salary
                profile.currency = currency
                profile.income_frequency = income_frequency_obj
            
            profile.save()
            
            # Usar el serializer para retornar datos limpios del perfil
            profile_data = UserProfileSerializer(profile).data

            # Generar token
            access_token = AccessToken.for_user(user)

            return Response({
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "profile": profile_data
                },
                "access_token": str(access_token)
            }, status=201)

        return Response(serializer.errors, status=400)

class UserLoginView(APIView):
    permission_classes = []
    parser_classes = [JSONParser]
    
    @extend_schema(
        operation_id='login_user',
        description='Login user and get access token',
        request=UserLoginSerializer,
        responses={
            200: UserSerializer,
            400: UserLoginSerializer
        }
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            # Generar solo access token como solicitado
            access_token = AccessToken.for_user(user)

            # Traer el perfil si existe
            profile = getattr(user, "profile", None)

            return Response({
                "user": UserSerializer(user).data,
                "access_token": str(access_token),
                # El profile ya viene dentro de UserSerializer(user).data si está configurado así, 
                # pero UserSerializer tiene 'profile' = UserProfileSerializer
            }, status=200)

        return Response(serializer.errors, status=400)  
class LogoutView(APIView):
    permission_classes = []
    parser_classes = [JSONParser]

    @extend_schema(
        operation_id='logout_user',
        description='Logout descartando los tokens del cliente. Acepta refresh en body o access token en Authorization.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'refresh': {'type': 'string', 'description': 'Refresh token'},
                    'token': {'type': 'string', 'description': 'Access token'},
                    'access_token': {'type': 'string', 'description': 'Access token alias'}
                }
            }
        },
        responses={
            200: OpenApiResponse(description='Logout successful')
        }
    )
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token_in_body = request.data.get('token') or request.data.get('access_token')
            auth_header = request.headers.get('Authorization')

            if refresh_token:
                try:
                    RefreshToken(refresh_token)
                except Exception:
                    pass
                return Response({"detail": "Sesión cerrada exitosamente"}, status=status.HTTP_200_OK)

            if auth_header:
                parts = auth_header.split(' ')
                maybe_token = parts[1] if len(parts) > 1 else parts[0]
                try:
                    AccessToken(maybe_token)
                except Exception:
                    pass
                return Response({"detail": "Sesión cerrada exitosamente"}, status=status.HTTP_200_OK)

            if token_in_body:
                try:
                    AccessToken(token_in_body)
                except Exception:
                    pass
                return Response({"detail": "Sesión cerrada exitosamente"}, status=status.HTTP_200_OK)

            return Response({"detail": "Sesión cerrada exitosamente"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": f"Error al cerrar sesión: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_profile(self, user):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return profile

    def get(self, request):
        profile = self._get_profile(request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        profile = self._get_profile(request.user)
        serializer = UserProfileSerializer(
            profile,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
