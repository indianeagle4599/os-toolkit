"""
test_matrix — multi-drive scenario enumeration.

Guarantee: benchmarks/matrix.py produces correct scenario counts and filters
for transfer (N²) and analysis (N within-drive only).
"""

from types import SimpleNamespace

import pytest

from benchmarks.matrix import (
    iter_analysis_scenarios,
    iter_transfer_scenarios,
    parse_drives,
)


@pytest.fixture(autouse=True)
def _matrix_storage_probes(monkeypatch):
    """Avoid real disk probes when sorting synthetic drive paths in tests."""
    import benchmarks.matrix as matrix_mod

    def _neutral_describe(p):
        return {
            "rotational": None,
            "physical_id": None,
            "mount": str(p),
            "platform": "test",
            "path": str(p),
        }

    monkeypatch.setattr(matrix_mod, "describe_path", _neutral_describe)
    monkeypatch.setattr(matrix_mod, "same_physical_device", lambda a, b: None)


def _drives(n):
    labels = "abcd"[:n]
    return {k: f"/{k}" for k in labels}


def test_transfer_scenario_counts():
    assert len(list(iter_transfer_scenarios(_drives(1), "all"))) == 1
    assert len(list(iter_transfer_scenarios(_drives(2), "all"))) == 4
    assert len(list(iter_transfer_scenarios(_drives(3), "all"))) == 9
    assert len(list(iter_transfer_scenarios(_drives(4), "all"))) == 16


def test_transfer_within_and_cross():
    assert len(list(iter_transfer_scenarios(_drives(2), "within"))) == 2
    assert len(list(iter_transfer_scenarios(_drives(2), "cross"))) == 2
    assert len(list(iter_transfer_scenarios(_drives(3), "within"))) == 3
    assert len(list(iter_transfer_scenarios(_drives(3), "cross"))) == 6


def test_transfer_custom_subset():
    scenarios = list(iter_transfer_scenarios(_drives(4), "a->c,b->d"))
    assert len(scenarios) == 2
    assert {s.id for s in scenarios} == {"a_to_c", "b_to_d"}


def test_analysis_within_drive_only():
    assert len(list(iter_analysis_scenarios(_drives(1), "all"))) == 1
    assert len(list(iter_analysis_scenarios(_drives(2), "all"))) == 2
    assert len(list(iter_analysis_scenarios(_drives(4), "all"))) == 4


def test_analysis_cross_raises():
    with pytest.raises(ValueError, match="cross-drive"):
        list(iter_analysis_scenarios(_drives(2), "cross"))


def test_parse_drives_skips_empty():
    args = SimpleNamespace(drive_a="/a", drive_b=None, drive_c="/c")
    parsed = parse_drives(args)
    assert list(parsed.keys()) == ["a", "c"]


def test_scenario_sort_ssd_before_hdd(monkeypatch):
    from pathlib import Path

    import benchmarks.matrix as matrix_mod

    def fake_describe(p):
        rotational = True if any(d in str(p) for d in ["E:", "F:"]) else False
        return {
            "rotational": rotational,
            "physical_id": None,
            "mount": p,
            "platform": "Windows",
            "path": p,
        }

    monkeypatch.setattr(matrix_mod, "describe_path", fake_describe)
    monkeypatch.setattr(matrix_mod, "same_physical_device", lambda a, b: False)
    drives = {
        "a": Path("C:/a"),
        "b": Path("D:/b"),
        "c": Path("E:/c"),
        "d": Path("F:/d"),
    }
    scenarios = list(iter_transfer_scenarios(drives, "all"))
    first = scenarios[0]
    assert fake_describe(str(first.src_path))["rotational"] is False
    assert fake_describe(str(first.dst_path))["rotational"] is False
    last = scenarios[-1]
    assert (
        fake_describe(str(last.src_path))["rotational"] is True
        or fake_describe(str(last.dst_path))["rotational"] is True
    )
