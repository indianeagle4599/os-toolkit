"""File transfer — specs/file_transfer.md guarantees."""

import os

import pytest

from os_toolkit.transfer.copy import parallel_copy
from os_toolkit.transfer.strategies import apply_strategy, prescan_source
from os_toolkit.transfer.verify import destination_matches_size
from os_toolkit.transfer.worker import copy_worker, reset_copy_caches


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
    parallel_copy(str(src), str(dst), workers=1, verbosity=1, dry_run=False)
    out = capsys.readouterr().out
    assert "skipped" in out.lower()


def test_copy_worker_creates_file(tmp_path):
    src = tmp_path / "s.txt"
    dst = tmp_path / "d.txt"
    src.write_bytes(b"abc")
    reset_copy_caches({})
    status, size, err = copy_worker((str(src), str(dst), "d.txt", 3, False))
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


def test_parallel_copy_hdd_dest_uses_walk_path(monkeypatch, tmp_path):
    """HDD/unknown dest routes to hdd_copy (no thread pool)."""
    from unittest.mock import patch

    from os_toolkit.core import storage

    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    (src / "one.txt").write_bytes(b"x")

    monkeypatch.setattr(
        storage,
        "rotational_for_path",
        lambda p: True if "dst" in str(p) else False,
    )

    def reject_pool(*_a, **_k):
        raise AssertionError("HDD path must not use ThreadPoolExecutor")

    with patch("os_toolkit.transfer.copy.ThreadPoolExecutor", side_effect=reject_pool):
        assert parallel_copy(str(src), str(dst), workers=8, verbosity=0, dry_run=True)


def test_effective_workers_ssd_to_ssd_no_clamp():
    from unittest.mock import patch

    from os_toolkit.core import storage
    from os_toolkit.core.storage import effective_workers

    with patch.object(
        storage,
        "describe_path",
        side_effect=[
            {
                "rotational": False,
                "physical_id": "disk:0",
                "mount": "C:",
                "platform": "Windows",
                "path": "C:\\",
            },
            {
                "rotational": False,
                "physical_id": "disk:1",
                "mount": "D:",
                "platform": "Windows",
                "path": "D:\\",
            },
        ],
    ):
        d = effective_workers(4, "C:\\", "D:\\", file_count=1000)
    assert d.effective <= 4
    assert d.reason == "" or "ssd" in d.reason.lower()


def test_ssd_dest_uses_thread_pool(monkeypatch, tmp_path):
    import shutil
    from concurrent.futures import ThreadPoolExecutor as RealPool
    from unittest.mock import patch

    from os_toolkit.core import storage

    pool_calls = []

    def track_pool(*args, **kwargs):
        pool_calls.append(kwargs.get("max_workers", args[0] if args else None))
        return RealPool(*args, **kwargs)

    monkeypatch.setattr(shutil, "copy2", lambda *_a, **_k: None)

    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _make_tree(src)

    monkeypatch.setattr(
        storage,
        "rotational_for_path",
        lambda _p: False,
    )
    with patch("os_toolkit.transfer.copy.ThreadPoolExecutor", side_effect=track_pool):
        parallel_copy(str(src), str(dst), workers=4, verbosity=0, dry_run=False)
    assert pool_calls == [4]


def test_hdd_path_used_when_slow_dest(monkeypatch, tmp_path):
    import shutil
    from unittest.mock import patch

    from os_toolkit.core import storage

    copy2_calls = []

    def track_copy2(src, dst):
        copy2_calls.append((src, dst))

    monkeypatch.setattr(shutil, "copy2", track_copy2)
    monkeypatch.setattr(
        storage,
        "rotational_for_path",
        lambda p: True if "dst" in str(p) else False,
    )

    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _make_tree(src)

    def reject_pool(*_a, **_k):
        raise AssertionError("HDD path must not use ThreadPoolExecutor")

    with patch("os_toolkit.transfer.copy.ThreadPoolExecutor", side_effect=reject_pool):
        parallel_copy(str(src), str(dst), workers=1, verbosity=0, dry_run=False)
    assert copy2_calls


def test_hdd_path_used_on_dry_run(monkeypatch, tmp_path):
    from unittest.mock import patch

    from os_toolkit.core import storage

    pool_calls = []

    class FakePool:
        def __init__(self, max_workers=None):
            pool_calls.append(max_workers)

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def submit(self, *_a, **_k):
            raise AssertionError("submit not expected")

    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _make_tree(src)

    monkeypatch.setattr(
        storage,
        "rotational_for_path",
        lambda p: True if "dst" in str(p) else False,
    )
    with patch("os_toolkit.transfer.copy.ThreadPoolExecutor", FakePool):
        parallel_copy(str(src), str(dst), workers=1, verbosity=0, dry_run=True)
    assert not pool_calls


@pytest.mark.skipif(os.name != "nt", reason="Windows only")
def test_robocopy_backend_invoked_when_env_set(monkeypatch, tmp_path):
    import subprocess

    from os_toolkit.core import storage
    from os_toolkit.transfer import copy as copy_mod

    monkeypatch.setenv("OS_TOOLKIT_ROBOCOPY", "1")
    monkeypatch.setattr(storage, "rotational_for_path", lambda _p: True)
    monkeypatch.setattr(
        copy_mod,
        "_source_file_count",
        lambda *a, **k: 60_001,
    )

    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    (src / "one.txt").write_bytes(b"x")

    run_calls = []

    def fake_run(cmd, **kw):
        run_calls.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="Files : 100 100 0 0 0 0\nBytes : 1 k 1 k 0 0 0 0\n",
            stderr="",
        )

    monkeypatch.setattr("os_toolkit.transfer.robocopy.robocopy_on_path", lambda: True)
    monkeypatch.setattr("os_toolkit.transfer.robocopy.subprocess.run", fake_run)

    parallel_copy(str(src), str(dst), workers=1, verbosity=0, dry_run=False)
    assert run_calls
    assert run_calls[0][0].lower() == "robocopy"


@pytest.mark.skipif(os.name != "nt", reason="Windows only")
def test_robocopy_fallback_to_fast_path_when_not_found(monkeypatch, tmp_path):
    import shutil
    from unittest.mock import patch

    from os_toolkit.core import storage
    from os_toolkit.transfer import copy as copy_mod

    monkeypatch.setenv("OS_TOOLKIT_ROBOCOPY", "1")
    monkeypatch.setattr(storage, "rotational_for_path", lambda _p: True)
    monkeypatch.setattr(
        copy_mod,
        "_source_file_count",
        lambda *a, **k: 60_001,
    )

    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    (src / "one.txt").write_bytes(b"x")

    copy2_calls = []

    def track_copy2(src_path, dst_path):
        copy2_calls.append((src_path, dst_path))

    monkeypatch.setattr(shutil, "copy2", track_copy2)
    monkeypatch.setattr("os_toolkit.transfer.robocopy.robocopy_on_path", lambda: True)

    def raise_not_found(*_a, **_k):
        raise FileNotFoundError("robocopy")

    monkeypatch.setattr("os_toolkit.transfer.robocopy.subprocess.run", raise_not_found)

    def reject_pool(*_a, **_k):
        raise AssertionError("HDD fallback must use hdd_copy, not thread pool")

    with patch("os_toolkit.transfer.copy.ThreadPoolExecutor", side_effect=reject_pool):
        parallel_copy(str(src), str(dst), workers=1, verbosity=0, dry_run=False)
    assert copy2_calls
