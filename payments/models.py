from django.db import models


class PaymentMethod(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class PaymentStatus(models.Model):
    status = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default="#000000")  # Hex color code
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Payment Statuses"
        ordering = ['status']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['is_active']),
        ]
    def __str__(self):
        return self.status 