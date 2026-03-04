import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from users.models import User
from cars.models import Car
from bookings.models import Booking
from notifications.models import Notification
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

# -----------------------------------------------------------------------------
# FIXTURES
# -----------------------------------------------------------------------------

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def dealer_user(db):
    return User.objects.create_user(
        email='dealer@carsphere.com',
        password='password123',
        role='DEALER'
    )

@pytest.fixture
def other_dealer(db):
    return User.objects.create_user(
        email='other_dealer@carsphere.com',
        password='password123',
        role='DEALER'
    )

@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        email='user@carsphere.com',
        password='password123',
        role='USER'
    )

@pytest.fixture
def car(dealer_user):
    return Car.objects.create(
        dealer=dealer_user,
        brand='BMW',
        model='M4',
        year=2024,
        price_per_day=Decimal('150.00'),
        fuel_type='PETROL',
        transmission='AUTOMATIC',
        latitude=48.8566,
        longitude=2.3522
    )

# -----------------------------------------------------------------------------
# AUTH & PERMISSION TESTS
# -----------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuthentication:
    def test_user_registration(self, api_client):
        url = reverse('register')
        data = {
            'email': 'newuser@example.com',
            'password': 'securepassword123',
            'role': 'USER'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email='newuser@example.com').exists()

    def test_login_and_jwt_token(self, api_client, regular_user):
        url = reverse('login')
        data = {
            'email': regular_user.email,
            'password': 'password123'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

# -----------------------------------------------------------------------------
# CAR MANAGEMENT TESTS
# -----------------------------------------------------------------------------

@pytest.mark.django_db
class TestCarManagement:
    def test_dealer_can_create_car(self, api_client, dealer_user):
        api_client.force_authenticate(user=dealer_user)
        url = reverse('car-list')
        data = {
            'brand': 'Audi',
            'model': 'RS6',
            'year': 2023,
            'price_per_day': '200.00',
            'fuel_type': 'PETROL',
            'transmission': 'AUTOMATIC',
            'latitude': 52.5200,
            'longitude': 13.4050
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Car.objects.filter(model='RS6').exists()

    def test_regular_user_cannot_create_car(self, api_client, regular_user):
        api_client.force_authenticate(user=regular_user)
        url = reverse('car-list')
        data = {'brand': 'Fake'}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_dealer_cannot_edit_others_car(self, api_client, other_dealer, car):
        api_client.force_authenticate(user=other_dealer)
        url = reverse('car-detail', kwargs={'pk': car.id})
        data = {'brand': 'Hacked'}
        response = api_client.patch(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

# -----------------------------------------------------------------------------
# BOOKING & LOGIC TESTS
# -----------------------------------------------------------------------------

@pytest.mark.django_db
class TestBookingSystem:
    def test_user_can_create_pending_booking(self, api_client, regular_user, car):
        api_client.force_authenticate(user=regular_user)
        url = reverse('booking-list')
        start = timezone.now() + timedelta(days=5)
        end = start + timedelta(days=3)
        data = {
            'car': car.id,
            'start_datetime': start.isoformat(),
            'end_datetime': end.isoformat()
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'PENDING'
        # Check automatic price calculation: 3 days * 150 = 450
        assert Decimal(response.data['total_price']) == Decimal('450.00')

    def test_booking_overlap_prevention(self, api_client, regular_user, car):
        # 1. First confirmed booking
        start = timezone.now() + timedelta(days=10)
        end = start + timedelta(days=2)
        Booking.objects.create(
            user=regular_user, car=car, start_datetime=start,
            end_datetime=end, status='CONFIRMED', total_price=Decimal('300.00')
        )

        # 2. Try to book exactly same time
        api_client.force_authenticate(user=regular_user)
        url = reverse('booking-list')
        response = api_client.post(url, {
            'car': car.id,
            'start_datetime': start.isoformat(),
            'end_datetime': end.isoformat()
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already booked" in str(response.data)

    def test_dealer_approval_workflow(self, api_client, dealer_user, regular_user, car):
        booking = Booking.objects.create(
            user=regular_user, car=car, 
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=2),
            status='PENDING', total_price=Decimal('150.00')
        )
        api_client.force_authenticate(user=dealer_user)
        url = reverse('booking-approve', kwargs={'pk': booking.id})
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        booking.refresh_from_db()
        assert booking.status == 'CONFIRMED'
        # Notification should be created
        assert Notification.objects.filter(user=regular_user).exists()

# -----------------------------------------------------------------------------
# GEO-FILTERING TESTS
# -----------------------------------------------------------------------------

@pytest.mark.django_db
class TestGeoFiltering:
    def test_bounding_box_query(self, api_client, car):
        # Car is at 48.8566, 2.3522 (Paris)
        url = reverse('car-list')
        # BBox around Paris
        response = api_client.get(url, {'north': 49, 'south': 48, 'east': 3, 'west': 2})
        assert len(response.data) == 1
        
        # BBox for Berlin
        response = api_client.get(url, {'north': 53, 'south': 52, 'east': 14, 'west': 13})
        assert len(response.data) == 0

    def test_haversine_radius_query(self, api_client, car):
        url = reverse('car-list')
        # Within 50km of Paris center
        response = api_client.get(url, {'lat': 48.8566, 'lng': 2.3522, 'radius': 50})
        assert len(response.data) == 1
        
        # Within 50km of London
        response = api_client.get(url, {'lat': 51.5074, 'lng': -0.1278, 'radius': 50})
        assert len(response.data) == 0

# -----------------------------------------------------------------------------
# ANALYTICS TESTS
# -----------------------------------------------------------------------------

@pytest.mark.django_db
class TestAnalytics:
    def test_dealer_analytics_summary(self, api_client, dealer_user, regular_user, car):
        # Create a confirmed booking to generate revenue
        Booking.objects.create(
            user=regular_user, car=car, 
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=2),
            status='CONFIRMED', total_price=Decimal('150.00')
        )
        
        api_client.force_authenticate(user=dealer_user)
        url = reverse('dealer_analytics')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_cars'] == 1
        assert response.data['total_revenue'] == 150.00
        assert response.data['confirmed_bookings'] == 1
