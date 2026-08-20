"""Evaluate transparent news baselines and optionally FinBERT on human labels."""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np

from collect_market_data import classify_news
from research_core import fit_logistic


ROOT = Path(__file__).resolve().parents[1]
LABEL_FILE = ROOT / "data" / "news_labels.csv"
OUTPUT_FILE = ROOT / "public" / "data" / "news_model_evaluation.json"
CLASSES = ["negative", "neutral", "positive"]


def tokens(value: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2]


def vocabulary(titles: list[str], limit: int = 600) -> list[str]:
    counts = Counter(token for title in titles for token in set(tokens(title)))
    return [token for token, _ in counts.most_common(limit)]


def matrix(titles: list[str], terms: list[str], inverse: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    lookup = {term: index for index, term in enumerate(terms)}
    document_frequency = np.zeros(len(terms))
    rows = np.zeros((len(titles), len(terms)))
    for row, title in enumerate(titles):
        counts = Counter(tokens(title))
        for token, count in counts.items():
            if token in lookup:
                rows[row, lookup[token]] = 1 + math.log(count)
        document_frequency += rows[row] > 0
    fitted_inverse = inverse if inverse is not None else np.log((1 + len(titles)) / (1 + document_frequency)) + 1
    return rows * fitted_inverse, fitted_inverse


def metrics(actual: list[str], predicted: list[str]) -> dict[str, object]:
    confusion = {left: {right: 0 for right in CLASSES} for left in CLASSES}
    for truth, guess in zip(actual, predicted):
        confusion[truth][guess] += 1
    per_class = {}
    for label in CLASSES:
        true_positive = confusion[label][label]
        false_positive = sum(confusion[other][label] for other in CLASSES if other != label)
        false_negative = sum(confusion[label][other] for other in CLASSES if other != label)
        precision = true_positive / max(true_positive + false_positive, 1)
        recall = true_positive / max(true_positive + false_negative, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-12)
        per_class[label] = {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}
    return {
        "accuracy": round(sum(left == right for left, right in zip(actual, predicted)) / max(len(actual), 1), 4),
        "macroPrecision": round(float(np.mean([value["precision"] for value in per_class.values()])), 4),
        "macroRecall": round(float(np.mean([value["recall"] for value in per_class.values()])), 4),
        "macroF1": round(float(np.mean([value["f1"] for value in per_class.values()])), 4),
        "perClass": per_class,
        "confusionMatrix": confusion,
    }


def main() -> None:
    with LABEL_FILE.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("title") and row.get("label") in CLASSES]
    if len(rows) < 40:
        raise RuntimeError("Se requieren al menos 40 titulares etiquetados; se recomiendan 200–500")
    # Deterministic holdout: every fourth row.  The file order is retained and published.
    train = [row for index, row in enumerate(rows) if index % 4]
    test = [row for index, row in enumerate(rows) if not index % 4]
    terms = vocabulary([row["title"] for row in train])
    train_x, inverse = matrix([row["title"] for row in train], terms)
    test_x, _ = matrix([row["title"] for row in test], terms, inverse)
    models = {label: fit_logistic(train_x, np.asarray([row["label"] == label for row in train], dtype=float), iterations=700) for label in CLASSES}
    probabilities = np.column_stack([models[label].predict_proba(test_x) for label in CLASSES])
    logistic_predictions = [CLASSES[index] for index in probabilities.argmax(axis=1)]
    lexicon_predictions = [classify_news(row["title"])[0] for row in test]
    result = {
        "generatedAt": np.datetime_as_string(np.datetime64("now"), unit="s") + "Z",
        "dataset": {"rows": len(rows), "train": len(train), "test": len(test), "classes": dict(Counter(row["label"] for row in rows))},
        "lexicon": metrics([row["label"] for row in test], lexicon_predictions),
        "tfidfLogistic": metrics([row["label"] for row in test], logistic_predictions),
        "finbert": {"status": "not_evaluated", "reason": "Instala transformers y documenta versión, pesos y entorno antes de comparar."},
        "warning": "El holdout no reemplaza una validación temporal o por fuente cuando el dataset crezca.",
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"NLP evaluation: {len(train)} train, {len(test)} test.")


if __name__ == "__main__":
    main()
