from django.db import models
from django.conf import settings

class Car(models.Model):
    FUEL_CHOICES = (
        ('PETROL', 'Petrol'),
        ('DIESEL', 'Diesel'),
        ('ELECTRIC', 'Electric'),
        ('HYBRID', 'Hybrid'),
    )
    TRANSMISSION_CHOICES = (
        ('MANUAL', 'Manual'),
        ('AUTOMATIC', 'Automatic'),
    )

    dealer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cars',
        limit_choices_to={'role': 'DEALER'}
    )
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.PositiveIntegerField()
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    fuel_type = models.CharField(max_length=20, choices=FUEL_CHOICES)
    transmission = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES)
    image = models.URLField(blank=True, null=True)

    # Geo location
    latitude = models.DecimalField(max_digits=9, decimal_places=6, db_index=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.brand} {self.model} ({self.year})"
