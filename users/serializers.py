from rest_framework import serializers
from .models import Currency, User
from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import MinLengthValidator

class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    currency = CurrencySerializer(read_only=True)
    currency_id = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.all(),
        source='currency',
        write_only=True
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[MinLengthValidator(8)],
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'id', 'name', 'email', 'password', 'confirm_password', 'salary',
            'currency', 'currency_id', 'income_frequency',
            'is_active', 'last_login', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_login', 'created_at', 'updated_at']

    def validate(self, data):
        # Verificar que las contraseñas coincidan
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError({
                "confirm_password": "Las contraseñas no coinciden"
            })
        return data

    def create(self, validated_data):
        # Remover confirm_password del validated_data
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