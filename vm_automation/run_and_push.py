"""VM-side replacement for the GitHub Actions "Climate Pipeline" workflow --
run from the VM's own crontab, not GitHub Actions. Same migration already
proven on hormuz-strait-monitor, ea-financial-tracker, dsn-anomaly-tracker,
and global-fuel-watch: GitHub Actions was measured delivering only ~21% of
this exact 15-min cadence in practice.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
DATA_PATHS = ["data/", "docs/data.json", "ml/", "status.json"]


def run(*args, check=True):
    return subprocess.run(list(args), cwd=str(REPO_DIR), check=check)


def sync_with_remote():
    # --hard, not --soft, and BEFORE the pipeline scripts run: reset --soft
    # only moves HEAD, leaving stale index entries for files this script
    # doesn't explicitly `git add`, which then get silently recommitted on
    # the next force-push. Learned this the hard way on hormuz-strait-monitor.
    run("git", "fetch", "origin", "main")
    run("git", "reset", "--hard", "origin/main")


def commit_summary():
    try:
        rows = json.load(open(REPO_DIR / "data/processed/latest.json"))
        parts = [f"{r['city'].split()[0]}: {r['temperature']}°C" for r in rows if r.get("temperature")]
        return " | ".join(parts[:3])
    except Exception:
        return "Tanzania weather update"


def git_commit_and_push():
    # freddynyanda@proton.me is Fred's real, verified GitHub email -- the
    # original workflow committed as "climate-bot <climate-bot@users.
    # noreply.github.com>", an unverified address, so every commit was real
    # but silently uncredited on his contribution graph.
    run("git", "config", "user.name", "nyandajr")
    run("git", "config", "user.email", "freddynyanda@proton.me")
    run("git", "add", *DATA_PATHS, check=False)

    diff = run("git", "diff", "--cached", "--quiet", check=False)
    if diff.returncode == 0:
        print("[run_and_push] no changes to commit")
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    summary = commit_summary()
    run("git", "commit", "-m", f"feat(pipeline): climate update {timestamp} — {summary}")
    run("git", "push", "--force", "origin", "HEAD:main")


def main():
    sync_with_remote()
    run(sys.executable, "scripts/fetch.py")
    run(sys.executable, "scripts/preprocess.py")
    run(sys.executable, "scripts/predict.py")
    run(sys.executable, "scripts/anomaly.py")
    run(sys.executable, "scripts/dashboard.py")
    git_commit_and_push()
    print("[run_and_push] done")


if __name__ == "__main__":
    main()
