"""Create a content-addressed manifest for every published research run."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA = ROOT / "public" / "data"
OUTPUT_FILE = PUBLIC_DATA / "research_manifest.json"
START_FILE = ROOT / "research_work" / "pipeline_started_at.txt"
TEST_FILE = ROOT / "research_work" / "test_summary.json"
ARTIFACT_NAMES = ["market.json", "backtest.json", "risk_model.json", "event_studies.json", "build_journal.json"]
MODEL_VERSION = "transparent-research-v4.0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    from_environment = os.getenv("GITHUB_SHA", "").strip()
    if from_environment:
        return from_environment[:12]
    try:
        return subprocess.check_output(["git", "rev-parse", "--short=12", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "no-disponible"


def main() -> None:
    artifacts = []
    for name in ARTIFACT_NAMES:
        path = PUBLIC_DATA / name
        if path.exists():
            artifacts.append({"name": name, "sha256": sha256(path), "bytes": path.stat().st_size})
    combined = hashlib.sha256("".join(item["sha256"] for item in artifacts).encode("utf-8")).hexdigest()
    market_path = PUBLIC_DATA / "market.json"
    market = json.loads(market_path.read_text(encoding="utf-8")) if market_path.exists() else {"stocks": {}, "errors": {}}
    expected_path = ROOT / "data" / "tickers.json"
    expected = len(json.loads(expected_path.read_text(encoding="utf-8")))
    stocks = market.get("stocks", {})
    macro = market.get("macro", {})
    fundamental_signals = sum(len(stock.get("fundamental", [])) for stock in stocks.values())
    expected_fundamental = max(len(stocks) * 4, 1)
    macro_available = sum(item.get("value") is not None for item in macro.values())
    macro_expected = max(len(macro), 1)
    asset_coverage = len(stocks) / max(expected, 1)
    evidence_coverage = min(fundamental_signals / expected_fundamental, 1)
    macro_coverage = macro_available / macro_expected
    coverage = max(0.0, min(1.0, .55 * asset_coverage + .30 * evidence_coverage + .15 * macro_coverage))
    tests = json.loads(TEST_FILE.read_text(encoding="utf-8")) if TEST_FILE.exists() else {}
    started = float(START_FILE.read_text(encoding="utf-8")) if START_FILE.exists() else time.time()
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%dT%H%M%SZ") + "-" + combined[:8]
    output = {
        "generatedAt": now.replace(microsecond=0).isoformat(),
        "mode": "live",
        "runId": run_id,
        "modelVersion": MODEL_VERSION,
        "gitCommit": git_commit(),
        "dataHash": f"sha256:{combined}",
        "horizon": "60 sesiones",
        "assetsProcessed": len(stocks),
        "assetsExpected": expected,
        "newsClassified": sum(len(stock.get("news", [])) for stock in stocks.values()),
        "nonCriticalErrors": len(market.get("errors", {})),
        "testsPassed": int(tests.get("passed", 0)),
        "dataCoverage": round(coverage * 100, 2),
        "durationSeconds": round(max(0, time.time() - started), 2),
        "artifacts": artifacts,
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Manifest {run_id}: cobertura {coverage * 100:.1f}%.")


if __name__ == "__main__":
    main()
