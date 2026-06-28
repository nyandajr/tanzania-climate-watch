import csv
import os
import statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta

def load_csv(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))

def safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def main():
    now      = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).isoformat()

    metrics   = [r for r in load_csv("data/processed/climate_metrics.csv")  if r.get("timestamp","") >= week_ago]
    anomalies = [r for r in load_csv("data/anomalies/anomaly_log.csv")       if r.get("timestamp","") >= week_ago]
    model_perf= [r for r in load_csv("data/metrics/model_performance.csv")   if r.get("timestamp","") >= week_ago]

    # Per-city stats
    city_data = defaultdict(lambda: {"temps":[], "humidity":[], "name":""})
    for r in metrics:
        ck = r.get("city_key","")
        city_data[ck]["name"] = r.get("city", ck)
        t = safe_float(r.get("temperature"))
        h = safe_float(r.get("humidity"))
        if t: city_data[ck]["temps"].append(t)
        if h: city_data[ck]["humidity"].append(h)

    # Best MAE per city
    best_mae = {}
    for r in model_perf:
        ck  = r.get("city_key","")
        mae = safe_float(r.get("mae"))
        if mae and (ck not in best_mae or mae < best_mae[ck]):
            best_mae[ck] = mae

    date_str = now.strftime("%Y-%m-%d")
    cycles   = len(metrics) // 5 if metrics else 0

    lines = [
        f"# Weekly Climate Report — {date_str}",
        f"",
        f"Generated: {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"",
        f"## Summary",
        f"- Data points collected: {len(metrics)}",
        f"- Pipeline cycles completed: {cycles}",
        f"- Anomalies detected: {len(anomalies)}",
        f"",
        f"## City Statistics (Last 7 Days)",
        f"",
        f"| City | Avg Temp | Min Temp | Max Temp | Avg Humidity | Best MAE |",
        f"|------|----------|----------|----------|--------------|----------|",
    ]

    for ck, d in city_data.items():
        temps = d["temps"]
        if not temps:
            continue
        avg  = round(statistics.mean(temps), 1)
        mn   = round(min(temps), 1)
        mx   = round(max(temps), 1)
        hmid = round(statistics.mean(d["humidity"]), 1) if d["humidity"] else "N/A"
        mae  = f"{best_mae[ck]:.2f}°C" if ck in best_mae else "training..."
        lines.append(f"| {d['name']} | {avg}°C | {mn}°C | {mx}°C | {hmid}% | {mae} |")

    lines += ["", "## Anomalies", ""]

    if anomalies:
        lines += [
            "| Time | City | Field | Value | Type | Severity |",
            "|------|------|-------|-------|------|----------|",
        ]
        for a in anomalies[-20:]:
            ts   = a.get("timestamp","")[:16]
            city = a.get("city","")
            fld  = a.get("field","")
            val  = a.get("value","")
            typ  = a.get("type","")
            sev  = a.get("severity","").upper()
            lines.append(f"| {ts} | {city} | {fld} | {val} | {typ} | {sev} |")
    else:
        lines.append("_No anomalies detected this week._")

    os.makedirs("reports/weekly", exist_ok=True)
    path = f"reports/weekly/report_{date_str}.md"
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[weekly_report] Generated {path}")

if __name__ == "__main__":
    main()
