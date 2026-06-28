import requests
import json
import os
from datetime import datetime, timezone

CITIES = {
    "dar_es_salaam": {"name": "Dar es Salaam", "lat": -6.7924, "lon": 39.2083},
    "dodoma":         {"name": "Dodoma",         "lat": -6.1722, "lon": 35.7395},
    "arusha":         {"name": "Arusha",          "lat": -3.3869, "lon": 36.6830},
    "mwanza":         {"name": "Mwanza",          "lat": -2.5164, "lon": 32.9175},
    "zanzibar":       {"name": "Zanzibar",        "lat": -6.1659, "lon": 39.2026},
}

def fetch_city(city_key, info):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": info["lat"],
        "longitude": info["lon"],
        "hourly": "temperature_2m,relativehumidity_2m,precipitation,pressure_msl,windspeed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
        "current_weather": True,
        "timezone": "Africa/Dar_es_Salaam",
        "forecast_days": 7,
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    payload = r.json()
    payload["meta"] = {
        "city": info["name"],
        "city_key": city_key,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    return payload

def main():
    os.makedirs("data/raw", exist_ok=True)
    results = {}
    for key, info in CITIES.items():
        try:
            results[key] = fetch_city(key, info)
            print(f"[fetch] {info['name']} OK")
        except Exception as e:
            print(f"[fetch] {info['name']} FAILED: {e}")

    with open("data/raw/latest.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"[fetch] Saved {len(results)} cities to data/raw/latest.json")

if __name__ == "__main__":
    main()
