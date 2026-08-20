from __future__ import annotations

import json
from pathlib import Path

import unittest

from validate_market_data import validate


def valid_payload() -> dict[str, object]:
    scores = {"technical": 60, "fundamental": 60, "news": 60, "macro": 60, "risk": 60}
    contributions = [
        {"feature": key, "group": key, "rawValue": "60", "normalized": 60, "weight": 20, "contribution": 2, "formula": "(60-50)*.2", "source": "test", "asOf": "2026-01-01", "status": "verified"}
        for key in scores
    ]
    return {
        "generatedAt": "2026-01-01T00:00:00Z",
        "mode": "live",
        "stocks": {
            "TEST": {
                "ticker": "TEST", "name": "Test", "price": 10, "score": 60, "scores": scores,
                "history": list(range(10)), "technical": [], "fundamental": [], "news": [], "trace": {},
                "explanation": {"base": 50, "result": 60, "interval": {"low": 50, "high": 70}, "contributions": contributions},
            }
        },
    }


class DataQualityTests(unittest.TestCase):
    def test_valid_market_payload_passes(self) -> None:
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            path = Path(directory) / "market.json"
            path.write_text(json.dumps(valid_payload()), encoding="utf-8")
            validate(path)


    def test_accidental_secret_is_rejected(self) -> None:
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            payload = valid_payload()
            payload["debug"] = "PRIVATE KEY"
            path = Path(directory) / "market.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                validate(path)
