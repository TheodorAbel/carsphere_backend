from django.db import models
from django.conf import settings

class Notification(models.Model):
    CATEGORY_CHOICES = (
        ('BOOKING', 'Booking'),
        ('SYSTEM', 'System'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='BOOKING')
    title = models.CharField(max_length=100)
    message = models.TextField()
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.email}: {self.title}"
