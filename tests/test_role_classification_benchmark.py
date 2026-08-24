from __future__ import annotations

import importlib.util
from pathlib import Path


def test_labeled_role_classification_corpus_has_no_regressions():
    path = Path(__file__).resolve().parents[1] / "scripts" / "role_classification_benchmark.py"
    spec = importlib.util.spec_from_file_location("role_classification_benchmark", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    result = module.evaluate()
    assert result["rows"] >= 30
    assert result["precision"] >= 0.95
    assert result["recall"] >= 0.95
    assert result["mismatches"] == []
