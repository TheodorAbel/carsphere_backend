import csv
import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from cars.models import Car

User = get_user_model()


class Command(BaseCommand):
    help = "Import cars from a CSV file and append to the database."

    def add_arguments(self, parser):
        parser.add_argument("--path", required=True)
        parser.add_argument("--use-id", action="store_true")
        parser.add_argument("--skip-existing", action="store_true")

    def handle(self, *args, **options):
        path = Path(options["path"]).expanduser()
        if not path.exists():
            raise SystemExit(f"CSV not found: {path}")

        use_id = options["use_id"]
        skip_existing = options["skip_existing"]

        created = 0
        skipped = 0

        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    dealer_id = int(row.get("dealer_id") or 0)
                except ValueError:
                    dealer_id = 0

                dealer = None
                if dealer_id:
                    dealer = User.objects.filter(id=dealer_id).first()
                if dealer is None:
                    dealer = User.objects.filter(role="DEALER").first()
                    if dealer is None:
                        dealer = User.objects.create_user(
                            email="dealer@carsphere.local",
                            password="dealer1234",
                            role="DEALER",
                        )

                images_raw = row.get("images") or "[]"
                try:
                    images = json.loads(images_raw)
                    if not isinstance(images, list):
                        images = []
                except json.JSONDecodeError:
                    images = []

                image = row.get("image") or (images[0] if images else None)

                brand = (row.get("brand") or "").strip()
                model = (row.get("model") or "").strip()
                year = int(row.get("year") or 0)

                if skip_existing:
                    exists = Car.objects.filter(
                        brand=brand,
                        model=model,
                        year=year,
                        image=image,
                    ).exists()
                    if exists:
                        skipped += 1
                        continue

                car_kwargs = {
                    "dealer": dealer,
                    "brand": brand,
                    "model": model,
                    "year": year,
                    "price_per_day": Decimal(row.get("price_per_day") or 0),
                    "fuel_type": (row.get("fuel_type") or "PETROL").strip(),
                    "transmission": (row.get("transmission") or "AUTOMATIC").strip(),
                    "latitude": Decimal(row.get("latitude") or 0),
                    "longitude": Decimal(row.get("longitude") or 0),
                    "image": image,
                    "images": images,
                }

                if use_id and row.get("id"):
                    car_kwargs["id"] = int(row["id"])

                Car.objects.create(**car_kwargs)
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {created} cars. Skipped {skipped}."))
