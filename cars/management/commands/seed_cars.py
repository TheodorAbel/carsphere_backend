from decimal import Decimal
import random

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from cars.models import Car

User = get_user_model()


class Command(BaseCommand):
    help = "Seed discovery cars around Addis Ababa."

    def add_arguments(self, parser):
        parser.add_argument("--per-location", type=int, default=10)
        parser.add_argument("--dealers", type=int, default=3)
        parser.add_argument("--email", type=str, default="dealer@carsphere.local")
        parser.add_argument("--password", type=str, default="dealer1234")
        parser.add_argument("--min-price", type=int, default=900)
        parser.add_argument("--max-price", type=int, default=4500)
        parser.add_argument("--reset", action="store_true")

    def handle(self, *args, **options):
        per_location = options["per_location"]
        dealer_count = options["dealers"]
        email = options["email"]
        password = options["password"]
        min_price = options["min_price"]
        max_price = options["max_price"]
        reset = options["reset"]

        dealers = []
        if dealer_count <= 1:
            dealer = User.objects.filter(role="DEALER").first()
            if dealer is None:
                dealer = User.objects.create_user(email=email, password=password, role="DEALER")
                self.stdout.write(self.style.SUCCESS(f"Created dealer: {dealer.email}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Using dealer: {dealer.email}"))
            dealers = [dealer]
        else:
            for i in range(dealer_count):
                dealer_email = f"dealer{i+1}@carsphere.local"
                dealer = User.objects.filter(email=dealer_email).first()
                if dealer is None:
                    dealer = User.objects.create_user(email=dealer_email, password=password, role="DEALER")
                    self.stdout.write(self.style.SUCCESS(f"Created dealer: {dealer.email}"))
                dealers.append(dealer)

        if reset:
            deleted, _ = Car.objects.filter(dealer__in=dealers).delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing cars for seeded dealers."))

        # Five Addis Ababa zones (slightly adjusted coordinates)
        locations = [
            ("Bole", 9.0110, 38.7900),
            ("Piazza", 9.0379, 38.7590),
            ("Sar Bet", 9.0060, 38.7320),
            ("Megenagna", 9.0200, 38.8090),
            ("Mexico", 8.9980, 38.7370),
        ]

        brands = [
            ("Toyota", ["Corolla", "Yaris", "Rav4"]),
            ("Hyundai", ["Elantra", "Accent", "Tucson"]),
            ("Kia", ["Rio", "Sportage", "Sorento"]),
            ("Nissan", ["Sunny", "X-Trail", "Kicks"]),
            ("Honda", ["Civic", "Fit", "CR-V"]),
            ("Volkswagen", ["Golf", "Polo", "Tiguan"]),
        ]

        fuel_choices = ["PETROL", "DIESEL", "ELECTRIC", "HYBRID"]
        transmission_choices = ["MANUAL", "AUTOMATIC"]

        random.seed(42)
        cars_to_create = []
        for loc_index, (name, base_lat, base_lng) in enumerate(locations):
            for i in range(per_location):
                dealer = dealers[(loc_index + i) % len(dealers)]
                brand, models = random.choice(brands)
                model = random.choice(models)
                year = random.randint(2014, 2024)
                price = Decimal(str(random.randint(min_price, max_price)))
                fuel = random.choice(fuel_choices)
                transmission = random.choice(transmission_choices)

                # Small offsets to spread cars around each location
                lat_offset = random.uniform(-0.003, 0.003)
                lng_offset = random.uniform(-0.003, 0.003)
                lat = round(base_lat + lat_offset, 6)
                lng = round(base_lng + lng_offset, 6)

                image_url = (
                    f"https://picsum.photos/seed/"
                    f"{brand.lower()}-{model.lower()}-{loc_index}-{i}/600/400"
                )

                cars_to_create.append(
                    Car(
                        dealer=dealer,
                        brand=brand,
                        model=model,
                        year=year,
                        price_per_day=price,
                        fuel_type=fuel,
                        transmission=transmission,
                        image=image_url,
                        latitude=Decimal(str(lat)),
                        longitude=Decimal(str(lng)),
                    )
                )

        Car.objects.bulk_create(cars_to_create)
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(cars_to_create)} cars across {len(locations)} locations "
                f"for {len(dealers)} dealers."
            )
        )
