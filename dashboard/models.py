from django.db import models
from django.conf import settings
from users.models import Currency


class UserFinanceDashboard(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dashboards")
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["user"])]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Dashboard {self.id} for {self.user_id}"
