"""Tests for os_toolkit.core — specs implied by shared library contracts."""

import os
from types import ModuleType

from os_toolkit.core.config import cfg_get
from os_toolkit.core.format import format_eta, human_readable_size
from os_toolkit.core.paths import extended_path, is_under, path_parts, rel_path


def test_human_readable_size_boundaries():
    """Core size formatting used across tools."""
    assert human_readable_size(0) == "0.0 B"
    assert "KB" in human_readable_size(2048)
    assert human_readable_size(1024**4).endswith("TB")


def test_format_eta_tiers():
    assert format_eta(90) == "1:30"
    assert "h" in format_eta(7200)


def test_cfg_get_prefers_config_module():
    mod = ModuleType("cfg")
    mod.WORKERS = 4
    assert cfg_get(mod, "WORKERS", 1) == 4
    assert cfg_get(None, "WORKERS", 1) == 1
    mod.EMPTY = ""
    assert cfg_get(mod, "EMPTY", 9) == 9


def test_rel_path_at_root():
    root = os.path.abspath(os.sep if os.name == "nt" else "/")
    assert rel_path(root, root) == ""


def test_path_parts_normalizes():
    assert path_parts("a\\b/c") == ("a", "b", "c")
    assert path_parts("") == ()


def test_extended_path_windows_prefix(monkeypatch):
    if os.name != "nt":
        return
    monkeypatch.setattr(os, "name", "nt")
    out = extended_path("C:\\temp\\file.txt")
    assert out.startswith("\\\\?\\")


def test_is_under(tmp_path):
    root = tmp_path / "root"
    sub = root / "sub"
    sub.mkdir(parents=True)
    sibling = tmp_path / "other"
    sibling.mkdir()
    assert is_under(str(sub), str(root))
    assert is_under(str(root), str(root))
    assert not is_under(str(sibling), str(root))
