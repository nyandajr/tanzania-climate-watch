# Tanzania Climate Prediction Pipeline

Real-time weather monitoring and ML forecasting for 5 Tanzanian cities, updated automatically every 15 minutes via GitHub Actions.

**[Live Dashboard →](https://nyandajr.github.io/tanzania-climate-watch)**

---

## Cities Covered

| City | Coordinates |
|------|-------------|
| Dar es Salaam | -6.79°, 39.21° |
| Dodoma | -6.17°, 35.74° |
| Arusha | -3.39°, 36.68° |
| Mwanza | -2.52°, 32.92° |
| Zanzibar | -6.17°, 39.20° |

## Pipeline Architecture

```
Open-Meteo API (free, no key)
        │
   fetch.py          → data/raw/latest.json
        │
   preprocess.py     → data/processed/climate_metrics.csv
        │
   predict.py        → data/predictions/latest.json
        │             ml/inference_state.json
   anomaly.py        → data/anomalies/anomaly_log.csv
        │
   dashboard.py      → docs/data.json  (GitHub Pages reads this)
        │
   GitHub Actions    → git commit + push (1 commit/run)
```

## ML Model

- **Algorithm**: Ridge Regression (scikit-learn)
- **Features**: cyclic hour/day encoding, temperature, humidity, pressure, windspeed
- **Target**: next-hour temperature
- **Metric**: MAE tracked over time per city
- **Cold start**: API forecast used until 20 data points collected

## Features

- Live current conditions for all 5 cities
- 7-day temperature max/min forecast charts
- 30-day historical temperature trends
- Model accuracy (MAE) over time chart
- Anomaly detection (z-score + hard thresholds)
- Weekly markdown reports (auto-generated every Monday)

## Data Source

[Open-Meteo](https://open-meteo.com/) — free, open-source weather API, no API key required.

## Local Development

```bash
pip install -r requirements.txt
python scripts/fetch.py
python scripts/preprocess.py
python scripts/predict.py
python scripts/anomaly.py
python scripts/dashboard.py
# open docs/index.html in browser (serve via local HTTP server)
python -m http.server 8080 --directory docs
```

## GitHub Pages Setup

1. Go to repo **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / folder: `/docs`
4. Save — your dashboard will be live at `https://nyandajr.github.io/tanzania-climate-watch`
