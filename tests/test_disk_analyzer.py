"""Disk analyzer CLI wrapper — specs/usage.md."""

from os_toolkit.analysis.usage import run_usage


def test_run_usage_success(usage_tree, capsys):
    """Guarantee: read-only scan returns success on valid tree."""
    ok = run_usage(
        str(usage_tree), max_depth=3, threshold=0.0, verbosity=0, shallow_scan=False
    )
    assert ok is True
    out = capsys.readouterr().out
    assert "Storage Analysis Results" in out
    assert "big" in out or "small" in out


def test_run_usage_missing_path_fails(tmp_path, capsys):
    """Adversarial: invalid path."""
    bad = tmp_path / "nope"
    ok = run_usage(
        str(bad), max_depth=2, threshold=1.0, verbosity=0, shallow_scan=False
    )
    assert ok is False
