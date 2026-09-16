from rest_framework import serializers
from .models import Currency, User, UserProfile, IncomeFrequency
from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import MinLengthValidator
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = '__all__'

class IncomeFrequencySerializer(serializers.ModelSerializer):
    class Meta:
        model = IncomeFrequency
        fields = '__all__'

class UserProfileSerializer(serializers.ModelSerializer):
    currency_id = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.all(),
        source="currency",
        required=False
    )

    income_frequency_id = serializers.PrimaryKeyRelatedField(
        queryset=IncomeFrequency.objects.all(),
        source="income_frequency",
        required=False
    )

    class Meta:
        model = UserProfile
        fields = [
            "first_name",
            "last_name",
            "phone",
            "salary",
            "currency_id",
            "income_frequency_id",
            "notification_method",
            "budget_alerts",
            "goal_reminders",
            "weekly_reports",
            "monthly_reports",
            "transaction_alerts",
            "payment_reminders",
        ]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    name = serializers.SerializerMethodField()
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[MinLengthValidator(8)],
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=False,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'id', 'email', 'name', 'password', 'confirm_password', 
            'is_active', 'last_login', 'created_at', 'updated_at',
            'profile'
        ]
        read_only_fields = ['id', 'last_login', 'created_at', 'updated_at']

    def get_name(self, obj):
        return obj.get_short_name() or "Usuario"

    def validate(self, data):
        # Solo validar confirm_password si se proporciona
        if 'confirm_password' in data and data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError({
                "confirm_password": "Las contraseñas no coinciden"
            })
        return data

    def create(self, validated_data):
        # Remover confirm_password del validated_data si existe
        validated_data.pop('confirm_password', None)
        
        # Encriptar la contraseña
        password = validated_data.pop('password')
        validated_data['password'] = make_password(password)
        
        # Crear el usuario
        user = User.objects.create(**validated_data)
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        try:
            user = User.objects.get(email=email)
            if not user.is_active:
                raise serializers.ValidationError("Usuario inactivo")
            if not check_password(password, user.password):
                raise serializers.ValidationError("Credenciales inválidas")
            data['user'] = user
            return data
        except User.DoesNotExist:
            raise serializers.ValidationError("Credenciales inválidas") 

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True,
        validators=[MinLengthValidator(8)]
    )
    confirm_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user

        if not check_password(value, user.password):
            raise serializers.ValidationError("La contraseña actual es incorrecta")

        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                "confirm_password": "Las contraseñas no coinciden"
            })

        return data

    def save(self, **kwargs):
        user = self.context['request'].user
        user.password = make_password(self.validated_data['new_password'])
        user.save()
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                "confirm_password": "Las contraseñas no coinciden"
            })

        # Decodificar el UID
        try:
            user_id = force_str(urlsafe_base64_decode(data['uid']))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({
                "token": "El enlace de recuperación es inválido o el usuario no existe."
            })

        # Verificar token criptográfico
        if not default_token_generator.check_token(user, data['token']):
            raise serializers.ValidationError({
                "token": "El enlace de recuperación es inválido o ha expirado."
            })

        # Validar complejidad de contraseña según validadores configurados de Django
        try:
            validate_password(data['new_password'], user=user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({
                "new_password": list(e.messages)
            })

        self.user = user
        return data

    def save(self, **kwargs):
        self.user.set_password(self.validated_data['new_password'])
        self.user.save()
        return self.user
