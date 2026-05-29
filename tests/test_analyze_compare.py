"""Analyze compare pipeline — specs/analyze_compare.md."""

import csv
import os
from types import SimpleNamespace

import pytest

from os_toolkit.analysis.compare import run_compare, settings_from_namespace

pytest.importorskip("numpy")
pytest.importorskip("pandas")
pytest.importorskip("tqdm")

pytestmark = pytest.mark.requires_ml


def _write_features(path, rows):
    keys = ["path", "depth", "size_bytes", "files", "folders", "name"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def _tiny_csv_pair(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    base = {
        "depth": 0,
        "size_bytes": 100,
        "files": 1,
        "folders": 0,
        "name": "root",
    }
    _write_features(old, [{"path": ".", **base}])
    _write_features(
        new,
        [
            {"path": ".", **base},
            {
                "path": "child",
                "depth": 1,
                "size_bytes": 10,
                "files": 1,
                "folders": 0,
                "name": "child",
            },
        ],
    )
    return str(old), str(new)


def test_compare_writes_matches(tmp_path, runs_root, capsys):
    """Guarantee: compare produces matches.json for valid CSV pair."""
    old, new = _tiny_csv_pair(tmp_path)
    args = SimpleNamespace(
        old=old,
        new=new,
        run_id="cmp_test",
        threshold=0.0,
        topk=2,
        batch_size=1000,
        structure_filter=0.0,
        name_sim="tfidf",
        tfidf_ngrams="3-5",
        tokenizer="char",
        depth_limit=10,
        workers=1,
        color=False,
    )
    settings = settings_from_namespace(args)
    run_compare(settings)
    run_path = runs_root / "cmp_test"
    matches_json = run_path / "matches.json"
    assert matches_json.is_file()
