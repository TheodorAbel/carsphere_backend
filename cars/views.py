import os

from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Car
from .serializers import CarSerializer
from users.permissions import IsDealer, IsOwnerOrReadOnly
from cars.management.commands.import_auto_dev import Command as ImportAutoDevCommand


class CarViewSet(viewsets.ModelViewSet):
    queryset = Car.objects.all()
    serializer_class = CarSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['brand', 'fuel_type', 'transmission']
    search_fields = ['brand', 'model']
    ordering_fields = ['price_per_day', 'year', 'created_at']

    def get_permissions(self):
        if self.action in ['create']:
            return [IsDealer()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwnerOrReadOnly()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save(dealer=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()

        # Dealer-only filter for "my cars"
        mine = self.request.query_params.get('mine')
        if (
            mine in ['1', 'true', 'True', 'yes', 'YES']
            and self.request.user.is_authenticated
            and self.request.user.role == 'DEALER'
        ):
            queryset = queryset.filter(dealer=self.request.user)

        # Bounding Box Filtering (Level 3)
        north = self.request.query_params.get('north')
        south = self.request.query_params.get('south')
        east = self.request.query_params.get('east')
        west = self.request.query_params.get('west')

        if all([north, south, east, west]):
            queryset = queryset.filter(
                latitude__lte=north,
                latitude__gte=south,
                longitude__lte=east,
                longitude__gte=west
            )

        # Radius Filtering (lat, lng, radius in km)
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        radius = self.request.query_params.get('radius')

        if lat and lng and radius:
            try:
                lat = float(lat)
                lng = float(lng)
                radius = float(radius)

                from django.db.models import ExpressionWrapper, F, FloatField
                from django.db.models.functions import ACos, Cos, Radians, Sin

                distance_expr = ExpressionWrapper(
                    ACos(
                        Sin(Radians(lat)) * Sin(Radians(F('latitude'))) +
                        Cos(Radians(lat)) * Cos(Radians(F('latitude'))) *
                        Cos(Radians(F('longitude')) - Radians(lng))
                    ) * 6371.0,
                    output_field=FloatField()
                )
                queryset = queryset.annotate(distance=distance_expr).filter(distance__lte=radius)
            except (ValueError, TypeError):
                pass

        # Price range filtering (supports min_price/max_price or price_min/price_max)
        min_price = self.request.query_params.get('min_price') or self.request.query_params.get('price_min')
        max_price = self.request.query_params.get('max_price') or self.request.query_params.get('price_max')
        if min_price:
            try:
                queryset = queryset.filter(price_per_day__gte=min_price)
            except (ValueError, TypeError):
                pass
        if max_price:
            try:
                queryset = queryset.filter(price_per_day__lte=max_price)
            except (ValueError, TypeError):
                pass

        return queryset

    @action(detail=False, methods=['get'], permission_classes=[IsDealer], url_path='dealer')
    def dealer_cars(self, request):
        queryset = Car.objects.filter(dealer=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny], url_path='import-auto-dev')
    def import_auto_dev(self, request):
        token = request.headers.get('X-Import-Token') or request.query_params.get('token')
        expected = os.getenv('AUTO_DEV_IMPORT_TOKEN')
        if not expected or token != expected:
            return Response({"detail": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)

        data = request.data or {}
        options = {
            "count": int(data.get("count", 100)),
            "photos_min": int(data.get("photos_min", 1)),
            "photos_max": int(data.get("photos_max", 5)),
            "dealers": int(data.get("dealers", 5)),
            "min_price": int(data.get("min_price", 900)),
            "max_price": int(data.get("max_price", 4500)),
            "reset": bool(data.get("reset", True)),
            "page": int(data.get("page", 1)),
            "limit": int(data.get("limit", 100)),
            "max_pages": int(data.get("max_pages", 20)),
            "vehicle_year": data.get("vehicle_year", ""),
            "vehicle_make": data.get("vehicle_make", ""),
            "vehicle_model": data.get("vehicle_model", ""),
            "api_key": data.get("api_key", ""),
            "base_url": data.get("base_url", ""),
            "auth": data.get("auth", "apikey"),
            "allowed_models": data.get("allowed_models", ""),
            "allowed_makes": data.get("allowed_makes", ""),
            "max_per_model": int(data.get("max_per_model", 6)),
            "excluded_makes": data.get("excluded_makes", ""),
            "skip_existing": bool(data.get("skip_existing", False)),
            "debug": bool(data.get("debug", False)),
        }

        ImportAutoDevCommand().handle(**options)
        return Response({"detail": "Import completed.", "options": options})
