*** Begin Patch
*** Update File: C:\Users\ENVY 13\Documents\Dev\carsphere\cars\views.py
@@
             "allowed_models": data.get("allowed_models", ""),
+            "allowed_makes": data.get("allowed_makes", ""),
             "max_per_model": int(data.get("max_per_model", 6)),
             "excluded_makes": data.get("excluded_makes", ""),
*** End Patch
