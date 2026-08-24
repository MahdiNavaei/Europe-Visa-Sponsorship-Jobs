from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from europe_visa_jobs.utils import classify_role

DEFAULT_CORPUS = Path(__file__).resolve().parents[1] / "data" / "role_classification_benchmark.json"


def evaluate(path: str | Path = DEFAULT_CORPUS) -> dict[str, Any]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    predictions = [classify_role(row["title"], row.get("department"), row.get("description")) for row in rows]
    technical_expected = [row["expected"] != "other" for row in rows]
    technical_predicted = [prediction.value != "other" for prediction in predictions]
    true_positive = sum(expected and predicted for expected, predicted in zip(technical_expected, technical_predicted, strict=True))
    false_positive = sum(not expected and predicted for expected, predicted in zip(technical_expected, technical_predicted, strict=True))
    false_negative = sum(expected and not predicted for expected, predicted in zip(technical_expected, technical_predicted, strict=True))
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    mismatches = [
        {"title": row["title"], "expected": row["expected"], "predicted": prediction.value}
        for row, prediction in zip(rows, predictions, strict=True)
        if prediction.value != row["expected"]
    ]
    return {
        "corpus": str(path),
        "rows": len(rows),
        "technical_rows": sum(technical_expected),
        "nontechnical_rows": len(rows) - sum(technical_expected),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "mismatches": mismatches,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the deterministic role classifier against its labeled corpus")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    args = parser.parse_args()
    print(json.dumps(evaluate(args.corpus), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
