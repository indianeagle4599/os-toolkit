"""
test_devices — physical device tagging for benchmark matrix.

Guarantee: benchmarks/devices.py exposes physical_id and same_physical_device
for honest multi-drive result tagging (benchmarks/README.md).
"""

from pathlib import Path

from benchmarks.devices import describe_path, physical_id, same_physical_device


def test_physical_id_same_tmp_paths(tmp_path):
    """Two paths under tmp_path share one physical device on a single volume."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    pid_a = physical_id(a)
    pid_b = physical_id(b)
    assert pid_a is not None
    assert pid_a == pid_b
    assert same_physical_device(a, b) is True


def test_describe_path_includes_physical_id(tmp_path):
    row = describe_path(str(tmp_path))
    assert "physical_id" in row
    assert row["physical_id"] is not None
