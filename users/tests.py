from django.test import TestCase
from django.urls import reverse
from django.core import mail
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class PasswordResetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.email = "usuario.prueba@gtopagos.com"
        self.password = "ContrasenaOriginal123"
        self.user = User.objects.create_user(
            email=self.email,
            password=self.password
        )
        self.request_url = reverse('password-reset-request')
        self.confirm_url = reverse('password-reset-confirm')

    def test_password_reset_request_valid_user(self):
        """Solicitar recuperación para un usuario registrado debe enviar un email con el token."""
        response = self.client.post(self.request_url, {'email': self.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)

        # Verificar envío de correo
        self.assertEqual(len(mail.outbox), 1)
        sent_mail = mail.outbox[0]
        self.assertEqual(sent_mail.to, [self.email])
        self.assertIn("Recuperación de contraseña", sent_mail.subject)
        self.assertIn("reset-password?uid=", sent_mail.body)
        self.assertIn("&token=", sent_mail.body)

    def test_password_reset_request_nonexistent_user(self):
        """Solicitar recuperación para un correo inexistente debe retornar 200 sin enviar correo."""
        response = self.client.post(self.request_url, {'email': 'noexiste@gtopagos.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_request_invalid_email(self):
        """Solicitar recuperación con formato de email inválido debe retornar 400."""
        response = self.client.post(self.request_url, {'email': 'correo-invalido'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_password_reset_confirm_success(self):
        """Confirmar restablecimiento con token válido debe cambiar la contraseña del usuario."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        new_password = "NuevaContrasenaSegura456!"

        payload = {
            'uid': uid,
            'token': token,
            'new_password': new_password,
            'confirm_password': new_password
        }
        response = self.client.post(self.confirm_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refrescar usuario y verificar que la contraseña cambió
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        self.assertFalse(self.user.check_password(self.password))

    def test_password_reset_confirm_mismatched_passwords(self):
        """Confirmar con contraseñas que no coinciden debe retornar error 400."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        payload = {
            'uid': uid,
            'token': token,
            'new_password': 'PasswordValido123',
            'confirm_password': 'PasswordDiferente456'
        }
        response = self.client.post(self.confirm_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('confirm_password', response.data)

    def test_password_reset_confirm_invalid_token(self):
        """Confirmar con token inválido debe retornar error 400."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        payload = {
            'uid': uid,
            'token': 'token-invalido-12345',
            'new_password': 'NuevaContrasenaSegura456!',
            'confirm_password': 'NuevaContrasenaSegura456!'
        }
        response = self.client.post(self.confirm_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('token', response.data)

    def test_password_reset_confirm_one_time_use(self):
        """Un token de restablecimiento solo puede utilizarse una vez."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        new_password = "PrimerCambio123!"

        # Primer uso: exitoso
        payload1 = {
            'uid': uid,
            'token': token,
            'new_password': new_password,
            'confirm_password': new_password
        }
        response1 = self.client.post(self.confirm_url, payload1)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Segundo uso con el mismo token: debe fallar porque el token quedó invalidado al cambiar el hash
        payload2 = {
            'uid': uid,
            'token': token,
            'new_password': "SegundoCambio123!",
            'confirm_password': "SegundoCambio123!"
        }
        response2 = self.client.post(self.confirm_url, payload2)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('token', response2.data)
