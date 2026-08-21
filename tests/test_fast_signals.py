import unittest

from fast_signal_core import build_signal, fingerprint


def sample_item(impact: float = .3):
    return {
        "title": "Company reports material earnings update",
        "source": "Example",
        "url": "https://example.com/event",
        "publishedAt": "2026-08-21T15:00:00Z",
        "sentiment": "positive",
        "eventType": "resultados",
        "duration": "medium",
        "confidence": .72,
        "relevance": .81,
        "novelty": .9,
        "entityMatched": True,
        "impactWeight": impact,
    }


class FastSignalTests(unittest.TestCase):
    def test_fast_signal_preserves_first_seen_timestamp(self) -> None:
        item = sample_item()
        item_id = fingerprint(item)
        previous = {"items": [{"id": item_id, "firstSeenAt": "2026-08-21T14:00:00+00:00"}]}
        result = build_signal("TEST", [item], 61, previous, "2026-08-21T15:00:00+00:00")
        self.assertEqual(result["items"][0]["firstSeenAt"], "2026-08-21T14:00:00+00:00")


    def test_fast_signal_marks_material_event_as_high_urgency(self) -> None:
        result = build_signal("TEST", [sample_item()], 63, None, "2026-08-21T15:00:00+00:00")
        self.assertEqual(result["signal"], "positive")
        self.assertEqual(result["urgency"], "high")
        self.assertEqual(result["signalStrength"], 26)


if __name__ == "__main__":
    unittest.main()
