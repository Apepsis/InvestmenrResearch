"""Orchestrate the complete deterministic research build."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK_DIR = ROOT / "research_work"


def run(script: str) -> None:
    print(f"\n==> {script}", flush=True)
    subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT, check=True)


def main() -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    (WORK_DIR / "pipeline_started_at.txt").write_text(str(time.time()), encoding="utf-8")
    run("collect_market_data.py")
    run("validate_market_data.py")
    run("refresh_fast_signals.py")
    run("build_feature_store.py")
    run("run_walk_forward.py")
    run("calculate_portfolio_risk.py")
    run("run_event_study.py")
    run("generate_live_predictions.py")
    run("update_model_registry.py")
    run("monitor_model.py")
    run("send_alerts.py")
    run("validate_research_artifacts.py")
    run("generate_research_manifest.py")
    print("\nPipeline de investigación completado.")


if __name__ == "__main__":
    main()
