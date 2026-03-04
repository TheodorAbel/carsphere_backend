from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from cars.models import Car

class Booking(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('REJECTED', 'Rejected'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
        limit_choices_to={'role': 'USER'}
    )
    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking {self.id} - {self.car} by {self.user}"

    def clean(self):
        if self.start_datetime >= self.end_datetime:
            raise ValidationError("Start time must be before end time.")
        
        # Conflict check logic moved to serializer/view for better control,
        # but basic validation can stay here.
        pass
