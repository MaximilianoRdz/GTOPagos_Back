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
                    'password': {'type': 'string', 'minLength': 8, 'description': 'User password (minimum 8 characters)'},
                    'confirm_password': {'type': 'string', 'description': 'Password confirmation (optional)'},
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

            # Crear perfil vacío (clave)
            UserProfile.objects.create(user=user)

            # Generar token
            access_token = AccessToken.for_user(user)

            return Response({
                "user": {
                    "id": user.id,
                    "email": user.email,
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
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            # Traer el perfil si existe
            profile = getattr(user, "profile", None)

            return Response({
                "user": UserSerializer(user).data,
                "refresh": str(refresh),
                "access_token": str(access_token)
            }, status=200)

        return Response(serializer.errors, status=400)  
class LogoutView(APIView):
    permission_classes = []
    parser_classes = [JSONParser]
    
    @extend_schema(
        operation_id='logout_user',
        description='Logout user by invalidating the client-side token',
        request={
            'application/json': {
                'type': 'object',
                'required': ['refresh'],
                'properties': {
                    'refresh': {'type': 'string', 'description': 'Refresh token to invalidate'}
                }
            }
        },
        responses={
            204: OpenApiResponse(description='No content, logout successful'),
            400: OpenApiResponse(description='Bad request, invalid token')
        }
    )
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({"detail": "Se requiere el refresh token"}, status=status.HTTP_400_BAD_REQUEST)
            
            # En JWT, el logout es principalmente un proceso del lado del cliente
            # donde el cliente descarta los tokens
            # Aquí simplemente validamos que el token sea válido y devolvemos una respuesta exitosa
            # El cliente debe eliminar los tokens almacenados localmente
            
            try:
                # Verificamos que el token sea válido
                RefreshToken(refresh_token)
            except Exception:
                return Response({"detail": "Token inválido"}, status=status.HTTP_400_BAD_REQUEST)
            
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

    