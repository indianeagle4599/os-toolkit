"""Shared pytest fixtures for os-toolkit."""

import pytest

from os_toolkit.analysis import runs as runs_module


@pytest.fixture
def runs_root(tmp_path, monkeypatch):
    """Hermetic runs/ — specs/analyze_profile.md, analyze_compare.md."""
    root = tmp_path / "runs"
    root.mkdir()
    monkeypatch.setattr(runs_module, "RUNS_ROOT", root)
    return root


@pytest.fixture
def usage_tree(tmp_path):
    """Small tree for usage specs — specs/usage.md."""
    root = tmp_path / "data"
    (root / "big").mkdir(parents=True)
    (root / "small").mkdir()
    (root / "big" / "file.bin").write_bytes(b"x" * 10_000)
    (root / "small" / "tiny.txt").write_bytes(b"hi")
    return root
