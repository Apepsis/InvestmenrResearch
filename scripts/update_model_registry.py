"""Govern champion/challenger promotion without silent model replacement."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5_core import promotion_qualified


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
BACKTEST_FILE = DATA / "backtest.json"
OUTPUT_FILE = DATA / "model_registry.json"


def main() -> None:
    backtest = json.loads(BACKTEST_FILE.read_text(encoding="utf-8"))
    previous: dict[str, Any] = json.loads(OUTPUT_FILE.read_text(encoding="utf-8")) if OUTPUT_FILE.exists() else {}
    statistical = backtest["metrics"]["statistical"]
    controlled = backtest["metrics"]["riskControlled"]
    qualified, checks = promotion_qualified(statistical, controlled)
    today = datetime.now(timezone.utc).date().isoformat()
    prior_streak = int(previous.get("qualificationStreak", 0))
    prior_date = str(previous.get("lastQualificationDate", ""))
    streak = prior_streak if prior_date == today else (prior_streak + 1 if qualified else 0)
    promoted = streak >= 3
    champion_key = "riskControlled" if promoted else "statistical"
    decision = (
        "Promovido después de tres ejecuciones diarias calificadas consecutivas."
        if promoted
        else "Permanece como challenger hasta cumplir todos los criterios en tres ejecuciones diarias consecutivas."
    )
    history = list(previous.get("history", []))
    if not history or history[-1].get("date") != today:
        history.append({"date": today, "qualified": qualified, "streak": streak, "champion": champion_key})
    output = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "mode": "live",
        "champion": {
            "key": champion_key,
            "version": "risk-controlled-v5.0" if promoted else "transparent-research-v4.0",
            "metrics": backtest["metrics"][champion_key],
        },
        "challenger": {
            "key": "riskControlled",
            "version": "risk-controlled-v5.0",
            "metrics": controlled,
            "rules": backtest.get("riskControls", {}),
        },
        "baseline": {"key": "statistical", "version": "transparent-research-v4.0", "metrics": statistical},
        "promotionCriteria": checks,
        "qualifiedThisRun": qualified,
        "qualificationStreak": streak,
        "requiredStreak": 3,
        "lastQualificationDate": today,
        "decision": decision,
        "history": history[-30:],
        "guardrail": "La promoción nunca reescribe predicciones ya publicadas y requiere evidencia fuera de muestra repetida.",
    }
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Registry: champion={champion_key}; challenger qualified={qualified}; streak={streak}/3.")


if __name__ == "__main__":
    main()
