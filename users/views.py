from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import JSONParser
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from .models import Currency, User, IncomeFrequency, UserProfile
from .serializers import (
    CurrencySerializer,
    UserLoginSerializer,
    UserSerializer,
    IncomeFrequencySerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)

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
        user = request.user
        return Response({
            "detail": "Token válido",
            "code": "token_valid",
            "user_id": user.id,
            "user": {
                "email": user.email,
                "name": user.get_full_name() or user.get_short_name() or "Usuario"
            }
        }, status=status.HTTP_200_OK)

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

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Contraseña actualizada correctamente"},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id='password_reset_request',
        description='Solicita un enlace de recuperación de contraseña enviado por correo electrónico.',
        request=PasswordResetRequestSerializer,
        responses={200: OpenApiResponse(description='Correo de recuperación procesado.')}
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        user = User.objects.filter(email__iexact=email, is_active=True).first()

        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:4200').rstrip('/')
            reset_url = f"{frontend_url}/reset-password?uid={uid}&token={token}"

            user_name = user.get_short_name() or user.email

            subject = "Recuperación de contraseña - GTOPagos"
            message_plain = (
                f"Hola {user_name},\n\n"
                f"Hemos recibido una solicitud para restablecer la contraseña de tu cuenta en GTOPagos.\n\n"
                f"Para crear una nueva contraseña, haz clic en el siguiente enlace:\n"
                f"{reset_url}\n\n"
                f"Este enlace es válido por 24 horas y solo puede utilizarse una vez.\n\n"
                f"Si tú no solicitaste este cambio, puedes ignorar este correo de forma segura.\n\n"
                f"Atentamente,\nEl equipo de GTOPagos"
            )

            message_html = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b;">
              <table width="100%" border="0" cellspacing="0" cellpadding="0">
                <tr>
                  <td align="center">
                    <table width="600" border="0" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0;">
                      <tr>
                        <td style="background: linear-gradient(135deg, #059669 0%, #0d9488 50%, #0284c7 100%); padding: 32px 40px; text-align: center;">
                          <h1 style="color: #ffffff; margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -0.5px;">GTOPagos</h1>
                          <p style="color: #e0f2fe; margin: 8px 0 0 0; font-size: 14px;">Gestión Financiera Inteligente</p>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding: 40px;">
                          <h2 style="font-size: 20px; font-weight: 700; color: #0f172a; margin-top: 0; margin-bottom: 16px;">Restablecer tu contraseña</h2>
                          <p style="font-size: 15px; line-height: 1.6; color: #475569; margin-bottom: 24px;">
                            Hola <strong>{user_name}</strong>,<br><br>
                            Recibimos una solicitud para restablecer la contraseña de tu cuenta. Haz clic en el botón de abajo para definir una nueva contraseña:
                          </p>
                          <div style="text-align: center; margin: 32px 0;">
                            <a href="{reset_url}" target="_blank" style="background: linear-gradient(135deg, #059669 0%, #0d9488 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 12px; font-size: 15px; font-weight: 700; display: inline-block; box-shadow: 0 4px 12px rgba(13, 148, 136, 0.3);">
                              Restablecer mi Contraseña
                            </a>
                          </div>
                          <p style="font-size: 13px; line-height: 1.5; color: #64748b; margin-bottom: 16px;">
                            Si el botón no funciona, copia y pega el siguiente enlace en tu navegador:<br>
                            <a href="{reset_url}" style="color: #0d9488; word-break: break-all;">{reset_url}</a>
                          </p>
                          <div style="background-color: #f1f5f9; border-left: 4px solid #0d9488; padding: 12px 16px; border-radius: 4px; margin-top: 24px;">
                            <p style="margin: 0; font-size: 12px; color: #475569;">
                              <strong>Nota de seguridad:</strong> Este enlace expira en 24 horas y solo puede usarse una vez. Si no hiciste esta solicitud, puedes ignorar este correo.
                            </p>
                          </div>
                        </td>
                      </tr>
                      <tr>
                        <td style="background-color: #f8fafc; padding: 20px 40px; text-align: center; border-top: 1px solid #f1f5f9;">
                          <p style="margin: 0; font-size: 12px; color: #94a3b8;">
                            © {timezone.now().year} GTOPagos. Todos los derechos reservados.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </body>
            </html>
            """

            try:
                send_mail(
                    subject=subject,
                    message=message_plain,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=message_html,
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Error sending password reset email: {e}")

        return Response(
            {"message": "Si tu correo se encuentra registrado, recibirás un enlace con las instrucciones para restablecer tu contraseña."},
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id='password_reset_confirm',
        description='Confirma y actualiza la nueva contraseña utilizando el token criptográfico y UID recibido.',
        request=PasswordResetConfirmSerializer,
        responses={200: OpenApiResponse(description='Contraseña actualizada con éxito.')}
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Tu contraseña ha sido restablecida exitosamente. Ya puedes iniciar sesión con tu nueva contraseña."},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DemoLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id='demo_login',
        description='Inicia sesión inmediatamente como usuario de prueba (Demo) con datos precargados.',
        responses={200: UserSerializer}
    )
    def post(self, request):
        from .demo_data import ensure_demo_user_and_data
        demo_user = ensure_demo_user_and_data()
        access_token = AccessToken.for_user(demo_user)

        return Response({
            "user": UserSerializer(demo_user).data,
            "access_token": str(access_token),
            "is_demo": True
        }, status=status.HTTP_200_OK)

