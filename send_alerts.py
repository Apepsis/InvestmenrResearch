"""Create deduplicated research alerts and optionally send a Gmail digest.

Credentials are read only from GitHub Actions secrets. The public artifact never
contains recipients, passwords or SMTP error messages.
"""

from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from v5_core import alert_fingerprint


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUTPUT_FILE = DATA / "alerts.json"


def parse_time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def build_candidates(
    live: dict[str, Any],
    monitoring: dict[str, Any],
    registry: dict[str, Any],
    neural: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for issue in monitoring.get("issues", []):
        if issue.get("severity") == "critical":
            candidates.append({
                "fingerprint": alert_fingerprint(str(issue["code"])),
                "code": str(issue["code"]),
                "severity": "critical",
                "ticker": None,
                "title": "Emergencia de integridad del pipeline",
                "message": str(issue["message"]),
                "cooldownHours": 24,
            })
    by_ticker: dict[str, dict[int, dict[str, Any]]] = {}
    for prediction in live.get("predictions", []):
        by_ticker.setdefault(str(prediction["ticker"]), {})[int(prediction["horizonSessions"])] = prediction
    for ticker, horizons in by_ticker.items():
        short, medium, long = horizons.get(5), horizons.get(20), horizons.get(60)
        neural_by_horizon = {
            int(item["horizonSessions"]): item
            for item in (neural or {}).get("currentPredictions", [])
            if item.get("ticker") == ticker
        } if (neural or {}).get("active", {}).get("role") == "champion" else {}
        neural_medium, neural_long = neural_by_horizon.get(20), neural_by_horizon.get(60)
        neural_agrees = not neural_by_horizon or (
            neural_medium and neural_long
            and float(neural_medium["probability"]) >= .60
            and float(neural_long["probability"]) >= .57
        )
        if medium and long and neural_agrees and float(medium["probability"]) >= .66 and float(long["probability"]) >= .60 and float(medium["uncertainty"]["low"]) >= .50:
            strength = (float(medium["probability"]) + float(long["probability"])) / 2
            agreement = " La red Champion también coincide." if neural_by_horizon else ""
            candidates.append({
                "fingerprint": alert_fingerprint("research_opportunity", ticker),
                "code": "research_opportunity",
                "severity": "opportunity",
                "ticker": ticker,
                "title": f"Oportunidad de investigación: {ticker}",
                "message": f"P(superar SPY): 20 sesiones {float(medium['probability']) * 100:.1f}% y 60 sesiones {float(long['probability']) * 100:.1f}%.{agreement} Revisar evidencia y riesgo antes de decidir.",
                "strength": round(strength, 6),
                "cooldownHours": 72,
            })
        if short and medium and float(short["probability"]) <= .25 and float(medium["probability"]) <= .35:
            candidates.append({
                "fingerprint": alert_fingerprint("downside_watch", ticker),
                "code": "downside_watch",
                "severity": "warning",
                "ticker": ticker,
                "title": f"Riesgo elevado para revisar: {ticker}",
                "message": f"P(superar SPY): 5 sesiones {float(short['probability']) * 100:.1f}% y 20 sesiones {float(medium['probability']) * 100:.1f}%. No es orden de venta.",
                "cooldownHours": 48,
            })
    if registry.get("champion", {}).get("key") == "riskControlled" and registry.get("history", [])[-1:].copy():
        candidates.append({
            "fingerprint": alert_fingerprint("model_promoted"),
            "code": "model_promoted",
            "severity": "info",
            "ticker": None,
            "title": "Nuevo champion promovido",
            "message": "El challenger con control de riesgo cumplió los criterios fuera de muestra durante tres ejecuciones diarias.",
            "cooldownHours": 720,
        })
    if (neural or {}).get("promotedThisRun"):
        candidates.append({
            "fingerprint": alert_fingerprint("neural_model_promoted"),
            "code": "neural_model_promoted",
            "severity": "info",
            "ticker": None,
            "title": "Nuevo Neural Champion promovido",
            "message": f"{(neural or {}).get('active', {}).get('version', 'La V8')} aprobó los gates temporales, de calibración y múltiples ensayos.",
            "cooldownHours": 720,
        })
    order = {"critical": 0, "warning": 1, "opportunity": 2, "info": 3}
    return sorted(candidates, key=lambda item: (order.get(str(item["severity"]), 9), -float(item.get("strength", 0))))[:8]


def pending_after_cooldown(candidates: list[dict[str, Any]], history: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    latest: dict[str, datetime] = {}
    for item in history:
        sent = parse_time(str(item.get("sentAt", "")))
        if sent:
            latest[str(item.get("fingerprint"))] = max(sent, latest.get(str(item.get("fingerprint")), sent))
    output = []
    for item in candidates:
        last = latest.get(str(item["fingerprint"]))
        if last is None or now - last >= timedelta(hours=int(item.get("cooldownHours", 24))):
            output.append(item)
    return output


def send_digest(sender: str, recipients: list[str], app_password: str, candidates: list[dict[str, Any]], generated_at: str) -> None:
    message = EmailMessage()
    message["Subject"] = f"Research Lab: {len(candidates)} alerta(s) para revisar"
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    lines = ["Investment Research Agent V8", f"Generado: {generated_at}", ""]
    for item in candidates:
        lines.extend([f"[{str(item['severity']).upper()}] {item['title']}", str(item["message"]), ""])
    lines.extend([
        "Estas alertas son señales para investigar, no órdenes de compra o venta.",
        "Comprueba fuentes, liquidez, costos y tu tolerancia al riesgo antes de actuar.",
    ])
    message.set_content("\n".join(lines))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(sender, app_password)
        smtp.send_message(message)


def main() -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    live = json.loads((DATA / "live_predictions.json").read_text(encoding="utf-8"))
    monitoring = json.loads((DATA / "model_monitoring.json").read_text(encoding="utf-8"))
    registry = json.loads((DATA / "model_registry.json").read_text(encoding="utf-8"))
    neural_path = DATA / "neural_lab.json"
    neural = json.loads(neural_path.read_text(encoding="utf-8")) if neural_path.exists() else None
    previous = json.loads(OUTPUT_FILE.read_text(encoding="utf-8")) if OUTPUT_FILE.exists() else {}
    history = list(previous.get("history", []))
    candidates = build_candidates(live, monitoring, registry, neural)
    pending = pending_after_cooldown(candidates, history, now)
    enabled = os.getenv("ALERTS_ENABLED", "").strip().lower() in {"1", "true", "yes", "si", "sí"}
    sender = os.getenv("ALERT_EMAIL_FROM", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip().replace(" ", "")
    recipients = [value.strip() for value in os.getenv("ALERT_EMAIL_TO", "").replace(";", ",").split(",") if value.strip()]
    delivery = "disabled"
    error_class: str | None = None
    sent_count = 0
    if enabled and (not sender or not password or not recipients):
        delivery = "misconfigured"
    elif enabled and not pending:
        delivery = "no-new-alerts"
    elif enabled:
        try:
            send_digest(sender, recipients, password, pending, now.isoformat())
            delivery = "sent"
            sent_count = len(pending)
            history.extend({
                "fingerprint": item["fingerprint"],
                "code": item["code"],
                "ticker": item.get("ticker"),
                "severity": item["severity"],
                "sentAt": now.isoformat(),
            } for item in pending)
        except Exception as exc:  # noqa: BLE001 - a provider failure must not corrupt research artifacts
            delivery = "failed"
            error_class = type(exc).__name__
    output = {
        "generatedAt": now.isoformat(),
        "mode": "live",
        "deliveryEnabled": enabled,
        "deliveryStatus": delivery,
        "deliveryErrorClass": error_class,
        "newAlertsSent": sent_count,
        "candidates": candidates,
        "pendingAfterCooldown": len(pending),
        "history": history[-500:],
        "policy": "Solo se envía un digest deduplicado; oportunidades requieren acuerdo entre 20 y 60 sesiones. No ejecuta operaciones.",
    }
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Alerts: {len(candidates)} candidatas; delivery={delivery}; sent={sent_count}.")


if __name__ == "__main__":
    main()
