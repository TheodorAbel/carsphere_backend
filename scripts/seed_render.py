import argparse
import json
import random
import sys
import time
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def request_json(method, url, data=None, token=None, timeout=60, retries=3, backoff=2.0):
    payload = None
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        payload = json.dumps(data).encode("utf-8")

    last_err = None
    for attempt in range(1, retries + 1):
        req = Request(url, data=payload, headers=headers, method=method)
        try:
            with urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
                if body:
                    return resp.status, json.loads(body)
                return resp.status, None
        except HTTPError as e:
            body = e.read().decode("utf-8")
            try:
                parsed = json.loads(body) if body else None
            except json.JSONDecodeError:
                parsed = body
            return e.code, parsed
        except (URLError, TimeoutError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(backoff * attempt)
                continue
            return 0, str(last_err)


def build_url(filename):
    return "https://commons.wikimedia.org/wiki/Special:FilePath/" + quote(filename, safe="")


def main():
    parser = argparse.ArgumentParser(description="Seed cars into Render API via HTTP.")
    parser.add_argument("--base-url", default="https://carsphere-backend.onrender.com/api/v1/")
    parser.add_argument("--per-location", type=int, default=10)
    parser.add_argument("--dealers", type=int, default=3)
    parser.add_argument("--password", default="dealer1234")
    parser.add_argument("--min-price", type=int, default=900)
    parser.add_argument("--max-price", type=int, default=4500)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--retries", type=int, default=4)
    args = parser.parse_args()

    base = args.base_url.rstrip("/") + "/"
    register_url = base + "auth/register/"
    login_url = base + "auth/login/"
    cars_url = base + "cars/"

    # Warm up Render cold start (ignore failures)
    try:
        request_json("GET", cars_url, timeout=args.timeout, retries=args.retries)
    except Exception:
        pass

    locations = [
        ("Bole", 9.0110, 38.7900),
        ("Piazza", 9.0379, 38.7590),
        ("Sar Bet", 9.0060, 38.7320),
        ("Megenagna", 9.0200, 38.8090),
        ("Mexico", 8.9980, 38.7370),
    ]

    # Real car image URLs per brand/model (Wikimedia Commons direct file paths)
    car_catalog = [
        ("Toyota", "Corolla", build_url("2019_Toyota_Corolla_Icon_Tech_VVT-i_Hybrid_1.8.jpg")),
        ("Toyota", "Yaris", build_url("2018_Toyota_Yaris_Icon_VVT-i_1.5.jpg")),
        ("Toyota", "Rav4", build_url("2019_Toyota_RAV4_2.5_Hybrid_Design_CVT.jpg")),
        ("Hyundai", "Elantra", build_url("2021_Hyundai_Elantra_SEL_(Canada),_front_8.28.21.jpg")),
        ("Hyundai", "Accent", build_url("2018_Hyundai_Accent_SE.jpg")),
        ("Hyundai", "Tucson", build_url("2022_Hyundai_Tucson_SE_AWD.jpg")),
        ("Kia", "Rio", build_url("2018_Kia_Rio_S.jpg")),
        ("Kia", "Sportage", build_url("Kia_Sportage_EX_2022_(52454009347).jpg")),
        ("Kia", "Sorento", build_url("2021_Kia_Sorento_SX.jpg")),
        ("Nissan", "Sunny", build_url("2019_Nissan_Sunny_SV.jpg")),
        ("Nissan", "X-Trail", build_url("2018_Nissan_X-Trail_Tekna_dCi_4x4.jpg")),
        ("Nissan", "Kicks", build_url("2018_Nissan_Kicks_SV_front_3.30.19.jpg")),
        ("Honda", "Civic", build_url("2017_Honda_Civic_SR_VTEC_1.0_Front.jpg")),
        ("Honda", "Fit", build_url("2018_Honda_Fit_EX.jpg")),
        ("Honda", "CR-V", build_url("2018_Honda_CR-V_EX.jpg")),
        ("Volkswagen", "Golf", build_url("2018_Volkswagen_Golf_SE_TSI_1.5.jpg")),
        ("Volkswagen", "Polo", build_url("2018_Volkswagen_Polo_SE_TSi_1.0_Front.jpg")),
        ("Volkswagen", "Tiguan", build_url("2017_Volkswagen_Tiguan_SE_TDI_BMT_4Motion_2.0.jpg")),
    ]

    fuel_choices = ["PETROL", "DIESEL", "ELECTRIC", "HYBRID"]
    transmission_choices = ["MANUAL", "AUTOMATIC"]

    random.seed(42)

    dealers = []
    for i in range(args.dealers):
        email = f"dealer{i+1}@carsphere.local"
        register_payload = {"email": email, "password": args.password, "role": "DEALER"}
        status, resp = request_json("POST", register_url, register_payload, timeout=args.timeout, retries=args.retries)
        if status in (200, 201):
            print(f"Registered dealer: {email}")
        else:
            # likely already exists
            print(f"Register status {status} for {email}: {resp}")

        status, login_resp = request_json("POST", login_url, {"email": email, "password": args.password}, timeout=args.timeout, retries=args.retries)
        if status != 200 or not isinstance(login_resp, dict) or "access" not in login_resp:
            print(f"Login failed for {email}: {status} {login_resp}")
            sys.exit(1)
        dealers.append({"email": email, "token": login_resp["access"]})

    if args.reset:
        for dealer in dealers:
            token = dealer["token"]
            status, mine = request_json("GET", cars_url + "?mine=1", token=token, timeout=args.timeout, retries=args.retries)
            if status != 200:
                print(f"Failed to fetch cars for {dealer['email']}: {status} {mine}")
                continue
            if isinstance(mine, list):
                for car in mine:
                    car_id = car.get("id")
                    if car_id is None:
                        continue
                    del_status, del_resp = request_json("DELETE", cars_url + f"{car_id}/", token=token, timeout=args.timeout, retries=args.retries)
                    if del_status not in (200, 204):
                        print(f"Delete failed for car {car_id}: {del_status} {del_resp}")
            print(f"Cleared cars for {dealer['email']}")

    total_needed = args.per_location * len(locations)
    used_keys = set()
    pool = []
    while len(pool) < total_needed:
        brand, model, image_url = random.choice(car_catalog)
        year = random.randint(2014, 2024)
        key = (brand, model, year)
        if key in used_keys:
            continue
        used_keys.add(key)
        pool.append((brand, model, image_url, year))

    created = 0
    idx = 0
    for loc_index, (name, base_lat, base_lng) in enumerate(locations):
        for i in range(args.per_location):
            dealer = dealers[(loc_index + i) % len(dealers)]
            brand, model, image_url, year = pool[idx]
            idx += 1
            price = Decimal(str(random.randint(args.min_price, args.max_price)))
            fuel = random.choice(fuel_choices)
            transmission = random.choice(transmission_choices)

            lat_offset = random.uniform(-0.003, 0.003)
            lng_offset = random.uniform(-0.003, 0.003)
            lat = round(base_lat + lat_offset, 6)
            lng = round(base_lng + lng_offset, 6)

            payload = {
                "brand": brand,
                "model": model,
                "year": year,
                "price_per_day": float(price),
                "fuel_type": fuel,
                "transmission": transmission,
                "latitude": float(lat),
                "longitude": float(lng),
                "image": image_url,
            }

            status, resp = request_json("POST", cars_url, payload, token=dealer["token"], timeout=args.timeout, retries=args.retries)
            if status in (200, 201):
                created += 1
            else:
                print(f"Create failed: {status} {resp}")

    print(f"Created {created} cars via API.")


if __name__ == "__main__":
    main()
