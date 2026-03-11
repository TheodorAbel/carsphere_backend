*** Begin Patch
*** Update File: C:\Users\ENVY 13\Documents\Dev\carsphere\cars\management\commands\import_auto_dev.py
@@
     def add_arguments(self, parser):
@@
         parser.add_argument("--allowed-models", type=str, default="")
+        parser.add_argument("--allowed-makes", type=str, default="")
         parser.add_argument("--max-per-model", type=int, default=6)
         parser.add_argument("--excluded-makes", type=str, default="")
         parser.add_argument("--debug", action="store_true")
@@
-        allowed = self._parse_allowed_models(options["allowed_models"])
+        allowed = self._parse_allowed_models(options["allowed_models"])
+        allowed_makes = self._parse_allowed_makes(options["allowed_makes"])
         excluded = self._parse_excluded_makes(options["excluded_makes"])
         max_per_model = max(1, options["max_per_model"])
@@
-        while created < target and page_count < max_pages:
-            params = {
-                "page": page,
-                "limit": limit,
-            }
-            if options["vehicle_year"]:
-                params["vehicle.year"] = options["vehicle_year"]
-            if options["vehicle_make"]:
-                params["vehicle.make"] = options["vehicle_make"]
-            if options["vehicle_model"]:
-                params["vehicle.model"] = options["vehicle_model"]
-
-            listings, status, error = self._fetch_listings(
-                listings_url,
-                api_key,
-                params,
-                auth_mode=options["auth"],
-            )
+        makes_queue = allowed_makes or [options["vehicle_make"]] if options["vehicle_make"] else [""]
+
+        for make in makes_queue:
+            page = max(1, options["page"])
+            page_count = 0
+            while created < target and page_count < max_pages:
+                params = {
+                    "page": page,
+                    "limit": limit,
+                }
+                if options["vehicle_year"]:
+                    params["vehicle.year"] = options["vehicle_year"]
+                if make:
+                    params["vehicle.make"] = make
+                if options["vehicle_model"]:
+                    params["vehicle.model"] = options["vehicle_model"]
+
+                listings, status, error = self._fetch_listings(
+                    listings_url,
+                    api_key,
+                    params,
+                    auth_mode=options["auth"],
+                )
             if options["debug"] and (status != 200):
                 self.stdout.write(self.style.WARNING(f"Listings request status={status} error={error}"))
             if not listings:
                 if options["debug"]:
                     self.stdout.write(self.style.WARNING("No listings returned for current page."))
