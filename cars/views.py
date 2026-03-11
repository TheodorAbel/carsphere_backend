*** Begin Patch
*** Update File: C:\Users\ENVY 13\Documents\Dev\carsphere\cars\views.py
@@
         options = {
             "count": int(data.get("count", 100)),
             "photos": int(data.get("photos", 4)),
             "dealers": int(data.get("dealers", 5)),
             "min_price": int(data.get("min_price", 900)),
             "max_price": int(data.get("max_price", 4500)),
             "reset": bool(data.get("reset", True)),
             "page": int(data.get("page", 1)),
             "limit": int(data.get("limit", 100)),
             "max_pages": int(data.get("max_pages", 5)),
             "vehicle_year": data.get("vehicle_year", ""),
             "vehicle_make": data.get("vehicle_make", ""),
             "vehicle_model": data.get("vehicle_model", ""),
             "api_key": data.get("api_key", ""),
             "base_url": data.get("base_url", ""),
             "auth": data.get("auth", "apikey"),
+            "allowed_models": data.get("allowed_models", ""),
+            "max_per_model": int(data.get("max_per_model", 6)),
             "debug": bool(data.get("debug", False)),
         }
*** End Patch
