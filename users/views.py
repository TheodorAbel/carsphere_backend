from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import UserSerializer, CustomTokenObtainPairSerializer
from .models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Count, Sum
from bookings.models import Booking
from cars.models import Car

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserSerializer

class LoginView(TokenObtainPairView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = CustomTokenObtainPairSerializer

class DealerAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != 'DEALER':
            return Response({"error": "Only dealers can access analytics."}, status=403)

        dealer_cars = Car.objects.filter(dealer=request.user)
        dealer_bookings = Booking.objects.filter(car__in=dealer_cars)

        stats = {
            "total_cars": dealer_cars.count(),
            "total_bookings": dealer_bookings.count(),
            "confirmed_bookings": dealer_bookings.filter(status='CONFIRMED').count(),
            "total_revenue": dealer_bookings.filter(status='CONFIRMED').aggregate(Sum('total_price'))['total_price__sum'] or 0,
            "bookings_by_status": dealer_bookings.values('status').annotate(count=Count('status')),
            "top_cars": dealer_bookings.values('car__brand', 'car__model').annotate(count=Count('id')).order_by('-count')[:5]
        }

        return Response(stats)
