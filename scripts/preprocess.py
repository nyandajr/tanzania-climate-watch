import json
import os
import csv
from datetime import datetime, timezone

FIELDNAMES = [
    "timestamp", "city", "city_key",
    "temperature", "windspeed", "winddirection", "weathercode", "is_day",
    "humidity", "precipitation", "pressure",
]

def load_latest():
    with open("data/raw/latest.json") as f:
        return json.load(f)

def get_hourly_index(times):
    now_prefix = datetime.now().strftime("%Y-%m-%dT%H:")
    for i, t in enumerate(times):
        if t.startswith(now_prefix):
            return i
    return 0

def extract_row(city_key, payload):
    cw = payload.get("current_weather", {})
    meta = payload.get("meta", {})
    hourly = payload.get("hourly", {})

    idx = get_hourly_index(hourly.get("time", []))

    def safe(lst, i):
        return lst[i] if lst and i < len(lst) else None

    return {
        "timestamp":    meta.get("fetched_at", datetime.now(timezone.utc).isoformat()),
        "city":         meta.get("city", city_key),
        "city_key":     city_key,
        "temperature":  cw.get("temperature"),
        "windspeed":    cw.get("windspeed"),
        "winddirection":cw.get("winddirection"),
        "weathercode":  cw.get("weathercode"),
        "is_day":       cw.get("is_day"),
        "humidity":     safe(hourly.get("relativehumidity_2m"), idx),
        "precipitation":safe(hourly.get("precipitation"), idx),
        "pressure":     safe(hourly.get("pressure_msl"), idx),
    }

def append_to_csv(path, rows):
    file_exists = os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

def main():
    os.makedirs("data/processed", exist_ok=True)
    data = load_latest()

    rows = []
    for city_key, payload in data.items():
        row = extract_row(city_key, payload)
        rows.append(row)
        print(f"[preprocess] {row['city']}: {row['temperature']}°C  "
              f"humidity={row['humidity']}%  pressure={row['pressure']}hPa")

    append_to_csv("data/processed/climate_metrics.csv", rows)

    with open("data/processed/latest.json", "w") as f:
        json.dump(rows, f, indent=2)

    print(f"[preprocess] Appended {len(rows)} rows to climate_metrics.csv")

if __name__ == "__main__":
    main()
