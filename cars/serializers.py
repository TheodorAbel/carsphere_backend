from rest_framework import serializers
from .models import Car

class CarSerializer(serializers.ModelSerializer):
    dealer_email = serializers.ReadOnlyField(source='dealer.email')

    class Meta:
        model = Car
        fields = (
            'id', 'dealer', 'dealer_email', 'brand', 'model', 'year',
            'price_per_day', 'fuel_type', 'transmission', 'image',
            'latitude', 'longitude', 'created_at'
        )
        read_only_fields = ('dealer',)

    def create(self, validated_data):
        # Dealer will be set in the view
        return super().create(validated_data)
