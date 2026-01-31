from django.db import models
from django.core.validators import EmailValidator
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin
)
from django.utils import timezone
from django.conf import settings

# Eliminar los campos first_name y last_name del modelo User de Django
# from django.contrib.auth.models import User as AuthUser
# if hasattr(AuthUser, 'first_name'):
#     AuthUser.first_name = None
# if hasattr(AuthUser, 'last_name'):
#     AuthUser.last_name = None


class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=5)
    sort_order = models.IntegerField(default=100)

    class Meta:
        verbose_name_plural = "Currencies"
        ordering = ['sort_order', 'code']

    def __str__(self):
        return f"{self.symbol} ({self.code})"

class IncomeFrequency(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=50)          
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name_plural = "Income Frequencies"

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es requerido')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'

    objects = UserManager()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['created_at']),
        ]
        
    def get_full_name(self):
        if hasattr(self, "profile"):
            return f"{self.profile.first_name} {self.profile.last_name}".strip()
        return ""
        
    def get_short_name(self):
        if hasattr(self, "profile"):
            return self.profile.first_name
        return ""
        
    def __str__(self):
        if hasattr(self, "profile"):
            return f"{self.get_full_name()} ({self.email})"
        return self.email

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    first_name = models.CharField(max_length=150, null=True, blank=True)
    last_name = models.CharField(max_length=150, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True)
    income_frequency = models.ForeignKey(IncomeFrequency, on_delete=models.PROTECT, null=True, blank=True, related_name="profiles")

    class Meta:
        indexes = [
            models.Index(fields=['salary']),
            models.Index(fields=['income_frequency']),
            models.Index(fields=['phone']),
        ]

    def __str__(self):
        return f"Profile of {self.user.name}"