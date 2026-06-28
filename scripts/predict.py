import json
import os
import csv
import numpy as np
from datetime import datetime, timezone

try:
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_absolute_error
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False

CITIES = {
    "dar_es_salaam": "Dar es Salaam",
    "dodoma":         "Dodoma",
    "arusha":         "Arusha",
    "mwanza":         "Mwanza",
    "zanzibar":       "Zanzibar",
}

METRICS_FIELDNAMES = [
    "timestamp", "city", "city_key", "model_type",
    "mae", "data_points", "next_hour_prediction",
]

def load_history():
    path = "data/processed/climate_metrics.csv"
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))

def load_api_forecasts():
    path = "data/raw/latest.json"
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        raw = json.load(f)
    out = {}
    for city_key, payload in raw.items():
        daily = payload.get("daily", {})
        out[city_key] = {
            "dates":        daily.get("time", []),
            "temp_max":     daily.get("temperature_2m_max", []),
            "temp_min":     daily.get("temperature_2m_min", []),
            "precipitation":daily.get("precipitation_sum", []),
            "windspeed_max":daily.get("windspeed_10m_max", []),
        }
    return out

def safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def city_history(all_rows, city_key):
    rows = []
    for r in all_rows:
        if r.get("city_key") != city_key:
            continue
        t = safe_float(r.get("temperature"))
        if t is None:
            continue
        rows.append({
            "timestamp":   r["timestamp"],
            "temperature": t,
            "humidity":    safe_float(r.get("humidity")) or 60.0,
            "pressure":    safe_float(r.get("pressure")) or 1013.0,
            "windspeed":   safe_float(r.get("windspeed")) or 0.0,
        })
    return rows

def make_features(row):
    try:
        dt = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
    except Exception:
        dt = datetime.now(timezone.utc)
    h = dt.hour
    d = dt.timetuple().tm_yday
    return [
        np.sin(2 * np.pi * h / 24),
        np.cos(2 * np.pi * h / 24),
        np.sin(2 * np.pi * d / 365),
        np.cos(2 * np.pi * d / 365),
        row["temperature"],
        row["humidity"],
        row["pressure"],
        row["windspeed"],
    ]

def train_and_predict(history):
    n = len(history)
    if not SKLEARN_OK or n < 20:
        return None, None, n

    X, y = [], []
    for i in range(n - 1):
        feat = make_features(history[i])
        X.append(feat)
        y.append(history[i + 1]["temperature"])

    if len(X) < 10:
        return None, None, n

    X, y = np.array(X), np.array(y)
    split = max(8, int(len(X) * 0.8))

    scaler = StandardScaler()
    X_tr = scaler.fit_transform(X[:split])
    X_te = scaler.transform(X[split:]) if split < len(X) else X[:0]

    model = Ridge(alpha=1.0)
    model.fit(X_tr, y[:split])

    mae = float(mean_absolute_error(y[split:], model.predict(X_te))) if len(X_te) > 0 else None

    last_feat = scaler.transform([make_features(history[-1])])
    next_pred = float(model.predict(last_feat)[0])

    return mae, next_pred, n

def save_model_state(predictions):
    os.makedirs("ml", exist_ok=True)
    state = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "Ridge Regression (sklearn)",
        "features": ["hour_sin","hour_cos","day_sin","day_cos","temperature","humidity","pressure","windspeed"],
        "cities": [
            {
                "city": p["city"],
                "city_key": p["city_key"],
                "mae": p["mae"],
                "data_points": p["data_points"],
                "next_hour_prediction": p["next_hour_prediction"],
                "model_type": p["model_type"],
            }
            for p in predictions
        ],
    }
    with open("ml/inference_state.json", "w") as f:
        json.dump(state, f, indent=2)

def append_metrics(predictions):
    os.makedirs("data/metrics", exist_ok=True)
    path = "data/metrics/model_performance.csv"
    file_exists = os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=METRICS_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        for p in predictions:
            writer.writerow({
                "timestamp":            p["predicted_at"],
                "city":                 p["city"],
                "city_key":             p["city_key"],
                "model_type":           p["model_type"],
                "mae":                  p["mae"],
                "data_points":          p["data_points"],
                "next_hour_prediction": p["next_hour_prediction"],
            })

def main():
    os.makedirs("data/predictions", exist_ok=True)
    all_rows  = load_history()
    forecasts = load_api_forecasts()

    predictions = []
    for city_key, city_name in CITIES.items():
        history = city_history(all_rows, city_key)
        mae, next_pred, n = train_and_predict(history)

        model_type = "ridge_regression" if mae is not None else \
                     ("api_fallback" if n < 20 else "training")

        pred = {
            "city_key":             city_key,
            "city":                 city_name,
            "predicted_at":         datetime.now(timezone.utc).isoformat(),
            "model_type":           model_type,
            "mae":                  mae,
            "data_points":          n,
            "next_hour_prediction": next_pred,
            "forecast_7day":        forecasts.get(city_key, {}),
        }
        predictions.append(pred)

        mae_str = f"MAE={mae:.2f}°C" if mae else f"need more data ({n}/20)"
        print(f"[predict] {city_name}: next={next_pred}  {mae_str}")

    with open("data/predictions/latest.json", "w") as f:
        json.dump(predictions, f, indent=2)

    append_metrics(predictions)
    save_model_state(predictions)

if __name__ == "__main__":
    main()
