from django.db import models
from django.conf import settings
from decimal import Decimal
from django.core.validators import MinValueValidator
from users.models import Currency


class UserFinanceDashboard(models.Model):
    DASHBOARD_TYPE_CHOICES = [
        ('EXPENSES', 'Expenses'),
        ('INCOME', 'Income'),
        ('BOTH', 'Both'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dashboards")
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100, default="", blank=True)
    description = models.TextField(blank=True)
    monthly_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Límite o presupuesto mensual asignado específicamente a este dashboard/tarjeta."
    )
    dashboard_type = models.CharField(
        max_length=10,
        choices=DASHBOARD_TYPE_CHOICES,
        default='BOTH',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["user"])]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        display = self.name or f"Dashboard {self.id}"
        return f"{display} for {self.user_id}"
