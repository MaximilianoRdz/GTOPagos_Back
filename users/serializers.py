from rest_framework import serializers
from .models import Currency, User, UserProfile, IncomeFrequency
from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import MinLengthValidator

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
        ]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
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
            'id', 'email', 'password', 'confirm_password', 
            'is_active', 'last_login', 'created_at', 'updated_at',
            'profile'
        ]
        read_only_fields = ['id', 'last_login', 'created_at', 'updated_at']

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
