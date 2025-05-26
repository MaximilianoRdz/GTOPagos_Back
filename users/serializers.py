from rest_framework import serializers
from .models import Currency, User
from django.contrib.auth.hashers import check_password

class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = '__all__'

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

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