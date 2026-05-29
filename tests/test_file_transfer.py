"""File transfer — specs/file_transfer.md guarantees."""

import os

from os_toolkit.transfer.copy import parallel_copy
from os_toolkit.transfer.strategies import apply_strategy, prescan_source
from os_toolkit.transfer.verify import destination_matches_size
from os_toolkit.transfer.worker import copy_worker


def _make_tree(root):
    root.mkdir(parents=True, exist_ok=True)
    (root / "a").mkdir()
    (root / "b").mkdir()
    (root / "a" / "one.txt").write_bytes(b"hello")
    (root / "b" / "two.txt").write_bytes(b"world!")


def test_destination_matches_size(tmp_path):
    """Guarantee: resume skips when dest size matches source."""
    f = tmp_path / "f.dat"
    f.write_bytes(b"12345")
    assert destination_matches_size(str(f), 5)
    assert not destination_matches_size(str(f), 4)


def test_dry_run_writes_nothing(tmp_path, capsys):
    """Guarantee: dry-run performs no file writes."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _make_tree(src)
    parallel_copy(str(src), str(dst), workers=1, verbosity=0, dry_run=True)
    assert not dst.exists() or list(dst.rglob("*")) == []


def test_copy_then_skip_on_rerun(tmp_path, capsys):
    """Guarantee: re-run skips files with matching dest size."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _make_tree(src)
    parallel_copy(str(src), str(dst), workers=1, verbosity=0, dry_run=False)
    assert (dst / "a" / "one.txt").read_bytes() == b"hello"
    parallel_copy(str(src), str(dst), workers=1, verbosity=0, dry_run=False)
    out = capsys.readouterr().out
    assert "Skipped" in out or "skipped" in out.lower()


def test_copy_worker_creates_file(tmp_path):
    src = tmp_path / "s.txt"
    dst = tmp_path / "d.txt"
    src.write_bytes(b"abc")
    status, size, err = copy_worker((str(src), str(dst), 3, False))
    assert status == "copied"
    assert dst.read_bytes() == b"abc"
    assert err is None


def test_smallest_first_strategy_order():
    files = [("/a", "a", 100), ("/b", "b", 10)]
    ordered = apply_strategy(files, "smallest-first")
    assert ordered[0][2] == 10


def test_prescan_finds_files(tmp_path):
    _make_tree(tmp_path)
    found = prescan_source(str(tmp_path))
    assert len(found) == 2


def test_rejects_dest_inside_source(tmp_path, capsys):
    """Adversarial: destination inside source must fail without copying."""
    src = tmp_path / "src"
    _make_tree(src)
    dst = src / "nested" / "dest"
    assert parallel_copy(str(src), str(dst), workers=1, verbosity=0) is False
    assert "inside source" in capsys.readouterr().out
