from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Booking
from .serializers import BookingSerializer
from users.permissions import IsUser, IsDealer, IsOwnerOrReadOnly

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def get_permissions(self):
        if self.action in ['create']:
            return [IsUser()]
        if self.action in ['update', 'partial_update']:
            return [IsDealer()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        car = serializer.validated_data['car']
        start = serializer.validated_data['start_datetime']
        end = serializer.validated_data['end_datetime']
        
        # Calculate total price
        duration = end - start
        days = max(duration.days + (1 if duration.seconds > 0 else 0), 1)
        total_price = days * car.price_per_day
        
        serializer.save(user=self.request.user, total_price=total_price)

    def get_queryset(self):
        user = self.request.user
        if user.role == 'DEALER':
            return Booking.objects.filter(car__dealer=user)
        return Booking.objects.filter(user=user)

    @action(detail=False, methods=['get'], permission_classes=[IsUser], url_path='user')
    def user_bookings(self, request):
        bookings = Booking.objects.filter(user=request.user)
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsDealer], url_path='dealer')
    def dealer_bookings(self, request):
        bookings = Booking.objects.filter(car__dealer=request.user)
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsDealer])
    def approve(self, request, pk=None):
        booking = self.get_object()
        if booking.car.dealer != request.user:
            return Response({"error": "Not allowed for this booking."}, status=status.HTTP_403_FORBIDDEN)
        
        # Re-verify conflicts before confirming (race condition check)
        overlaps = Booking.objects.filter(
            car=booking.car,
            status='CONFIRMED',
            start_datetime__lt=booking.end_datetime,
            end_datetime__gt=booking.start_datetime
        ).exclude(id=booking.id)

        if overlaps.exists():
            return Response(
                {"error": "Cannot approve. Another confirmed booking overlaps this period."},
                status=status.HTTP_400_BAD_REQUEST
            )

        booking.status = 'CONFIRMED'
        booking.save()
        
        # Real-time update: Broadcast availability change
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "availability",
                {
                    "type": "availability_update",
                    "car_id": booking.car.id,
                    "status": "booked",
                    "start": booking.start_datetime.isoformat(),
                    "end": booking.end_datetime.isoformat(),
                }
            )

        # Real-time update: Notify user
        from notifications.models import Notification
        Notification.objects.create(
            user=booking.user,
            category='BOOKING',
            title='Booking Confirmed',
            message=f"Your booking for {booking.car.brand} {booking.car.model} has been confirmed."
        )

        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"user_{booking.user.id}",
                {
                    "type": "user_notification",
                    "title": "Booking Confirmed",
                    "message": f"Your booking for {booking.car.brand} {booking.car.model} has been confirmed.",
                    "booking_id": booking.id
                }
            )
        
        return Response({"status": "booking confirmed"})

    @action(detail=True, methods=['post'], permission_classes=[IsDealer])
    def reject(self, request, pk=None):
        booking = self.get_object()
        if booking.car.dealer != request.user:
            return Response({"error": "Not allowed for this booking."}, status=status.HTTP_403_FORBIDDEN)
        booking.status = 'REJECTED'
        booking.save()
        return Response({"status": "booking rejected"})

    def partial_update(self, request, *args, **kwargs):
        booking = self.get_object()
        if booking.car.dealer != request.user:
            return Response({"error": "Not allowed for this booking."}, status=status.HTTP_403_FORBIDDEN)

        new_status = request.data.get('status')
        if new_status not in ['CONFIRMED', 'REJECTED']:
            return Response({"error": "Invalid status. Use CONFIRMED or REJECTED."}, status=status.HTTP_400_BAD_REQUEST)

        if new_status == 'CONFIRMED':
            # Re-verify conflicts before confirming (race condition check)
            overlaps = Booking.objects.filter(
                car=booking.car,
                status='CONFIRMED',
                start_datetime__lt=booking.end_datetime,
                end_datetime__gt=booking.start_datetime
            ).exclude(id=booking.id)

            if overlaps.exists():
                return Response(
                    {"error": "Cannot approve. Another confirmed booking overlaps this period."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            booking.status = 'CONFIRMED'
            booking.save()

            # Real-time update: Broadcast availability change
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()

            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    "availability",
                    {
                        "type": "availability_update",
                        "car_id": booking.car.id,
                        "status": "booked",
                        "start": booking.start_datetime.isoformat(),
                        "end": booking.end_datetime.isoformat(),
                    }
                )

            # Real-time update: Notify user
            from notifications.models import Notification
            Notification.objects.create(
                user=booking.user,
                category='BOOKING',
                title='Booking Confirmed',
                message=f"Your booking for {booking.car.brand} {booking.car.model} has been confirmed."
            )

            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"user_{booking.user.id}",
                    {
                        "type": "user_notification",
                        "title": "Booking Confirmed",
                        "message": f"Your booking for {booking.car.brand} {booking.car.model} has been confirmed.",
                        "booking_id": booking.id
                    }
                )
        else:
            booking.status = 'REJECTED'
            booking.save()

        serializer = self.get_serializer(booking)
        return Response(serializer.data)
