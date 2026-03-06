from rest_framework import serializers
from .models import Booking
from cars.models import Car
from django.utils import timezone

class BookingSerializer(serializers.ModelSerializer):
    car_details = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            'id', 'user', 'car', 'car_details', 'start_datetime', 
            'end_datetime', 'status', 'total_price', 'created_at'
        )
        read_only_fields = ('user', 'total_price', 'created_at')

    def get_car_details(self, obj):
        return {
            'brand': obj.car.brand,
            'model': obj.car.model,
            'price_per_day': obj.car.price_per_day
        }

    def validate(self, data):
        start = data['start_datetime']
        end = data['end_datetime']

        if start < timezone.now():
            raise serializers.ValidationError("Cannot book in the past.")
        
        if start >= end:
            raise serializers.ValidationError("Start time must be before end time.")

        # Check for overlaps with CONFIRMED bookings
        car = data['car']
        overlaps = Booking.objects.filter(
            car=car,
            status='CONFIRMED',
            start_datetime__lt=end,
            end_datetime__gt=start
        )
        
        if overlaps.exists():
            raise serializers.ValidationError("This car is already booked for the selected period.")

        return data
