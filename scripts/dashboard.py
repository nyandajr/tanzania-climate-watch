import json
import os
import csv
from datetime import datetime, timezone, timedelta
from collections import defaultdict

CITY_COLORS = ["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF"]


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def load_csv_tail(path, n=2000):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows[-n:]


def safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def build_history_chart(history):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    by_city = defaultdict(lambda: {"labels": [], "data": []})

    for row in history:
        if row.get("timestamp", "") < cutoff:
            continue
        t = safe_float(row.get("temperature"))
        if t is None:
            continue
        ck = row.get("city_key", "")
        by_city[ck]["labels"].append(row["timestamp"][:16])
        by_city[ck]["data"].append(t)
        by_city[ck]["city"] = row.get("city", ck)

    datasets = []
    for i, (ck, d) in enumerate(by_city.items()):
        n = len(d["data"])
        if n > 200:
            step = max(1, n // 200)
            d["labels"] = d["labels"][::step][:200]
            d["data"]   = d["data"][::step][:200]
        datasets.append({
            "label":           d.get("city", ck),
            "data":            d["data"],
            "labels":          d["labels"],
            "borderColor":     CITY_COLORS[i % len(CITY_COLORS)],
            "backgroundColor": "transparent",
            "tension":         0.3,
            "pointRadius":     1,
        })

    all_labels = sorted({l for d in datasets for l in d["labels"]})[:200]
    return {"labels": all_labels, "datasets": datasets}


def build_mae_chart(model_metrics):
    by_city = defaultdict(lambda: {"labels": [], "data": []})
    for row in model_metrics:
        mae = safe_float(row.get("mae"))
        if mae is None:
            continue
        ck = row.get("city_key", "")
        by_city[ck]["labels"].append(row.get("timestamp", "")[:16])
        by_city[ck]["data"].append(round(mae, 3))
        by_city[ck]["city"] = row.get("city", ck)

    datasets = []
    labels   = []
    for i, (ck, d) in enumerate(by_city.items()):
        datasets.append({
            "label":       d.get("city", ck),
            "data":        d["data"],
            "borderColor": CITY_COLORS[i % len(CITY_COLORS)],
            "tension":     0.3,
        })
        if not labels:
            labels = d["labels"]

    return {"labels": labels, "datasets": datasets}


def build_forecast_chart(predictions):
    labels   = []
    datasets = []
    for i, pred in enumerate(predictions or []):
        fc    = pred.get("forecast_7day", {})
        dates = fc.get("dates", [])[:7]
        tmax  = fc.get("temp_max", [])[:7]
        tmin  = fc.get("temp_min", [])[:7]
        if not labels and dates:
            labels = dates
        color = CITY_COLORS[i % len(CITY_COLORS)]
        datasets.append({
            "label":           f"{pred.get('city','')} Max",
            "data":            tmax,
            "borderColor":     color,
            "backgroundColor": color + "22",
            "fill":            False,
            "tension":         0.4,
        })
        datasets.append({
            "label":           f"{pred.get('city','')} Min",
            "data":            tmin,
            "borderColor":     color,
            "backgroundColor": "transparent",
            "borderDash":      [5, 5],
            "fill":            False,
            "tension":         0.4,
        })
    return {"labels": labels, "datasets": datasets}


def build_current_cards(current_data):
    WEATHER_ICONS = {
        0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
        45: "🌫️", 48: "🌫️",
        51: "🌦️", 53: "🌦️", 55: "🌧️",
        61: "🌧️", 63: "🌧️", 65: "🌧️",
        80: "🌦️", 81: "🌧️", 82: "⛈️",
        95: "⛈️", 96: "⛈️", 99: "⛈️",
    }
    WEATHER_DESC = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Icy fog",
        51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
        61: "Light rain", 63: "Moderate rain", 65: "Heavy rain",
        80: "Light showers", 81: "Showers", 82: "Violent showers",
        95: "Thunderstorm", 96: "Thunderstorm + hail", 99: "Heavy thunderstorm",
    }
    cards = []
    for item in (current_data or []):
        code = int(safe_float(item.get("weathercode") or 0) or 0)
        cards.append({
            "city":        item.get("city", ""),
            "temperature": item.get("temperature"),
            "humidity":    item.get("humidity"),
            "windspeed":   item.get("windspeed"),
            "pressure":    item.get("pressure"),
            "icon":        WEATHER_ICONS.get(code, "🌡️"),
            "description": WEATHER_DESC.get(code, "Unknown"),
        })
    return cards


def update_status(predictions):
    total_pts = sum(p.get("data_points", 0) for p in (predictions or []))
    status = {
        "status":        "running",
        "last_run":      datetime.now(timezone.utc).isoformat(),
        "pipeline_version": "1.0.0",
        "total_data_points": total_pts,
        "cities": ["dar_es_salaam", "dodoma", "arusha", "mwanza", "zanzibar"],
    }
    with open("status.json", "w") as f:
        json.dump(status, f, indent=2)


def main():
    os.makedirs("docs", exist_ok=True)

    current_data  = load_json("data/processed/latest.json", [])
    predictions   = load_json("data/predictions/latest.json", [])
    anomalies_raw = load_csv_tail("data/anomalies/anomaly_log.csv", 50)
    history       = load_csv_tail("data/processed/climate_metrics.csv", 3000)
    model_metrics = load_csv_tail("data/metrics/model_performance.csv", 500)

    data = {
        "updated_at":    datetime.now(timezone.utc).isoformat(),
        "cards":         build_current_cards(current_data),
        "forecast":      build_forecast_chart(predictions),
        "history":       build_history_chart(history),
        "mae":           build_mae_chart(model_metrics),
        "anomalies":     anomalies_raw[-10:][::-1],
        "model_summary": [
            {
                "city":       p.get("city"),
                "model_type": p.get("model_type"),
                "mae":        p.get("mae"),
                "data_points":p.get("data_points"),
                "next_pred":  p.get("next_hour_prediction"),
            }
            for p in (predictions or [])
        ],
    }

    with open("docs/data.json", "w") as f:
        json.dump(data, f)

    update_status(predictions)
    print("[dashboard] docs/data.json updated.")

if __name__ == "__main__":
    main()
