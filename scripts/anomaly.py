import json
import os
import csv
import statistics
from datetime import datetime, timezone

THRESHOLDS = {
    "temperature":  {"min": 8,   "max": 45},
    "humidity":     {"min": 5,   "max": 100},
    "pressure":     {"min": 985, "max": 1035},
    "windspeed":    {"min": 0,   "max": 65},
}

Z_THRESHOLD   = 2.5
ROLLING_WINDOW = 96   # 24 hours at 15-min intervals

FIELDNAMES = ["timestamp", "city", "city_key", "field", "value", "type", "detail", "severity"]

def load_history():
    path = "data/processed/climate_metrics.csv"
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))

def rolling_stats(history, city_key, field, window=ROLLING_WINDOW):
    values = []
    for r in history:
        if r.get("city_key") != city_key or not r.get(field):
            continue
        try:
            values.append(float(r[field]))
        except ValueError:
            pass
    recent = values[-window:]
    if len(recent) < 4:
        return None, None
    return statistics.mean(recent), statistics.stdev(recent)

def check(current_readings, history):
    anomalies = []
    ts = datetime.now(timezone.utc).isoformat()

    for r in current_readings:
        city_key = r.get("city_key")
        city     = r.get("city")

        for field in ("temperature", "humidity", "pressure", "windspeed"):
            raw = r.get(field)
            if raw is None:
                continue
            try:
                val = float(raw)
            except (TypeError, ValueError):
                continue

            lo = THRESHOLDS[field]["min"]
            hi = THRESHOLDS[field]["max"]
            if val < lo or val > hi:
                anomalies.append({
                    "timestamp": ts, "city": city, "city_key": city_key,
                    "field": field, "value": val, "type": "threshold_breach",
                    "detail": f"{field}={val} outside [{lo}, {hi}]",
                    "severity": "high",
                })
                continue

            mean, stdev = rolling_stats(history, city_key, field)
            if mean is not None and stdev and stdev > 0:
                z = abs(val - mean) / stdev
                if z > Z_THRESHOLD:
                    anomalies.append({
                        "timestamp": ts, "city": city, "city_key": city_key,
                        "field": field, "value": val, "type": "statistical_anomaly",
                        "detail": f"{field}={val} z={z:.2f} (μ={mean:.1f} σ={stdev:.1f})",
                        "severity": "high" if z > 3.5 else "medium",
                    })

    return anomalies

def append_anomalies(anomalies):
    os.makedirs("data/anomalies", exist_ok=True)
    path = "data/anomalies/anomaly_log.csv"
    file_exists = os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(anomalies)

def main():
    history = load_history()

    path = "data/processed/latest.json"
    if not os.path.exists(path):
        print("[anomaly] No current data — skipping.")
        return

    with open(path) as f:
        current = json.load(f)

    anomalies = check(current, history)
    append_anomalies(anomalies)

    os.makedirs("data/anomalies", exist_ok=True)
    with open("data/anomalies/latest.json", "w") as f:
        json.dump(anomalies, f, indent=2)

    if anomalies:
        for a in anomalies:
            print(f"[anomaly] {a['severity'].upper()} | {a['city']} | {a['detail']}")
    else:
        print("[anomaly] No anomalies detected.")

if __name__ == "__main__":
    main()
