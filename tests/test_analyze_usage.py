"""Analyze usage subcommand parity — specs/usage.md."""

import io
import sys

from os_toolkit.analysis.usage import run_usage


def _capture_run(path, **kwargs):
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        ok = run_usage(path, **kwargs)
    finally:
        sys.stdout = old
    return ok, buf.getvalue()


def test_usage_parity_with_disk_analyzer(usage_tree, capsys):
    """Guarantee: same inputs yield equivalent tree output from shared run_usage."""
    kwargs = dict(max_depth=3, threshold=0.0, verbosity=0, shallow_scan=False)
    ok1, out1 = _capture_run(str(usage_tree), **kwargs)
    ok2, out2 = _capture_run(str(usage_tree), **kwargs)
    assert ok1 == ok2 is True
    assert out1 == out2
    assert "Storage Analysis Results" in out1
