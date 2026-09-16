from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from users.models import User


class FinancialRecordType(models.Model):
    BEHAVIOR_CHOICES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
        ('TRANSFER', 'Transfer'),
    ]
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    behavior = models.CharField(max_length=20, choices=BEHAVIOR_CHOICES, default='EXPENSE')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=50)
    record_type = models.ForeignKey(FinancialRecordType, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='custom_categories')
    color = models.CharField(max_length=30, blank=True, default='')
    icon = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['record_type', 'name']
        unique_together = ['name', 'record_type', 'user']

    def __str__(self):
        return self.name


class CategoryKeyword(models.Model):
    category = models.ForeignKey(Category, related_name='keywords', on_delete=models.CASCADE)
    keyword = models.CharField(max_length=100)

    class Meta:
        unique_together = ['category', 'keyword']
        ordering = ['category', 'keyword']

    def clean(self):
        if self.keyword:
            self.keyword = self.keyword.strip().lower()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.keyword} -> {self.category.name}"


class FinancialGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='financial_goals')
    name = models.CharField(max_length=255)
    target_amount = models.DecimalField(max_digits=15, decimal_places=2)
    saved_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    target_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.user.email}"


class FinancialRecord(models.Model):
    user = models.ForeignKey(User, related_name="financial_records", on_delete=models.CASCADE)
    dashboard = models.ForeignKey('dashboard.UserFinanceDashboard', on_delete=models.PROTECT, null=False, blank=False, related_name='financial_records')
    record_type = models.ForeignKey(FinancialRecordType, on_delete=models.PROTECT)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    payment_method = models.ForeignKey('payments.PaymentMethod', on_delete=models.SET_NULL, null=True, blank=True)
    payment_status = models.ForeignKey('payments.PaymentStatus', on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    description = models.TextField(blank=True)
    record_date = models.DateField()
    is_recurrent = models.BooleanField(default=False)
    current_installment = models.PositiveIntegerField(null=True, blank=True)
    total_installments = models.PositiveIntegerField(null=True, blank=True)
    financial_goal = models.ForeignKey(FinancialGoal, on_delete=models.SET_NULL, null=True, blank=True, related_name='linked_records')
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(User, related_name="created_records", on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-record_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'record_date']),
            models.Index(fields=['record_type', 'category']),
            models.Index(fields=['is_recurrent']),
            models.Index(fields=['dashboard']),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.category and self.record_type:
            if self.category.record_type != self.record_type:
                raise ValidationError(
                    f"La categoría '{self.category.name}' pertenece al tipo '{self.category.record_type.name}', "
                    f"pero el registro está marcado como '{self.record_type.name}'. "
                    "Deben coincidir."
                )
        if self.dashboard and self.dashboard.user_id != self.user_id:
            raise ValidationError("El dashboard pertenece a otro usuario")
        if self.dashboard and not self.dashboard.is_active:
            raise ValidationError("No se pueden agregar o editar registros en un dashboard desactivado/archivado")
        if self.dashboard and self.record_type:
            if self.dashboard.dashboard_type == 'INCOME' and self.record_type.behavior == 'EXPENSE':
                raise ValidationError("No se permiten movimientos de tipo gasto en un dashboard de solo ingresos.")
            elif self.dashboard.dashboard_type == 'EXPENSES' and self.record_type.behavior == 'INCOME':
                raise ValidationError("No se permiten movimientos de tipo ingreso en un dashboard de solo gastos.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.record_type.name} - {self.amount}"


class FinancialRecordMetadata(models.Model):
    FREQUENCY_TYPES = [
        ("days", "Days"),
        ("weeks", "Weeks"),
        ("months", "Months"),
        ("years", "Years"),
    ]

    financial_record = models.OneToOneField(FinancialRecord, on_delete=models.CASCADE)
    currency = models.ForeignKey('users.Currency', on_delete=models.PROTECT, null=True, blank=True)
    frequency_type = models.CharField(max_length=10, choices=FREQUENCY_TYPES, null=True, blank=True)
    frequency_value = models.IntegerField(null=True, blank=True)
    next_occurrence = models.DateField(null=True, blank=True)
    extra_notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-next_occurrence']
        indexes = [
            models.Index(fields=['is_active', 'next_occurrence']),
        ]

    def calculate_next_occurrence(self):
        if not self.frequency_type or not self.frequency_value:
            return None

        last_date = self.financial_record.record_date
        if self.next_occurrence:
            last_date = self.next_occurrence

        if self.frequency_type == 'days':
            return last_date + timedelta(days=self.frequency_value)
        elif self.frequency_type == 'weeks':
            return last_date + timedelta(weeks=self.frequency_value)
        elif self.frequency_type == 'months':
            # Simple month addition
            month = last_date.month - 1 + self.frequency_value
            year = last_date.year + month // 12
            month = month % 12 + 1
            return last_date.replace(year=year, month=month)
        elif self.frequency_type == 'years':
            return last_date.replace(year=last_date.year + self.frequency_value)

        return None

    def save(self, *args, **kwargs):
        if self.is_active and self.frequency_type and self.frequency_value:
            self.next_occurrence = self.calculate_next_occurrence()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Metadata for Record {self.financial_record_id}" 
