"""Usability: corpus sampler prints progress and avoids dumping file lists."""

import json
import sys
from pathlib import Path

import pytest

from benchmarks import corpus


def _seed_cache(cache: Path) -> None:
    for ds in ("alpha_ds", "beta_ds"):
        root = cache / f"{ds}_extracted" / "data"
        root.mkdir(parents=True)
        for i in range(3):
            (root / f"file_{i}.txt").write_bytes(b"x" * 200)


def test_corpus_sampler_emits_progress(tmp_path, monkeypatch, capsys):
    cache = tmp_path / "_cache"
    out_corpus = tmp_path / "corpus"
    manifest = tmp_path / "toolkit_manifest.json"
    _seed_cache(cache)

    monkeypatch.setattr(corpus, "CACHE_ROOT", cache)
    monkeypatch.setattr(corpus, "CORPUS_ROOT", out_corpus)
    monkeypatch.setattr(corpus, "MANIFEST_PATH", manifest)
    monkeypatch.setattr(corpus, "PROFILE_BUDGETS", {("small", "mixed"): 50_000})
    monkeypatch.setattr(
        sys,
        "argv",
        ["corpus", "--profile", "small/mixed"],
    )

    corpus.main()
    captured = capsys.readouterr()
    out = captured.out

    assert "alpha_ds" in out or "beta_ds" in out
    assert "Results:" in out
    assert out.count("\n") < 30

    start = out.rfind("{")
    assert start >= 0
    summary = json.loads(out[start:])
    assert summary["file_count"] == 6
    assert "files" not in summary or isinstance(summary.get("files"), list) is False

    prof = json.loads(manifest.read_text(encoding="utf-8"))["profiles"]["small/mixed"]
    assert len(prof["files"]) == 6


def test_corpus_sampler_quiet_suppresses_progress(tmp_path, monkeypatch, capsys):
    cache = tmp_path / "_cache"
    _seed_cache(cache)
    monkeypatch.setattr(corpus, "CACHE_ROOT", cache)
    monkeypatch.setattr(corpus, "CORPUS_ROOT", tmp_path / "corpus")
    monkeypatch.setattr(corpus, "MANIFEST_PATH", tmp_path / "manifest.json")
    monkeypatch.setattr(corpus, "PROFILE_BUDGETS", {("small", "mixed"): 50_000})
    monkeypatch.setattr(sys, "argv", ["corpus", "--profile", "small/mixed", "--quiet"])

    corpus.main()
    out = capsys.readouterr().out
    assert "Results:" not in out
