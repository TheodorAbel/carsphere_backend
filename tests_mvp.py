import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from users.models import User
from cars.models import Car
from bookings.models import Booking
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def dealer_user(db):
    return User.objects.create_user(
        email='dealer@example.com',
        password='password123',
        role='DEALER'
    )

@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        email='user@example.com',
        password='password123',
        role='USER'
    )

@pytest.fixture
def car(dealer_user):
    return Car.objects.create(
        dealer=dealer_user,
        brand='Tesla',
        model='Model 3',
        year=2023,
        price_per_day=Decimal('100.00'),
        fuel_type='ELECTRIC',
        transmission='AUTOMATIC',
        latitude=Decimal('40.7128'),
        longitude=Decimal('-74.0060')
    )

@pytest.mark.django_db
class TestBookingOverlap:
    def test_overlapping_booking_prevention(self, api_client, regular_user, car):
        # 1. Create a confirmed booking
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(days=2)
        
        Booking.objects.create(
            user=regular_user,
            car=car,
            start_datetime=start,
            end_datetime=end,
            status='CONFIRMED',
            total_price=Decimal('200.00')
        )
        
        # 2. Try to book the same car for an overlapping period
        api_client.force_authenticate(user=regular_user)
        overlap_start = start + timedelta(hours=1)
        overlap_end = end + timedelta(hours=1)
        
        response = api_client.post(reverse('booking-list'), {
            'car': car.id,
            'start_datetime': overlap_start.isoformat(),
            'end_datetime': overlap_end.isoformat()
        })
        
        assert response.status_code == 400
        assert "already booked" in str(response.data)

@pytest.mark.django_db
class TestGeoFiltering:
    def test_bounding_box_filter(self, api_client, car):
        # Car is at 40.7128, -74.0060 (NYC)
        # BBox around NYC
        response = api_client.get(reverse('car-list'), {
            'north': 41.0,
            'south': 40.0,
            'east': -73.0,
            'west': -75.0
        })
        assert response.status_code == 200
        assert len(response.data) == 1
        
        # BBox for LA (should return 0)
        response = api_client.get(reverse('car-list'), {
            'north': 35.0,
            'south': 33.0,
            'east': -117.0,
            'west': -119.0
        })
        assert len(response.data) == 0

    def test_radius_filter(self, api_client, car):
        # Within 10km of NYC center
        response = api_client.get(reverse('car-list'), {
            'lat': 40.7128,
            'lng': -74.0060,
            'radius': 10
        })
        assert len(response.data) == 1
        
        # Within 10km of LA (should return 0)
        response = api_client.get(reverse('car-list'), {
            'lat': 34.0522,
            'lng': -118.2437,
            'radius': 10
        })
        assert len(response.data) == 0