-                break
-
-            for listing in listings:
-                if created >= target:
-                    break
-
-                vehicle = listing.get("vehicle", {}) if isinstance(listing, dict) else {}
-                vin = listing.get("vin") or vehicle.get("vin")
-                if not vin or vin in used_vins:
-                    continue
-
-                brand = vehicle.get("make") or listing.get("make")
-                model = vehicle.get("model") or listing.get("model")
-                year = vehicle.get("year") or listing.get("year") or listing.get("model_year")
-                if not (brand and model and year):
-                    continue
-
-                brand_norm = str(brand).strip()
-                model_norm = str(model).strip()
-                make_key = self._norm(brand_norm)
-                model_key = self._norm(model_norm)
-                key = (make_key, model_key)
-
-                if excluded and make_key in excluded:
-                    continue
-
-                if allowed and not self._match_allowed(make_key, model_key, allowed):
-                    continue
-
-                count = model_counts.get(key, 0)
-                if count >= max_per_model:
-                    continue
-
-                photos, photo_status, photo_error = self._fetch_photos(
-                    photos_url,
-                    api_key,
-                    vin,
-                    auth_mode=options["auth"],
-                )
-                if options["debug"] and photo_status != 200:
-                    self.stdout.write(self.style.WARNING(f"Photos status={photo_status} vin={vin} error={photo_error}"))
-                if len(photos) < photos_min:
-                    continue
-
-                used_vins.add(vin)
-                dealer = dealers[created % len(dealers)]
-                _, base_lat, base_lng = random.choice(locations)
-
-                price = self._derive_price(listing, min_price, max_price)
-                fuel = self._map_fuel(vehicle, listing)
-                transmission = self._map_transmission(vehicle, listing)
-
-                lat_offset = random.uniform(-0.003, 0.003)
-                lng_offset = random.uniform(-0.003, 0.003)
-                lat = round(base_lat + lat_offset, 6)
-                lng = round(base_lng + lng_offset, 6)
-
-                images = photos[:photos_max]
-
-                Car.objects.create(
-                    dealer=dealer,
-                    brand=brand_norm,
-                    model=model_norm,
-                    year=int(year),
-                    price_per_day=price,
-                    fuel_type=fuel,
-                    transmission=transmission,
-                    image=images[0],
-                    images=images,
-                    latitude=Decimal(str(lat)),
-                    longitude=Decimal(str(lng)),
-                )
-
-                created += 1
-                model_counts[key] = count + 1
-
-            page += 1
-            page_count += 1
+                break
+
+                for listing in listings:
+                    if created >= target:
+                        break
+
+                    vehicle = listing.get("vehicle", {}) if isinstance(listing, dict) else {}
+                    vin = listing.get("vin") or vehicle.get("vin")
+                    if not vin or vin in used_vins:
+                        continue
+
+                    brand = vehicle.get("make") or listing.get("make")
+                    model = vehicle.get("model") or listing.get("model")
+                    year = vehicle.get("year") or listing.get("year") or listing.get("model_year")
+                    if not (brand and model and year):
+                        continue
+
+                    brand_norm = str(brand).strip()
+                    model_norm = str(model).strip()
+                    make_key = self._norm(brand_norm)
+                    model_key = self._norm(model_norm)
+                    key = (make_key, model_key)
+
+                    if excluded and make_key in excluded:
+                        continue
+
+                    if allowed and not self._match_allowed(make_key, model_key, allowed):
+                        continue
+
+                    count = model_counts.get(key, 0)
+                    if count >= max_per_model:
+                        continue
+
+                    photos, photo_status, photo_error = self._fetch_photos(
+                        photos_url,
+                        api_key,
+                        vin,
+                        auth_mode=options["auth"],
+                    )
+                    if options["debug"] and photo_status != 200:
+                        self.stdout.write(self.style.WARNING(f"Photos status={photo_status} vin={vin} error={photo_error}"))
+                    if len(photos) < photos_min:
+                        continue
+
+                    used_vins.add(vin)
+                    dealer = dealers[created % len(dealers)]
+                    _, base_lat, base_lng = random.choice(locations)
+
+                    price = self._derive_price(listing, min_price, max_price)
+                    fuel = self._map_fuel(vehicle, listing)
+                    transmission = self._map_transmission(vehicle, listing)
+
+                    lat_offset = random.uniform(-0.003, 0.003)
+                    lng_offset = random.uniform(-0.003, 0.003)
+                    lat = round(base_lat + lat_offset, 6)
+                    lng = round(base_lng + lng_offset, 6)
+
+                    images = photos[:photos_max]
+
+                    Car.objects.create(
+                        dealer=dealer,
+                        brand=brand_norm,
+                        model=model_norm,
+                        year=int(year),
+                        price_per_day=price,
+                        fuel_type=fuel,
+                        transmission=transmission,
+                        image=images[0],
+                        images=images,
+                        latitude=Decimal(str(lat)),
+                        longitude=Decimal(str(lng)),
+                    )
+
+                    created += 1
+                    model_counts[key] = count + 1
+
+                page += 1
+                page_count += 1
@@
         self.stdout.write(self.style.SUCCESS(f"Imported {created} cars from Auto.dev."))
@@
     def _parse_excluded_makes(self, raw):
         if not raw:
             return set()
         return {self._norm(x) for x in raw.split(",") if x.strip()}
+
+    def _parse_allowed_makes(self, raw):
+        if not raw:
+            return []
+        return [x.strip() for x in raw.split(",") if x.strip()]
*** End Patch
