*** Begin Patch
*** Update File: C:\Users\ENVY 13\Documents\Dev\carsphere\cars\management\commands\import_auto_dev.py
@@
     def add_arguments(self, parser):
         parser.add_argument("--count", type=int, default=100)
         parser.add_argument("--photos", type=int, default=4)
         parser.add_argument("--dealers", type=int, default=5)
         parser.add_argument("--min-price", type=int, default=900)
         parser.add_argument("--max-price", type=int, default=4500)
         parser.add_argument("--reset", action="store_true")
         parser.add_argument("--page", type=int, default=1)
         parser.add_argument("--limit", type=int, default=100)
-        parser.add_argument("--max-pages", type=int, default=5)
+        parser.add_argument("--max-pages", type=int, default=20)
         parser.add_argument("--vehicle-year", type=str, default="")
         parser.add_argument("--vehicle-make", type=str, default="")
         parser.add_argument("--vehicle-model", type=str, default="")
         parser.add_argument("--api-key", type=str, default="")
         parser.add_argument("--base-url", type=str, default="")
         parser.add_argument("--auth", type=str, default="header")
+        parser.add_argument("--allowed-models", type=str, default="")
+        parser.add_argument("--max-per-model", type=int, default=6)
         parser.add_argument("--debug", action="store_true")
@@
         target = options["count"]
         photos_needed = options["photos"]
         min_price = options["min_price"]
         max_price = options["max_price"]
@@
         created = 0
         used_vins = set()
+        model_counts = {}
         page_count = 0
+
+        allowed = self._parse_allowed_models(options["allowed_models"])
+        max_per_model = max(1, options["max_per_model"])
@@
                 brand = vehicle.get("make") or listing.get("make")
                 model = vehicle.get("model") or listing.get("model")
                 year = vehicle.get("year") or listing.get("year") or listing.get("model_year")
                 if not (brand and model and year):
                     continue
+
+                brand_norm = str(brand).strip()
+                model_norm = str(model).strip()
+                key = (brand_norm.lower(), model_norm.lower())
+                if allowed and key not in allowed:
+                    continue
+
+                count = model_counts.get(key, 0)
+                if count >= max_per_model:
+                    continue
@@
                 photos = self._fetch_photos(photos_url, api_key, vin)
                 if len(photos) < photos_needed:
                     continue
@@
-                Car.objects.create(
+                Car.objects.create(
                     dealer=dealer,
-                    brand=str(brand),
-                    model=str(model),
+                    brand=brand_norm,
+                    model=model_norm,
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
+                model_counts[key] = count + 1
@@
         self.stdout.write(self.style.SUCCESS(f"Imported {created} cars from Auto.dev."))
+
+    def _parse_allowed_models(self, raw):
+        if not raw:
+            return set()
+        allowed = set()
+        parts = [p.strip() for p in raw.split(",") if p.strip()]
+        for part in parts:
+            if ":" in part:
+                make, model = part.split(":", 1)
+                allowed.add((make.strip().lower(), model.strip().lower()))
+        return allowed
*** End Patch
