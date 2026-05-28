"""Smart zip scan and scoring — specs/smart_zip.md."""

import argparse

import pytest

from os_toolkit.transfer.archive import run_smart_zip
from os_toolkit.transfer.archive_scan import choose_candidates, scan_root, settings


def _args(root, **kw):
    ns = argparse.Namespace(
        root=str(root),
        output="",
        sensitivity="high",
        exclude=[],
        workers=1,
        verbosity=0,
        dry_run=True,
        interactive=False,
        execute=False,
        overwrite=False,
        resume=False,
        delete_originals=False,
    )
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


def test_dry_run_does_not_create_zip(tmp_path, capsys):
    """Guarantee: default path is recommendation-only."""
    root = tmp_path / "project"
    root.mkdir(parents=True, exist_ok=True)
    for i in range(120):
        d = root / f"dir{i}"
        d.mkdir(exist_ok=True)
        (d / "f.txt").write_bytes(b"x" * 100)
    run_smart_zip(_args(root), parser=None)
    assert not any(p.suffix == ".zip" for p in tmp_path.rglob("*"))


def test_output_must_be_outside_root(tmp_path):
    """Guarantee: zip output cannot lie inside scan root."""
    root = tmp_path / "root"
    root.mkdir()
    inner = root / "out"
    inner.mkdir()
    args = _args(root, output=str(inner), dry_run=False, execute=True)
    with pytest.raises(SystemExit):
        run_smart_zip(args, parser=None)


def test_scan_and_choose_candidates(tmp_path):
    root = tmp_path / "pack"
    sub = root / "many_small"
    sub.mkdir(parents=True)
    for i in range(200):
        (sub / f"f{i}.txt").write_bytes(b"a" * 50)
    cfg = settings(_args(root), None)
    stats = scan_root(cfg)
    candidates = choose_candidates(stats, cfg)
    assert isinstance(candidates, list)
