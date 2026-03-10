import argparse
import json
import sys
import time
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
    parser = argparse.ArgumentParser(description="Fix car image URLs on Render via API.")
    parser.add_argument("--base-url", default="https://carsphere-backend.onrender.com/api/v1/")
    parser.add_argument("--dealers", type=int, default=3)
    parser.add_argument("--password", default="dealer1234")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--retries", type=int, default=4)
    args = parser.parse_args()

    base = args.base_url.rstrip("/") + "/"
    login_url = base + "auth/login/"
    cars_url = base + "cars/"

    car_catalog = {
        ("Toyota", "Corolla"): build_url("2019_Toyota_Corolla_Icon_Tech_VVT-i_Hybrid_1.8.jpg"),
        ("Hyundai", "Elantra"): build_url("2021_Hyundai_Elantra_SEL_(Canada),_front_8.28.21.jpg"),
        ("Kia", "Sportage"): build_url("Kia_Sportage_EX_2022_(52454009347).jpg"),
        ("Nissan", "Kicks"): build_url("2018_Nissan_Kicks_SV_front_3.30.19.jpg"),
        ("Honda", "Civic"): build_url("2017_Honda_Civic_SR_VTEC_1.0_Front.jpg"),
        ("Volkswagen", "Polo"): build_url("2018_Volkswagen_Polo_SE_TSi_1.0_Front.jpg"),
        ("Toyota", "Yaris"): build_url("2018_Toyota_Yaris_Icon_VVT-i_1.5.jpg"),
        ("Toyota", "Rav4"): build_url("2019_Toyota_RAV4_2.5_Hybrid_Design_CVT.jpg"),
        ("Hyundai", "Accent"): build_url("2018_Hyundai_Accent_SE.jpg"),
        ("Hyundai", "Tucson"): build_url("2022_Hyundai_Tucson_SE_AWD.jpg"),
        ("Kia", "Rio"): build_url("2018_Kia_Rio_S.jpg"),
        ("Kia", "Sorento"): build_url("2021_Kia_Sorento_SX.jpg"),
        ("Nissan", "Sunny"): build_url("2019_Nissan_Sunny_SV.jpg"),
        ("Nissan", "X-Trail"): build_url("2018_Nissan_X-Trail_Tekna_dCi_4x4.jpg"),
        ("Honda", "Fit"): build_url("2018_Honda_Fit_EX.jpg"),
        ("Honda", "CR-V"): build_url("2018_Honda_CR-V_EX.jpg"),
        ("Volkswagen", "Golf"): build_url("2018_Volkswagen_Golf_SE_TSI_1.5.jpg"),
        ("Volkswagen", "Tiguan"): build_url("2017_Volkswagen_Tiguan_SE_TDI_BMT_4Motion_2.0.jpg"),
    }

    total_updated = 0
    for i in range(args.dealers):
        email = f"dealer{i+1}@carsphere.local"
        status, login_resp = request_json(
            "POST",
            login_url,
            {"email": email, "password": args.password},
            timeout=args.timeout,
            retries=args.retries,
        )
        if status != 200 or not isinstance(login_resp, dict) or "access" not in login_resp:
            print(f"Login failed for {email}: {status} {login_resp}")
            sys.exit(1)

        token = login_resp["access"]
        status, mine = request_json(
            "GET",
            cars_url + "?mine=1",
            token=token,
            timeout=args.timeout,
            retries=args.retries,
        )
        if status != 200:
            print(f"Failed to fetch cars for {email}: {status} {mine}")
            continue

        if not isinstance(mine, list):
            print(f"Unexpected response for {email}: {mine}")
            continue

        for car in mine:
            brand = car.get("brand")
            model = car.get("model")
            car_id = car.get("id")
            new_url = car_catalog.get((brand, model))
            if not new_url or not car_id:
                continue

            if car.get("image") == new_url:
                continue

            patch_status, patch_resp = request_json(
                "PATCH",
                cars_url + f"{car_id}/",
                {"image": new_url},
                token=token,
                timeout=args.timeout,
                retries=args.retries,
            )
            if patch_status in (200, 204):
                total_updated += 1
            else:
                print(f"Update failed for car {car_id}: {patch_status} {patch_resp}")

        print(f"Updated images for {email}")

    print(f"Total images updated: {total_updated}")


if __name__ == "__main__":
    main()
