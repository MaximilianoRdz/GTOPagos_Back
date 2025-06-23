from django.db import models
from django.core.validators import EmailValidator
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin
)
from django.utils import timezone

# Eliminar los campos first_name y last_name del modelo User de Django
from django.contrib.auth.models import User as AuthUser
if hasattr(AuthUser, 'first_name'):
    AuthUser.first_name = None
if hasattr(AuthUser, 'last_name'):
    AuthUser.last_name = None


class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=5)

    class Meta:
        verbose_name_plural = "Currencies"
        ordering = ['code']

    def __str__(self):
        return f"{self.symbol} ({self.code})"


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
    INCOME_FREQUENCIES = [
        ("weekly", "Weekly"),
        ("biweekly", "Biweekly"),
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]

    email = models.EmailField(unique=True, validators=[EmailValidator()])
    name = models.CharField(max_length=100)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    income_frequency = models.CharField(max_length=10, choices=INCOME_FREQUENCIES, default="monthly", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = UserManager()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['created_at']),
        ]
        
    def get_full_name(self):
        return self.name
        
    def get_short_name(self):
        return self.name.split()[0] if self.name else ''
        
    def __str__(self):
        return f"{self.name} ({self.email})"