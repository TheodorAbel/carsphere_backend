import json
import os
import random
import time
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from cars.models import Car

User = get_user_model()


class Command(BaseCommand):
    help = "Import cars from Auto.dev and replace existing cars."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=100)
        parser.add_argument("--photos-min", type=int, default=1)
        parser.add_argument("--photos-max", type=int, default=5)
        parser.add_argument("--dealers", type=int, default=5)
        parser.add_argument("--min-price", type=int, default=900)
        parser.add_argument("--max-price", type=int, default=4500)
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--page", type=int, default=1)
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--max-pages", type=int, default=20)
        parser.add_argument("--vehicle-year", type=str, default="")
        parser.add_argument("--vehicle-make", type=str, default="")
        parser.add_argument("--vehicle-model", type=str, default="")
        parser.add_argument("--api-key", type=str, default="")
        parser.add_argument("--base-url", type=str, default="")
        parser.add_argument("--auth", type=str, default="header")
        parser.add_argument("--allowed-models", type=str, default="")
        parser.add_argument("--allowed-makes", type=str, default="")
        parser.add_argument("--max-per-model", type=int, default=6)
        parser.add_argument("--excluded-makes", type=str, default="")
        parser.add_argument("--debug", action="store_true")

    def handle(self, *args, **options):
        api_key = options["api_key"] or os.getenv("AUTO_DEV_API_KEY")
        if not api_key:
            raise SystemExit("AUTO_DEV_API_KEY is not set in the environment.")

        base_url = (
            options["base_url"]
            or os.getenv("AUTO_DEV_BASE_URL", "https://api.auto.dev")
        ).rstrip("/")
        listings_url = f"{base_url}/listings"
        photos_url = f"{base_url}/photos"

        dealers = self._get_dealers(options["dealers"])
        if options["reset"]:
            Car.objects.all().delete()
            self.stdout.write(self.style.WARNING("Deleted all existing cars."))

        locations = [
            ("Bole", 9.0110, 38.7900),
            ("Piazza", 9.0379, 38.7590),
            ("Sar Bet", 9.0060, 38.7320),
            ("Megenagna", 9.0200, 38.8090),
            ("Mexico", 8.9980, 38.7370),
        ]

        target = options["count"]
        photos_min = max(1, options["photos_min"])
        photos_max = max(photos_min, options["photos_max"])
        min_price = options["min_price"]
        max_price = options["max_price"]
        limit = max(1, min(100, options["limit"]))
        max_pages = max(1, options["max_pages"])

        created = 0
        used_vins = set()
        model_counts = {}

        allowed = self._parse_allowed_models(options["allowed_models"])
        allowed_makes = self._parse_allowed_makes(options["allowed_makes"])
        excluded = self._parse_excluded_makes(options["excluded_makes"])
        max_per_model = max(1, options["max_per_model"])

        makes_queue = allowed_makes or ([options["vehicle_make"]] if options["vehicle_make"] else [""])

        for make in makes_queue:
            page = max(1, options["page"])
            page_count = 0
            while created < target and page_count < max_pages:
                params = {
                    "page": page,
                    "limit": limit,
                }
                if options["vehicle_year"]:
                    params["vehicle.year"] = options["vehicle_year"]
                if make:
                    params["vehicle.make"] = make
                if options["vehicle_model"]:
                    params["vehicle.model"] = options["vehicle_model"]

                listings, status, error = self._fetch_listings(
                    listings_url,
                    api_key,
                    params,
                    auth_mode=options["auth"],
                )
                if options["debug"] and (status != 200):
                    self.stdout.write(self.style.WARNING(f"Listings request status={status} error={error}"))
                if not listings:
                    if options["debug"]:
                        self.stdout.write(self.style.WARNING("No listings returned for current page."))
                    break

                for listing in listings:
                    if created >= target:
                        break

                    vehicle = listing.get("vehicle", {}) if isinstance(listing, dict) else {}
                    vin = listing.get("vin") or vehicle.get("vin")
                    if not vin or vin in used_vins:
                        continue

                    brand = vehicle.get("make") or listing.get("make")
                    model = vehicle.get("model") or listing.get("model")
                    year = vehicle.get("year") or listing.get("year") or listing.get("model_year")
                    if not (brand and model and year):
                        continue

                    brand_norm = str(brand).strip()
                    model_norm = str(model).strip()
                    make_key = self._norm(brand_norm)
                    model_key = self._norm(model_norm)
                    key = (make_key, model_key)

                    if excluded and make_key in excluded:
                        continue

                    if allowed and not self._match_allowed(make_key, model_key, allowed):
                        continue

                    count = model_counts.get(key, 0)
                    if count >= max_per_model:
                        continue

                    photos, photo_status, photo_error = self._fetch_photos(
                        photos_url,
                        api_key,
                        vin,
                        auth_mode=options["auth"],
                    )
                    if options["debug"] and photo_status != 200:
                        self.stdout.write(self.style.WARNING(f"Photos status={photo_status} vin={vin} error={photo_error}"))
                    if len(photos) < photos_min:
                        continue

                    used_vins.add(vin)
                    dealer = dealers[created % len(dealers)]
                    _, base_lat, base_lng = random.choice(locations)

                    price = self._derive_price(listing, min_price, max_price)
                    fuel = self._map_fuel(vehicle, listing)
                    transmission = self._map_transmission(vehicle, listing)

                    lat_offset = random.uniform(-0.003, 0.003)
                    lng_offset = random.uniform(-0.003, 0.003)
                    lat = round(base_lat + lat_offset, 6)
                    lng = round(base_lng + lng_offset, 6)

                    images = photos[:photos_max]

                    Car.objects.create(
                        dealer=dealer,
                        brand=brand_norm,
                        model=model_norm,
                        year=int(year),
                        price_per_day=price,
                        fuel_type=fuel,
                        transmission=transmission,
                        image=images[0],
                        images=images,
                        latitude=Decimal(str(lat)),
                        longitude=Decimal(str(lng)),
                    )

                    created += 1
                    model_counts[key] = count + 1

                page += 1
                page_count += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {created} cars from Auto.dev."))

    def _parse_allowed_models(self, raw):
        if not raw:
            return set()
        allowed = set()
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        for part in parts:
            if ":" in part:
                make, model = part.split(":", 1)
                make_key = self._norm(make)
                model_key = self._norm(model) if model.strip() else "*"
                allowed.add((make_key, model_key))
        return allowed

    def _parse_allowed_makes(self, raw):
        if not raw:
            return []
        return [x.strip() for x in raw.split(",") if x.strip()]

    def _parse_excluded_makes(self, raw):
        if not raw:
            return set()
        return {self._norm(x) for x in raw.split(",") if x.strip()}

    def _norm(self, value):
        return "".join(ch for ch in str(value).lower() if ch.isalnum())

    def _match_allowed(self, make_key, model_key, allowed):
        for make, model in allowed:
            if make != make_key:
                continue
            if model == "*":
                return True
            if model in model_key:
                return True
        return False

    def _get_dealers(self, count):
        dealers = []
        for i in range(count):
            email = f"dealer{i+1}@carsphere.local"
            dealer = User.objects.filter(email=email).first()
            if dealer is None:
                dealer = User.objects.create_user(email=email, password="dealer1234", role="DEALER")
            dealers.append(dealer)
        return dealers

    def _apply_auth(self, req, api_key, auth_mode):
        if auth_mode in ("header", "both"):
            req.add_header("Authorization", f"Bearer {api_key}")
        if auth_mode in ("apikey", "both"):
            req.add_header("x-api-key", api_key)
            req.add_header("apikey", api_key)

    def _fetch_listings(self, url, api_key, params, auth_mode="header"):
        query = urlencode(params)
        if auth_mode in ("query", "both"):
            query = f"{query}&apiKey={api_key}"
        req = Request(f"{url}?{query}")
        self._apply_auth(req, api_key, auth_mode)
        req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                status = resp.status
        except HTTPError as e:
            return [], e.code, e.read().decode("utf-8")
        except (URLError, TimeoutError) as e:
            return [], 0, str(e)

        data = payload.get("data") if isinstance(payload, dict) else payload
        if isinstance(data, list):
            return data, status, None
        if isinstance(data, dict):
            for key in ("listings", "results", "records"):
                if isinstance(data.get(key), list):
                    return data.get(key), status, None
        for key in ("listings", "results", "records"):
            if isinstance(payload, dict) and isinstance(payload.get(key), list):
                return payload.get(key), status, None
        return [], status, None

    def _fetch_photos(self, url, api_key, vin, auth_mode="header"):
        photo_url = f"{url}/{vin}"
        if auth_mode in ("query", "both"):
            photo_url = f"{photo_url}?apiKey={api_key}"
        req = Request(photo_url)
        self._apply_auth(req, api_key, auth_mode)
        req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                status = resp.status
        except HTTPError as e:
            return [], e.code, e.read().decode("utf-8")
        except (URLError, TimeoutError) as e:
            return [], 0, str(e)

        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        photos = data.get("retail") if isinstance(data, dict) else []
        return photos or [], status, None

    def _derive_price(self, listing, min_price, max_price):
        price_candidates = [
            listing.get("price"),
            listing.get("list_price"),
            listing.get("msrp"),
            listing.get("retail_price"),
        ]
        for value in price_candidates:
            try:
                if value is not None:
                    raw = float(value)
                    per_day = max(min_price, min(max_price, raw / 10))
                    return Decimal(str(round(per_day, 2)))
            except (ValueError, TypeError):
                continue
        fallback = random.randint(min_price, max_price)
        return Decimal(str(fallback))

    def _map_fuel(self, vehicle, listing):
        value = (
            vehicle.get("fuel_type")
            or vehicle.get("fuelType")
            or vehicle.get("fuel")
            or listing.get("fuel_type")
        )
        if not value:
            return random.choice(["PETROL", "DIESEL", "ELECTRIC", "HYBRID"])
        text = str(value).lower()
        if "diesel" in text:
            return "DIESEL"
        if "electric" in text or "ev" in text:
            return "ELECTRIC"
        if "hybrid" in text:
            return "HYBRID"
        return "PETROL"

    def _map_transmission(self, vehicle, listing):
        value = vehicle.get("transmission") or listing.get("transmission")
        if not value:
            return random.choice(["MANUAL", "AUTOMATIC"])
        text = str(value).lower()
        if "auto" in text:
            return "AUTOMATIC"
        return "MANUAL"
