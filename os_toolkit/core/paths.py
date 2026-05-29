"""
paths — normalization, Windows extended paths, relative paths.
"""

import os
from typing import Union

PathLike = Union[str, os.PathLike]


def extended_path(path: PathLike) -> str:
    """Prefix path for Windows extended-length path support (>260 chars)."""
    path = os.fspath(path)
    if os.name == "nt" and not path.startswith("\\\\?\\"):
        return "\\\\?\\" + os.path.abspath(path)
    return path


def rel_path(root: PathLike, path: PathLike) -> str:
    """Relative path from root; empty string when path is root."""
    rel = os.path.relpath(os.fspath(path), os.fspath(root))
    return "" if rel == "." else rel


def path_parts(rel: str) -> tuple:
    """Split a relative path into lowercase tuple segments."""
    if not rel:
        return ()
    return tuple(part for part in str(rel).replace("\\", "/").split("/") if part)


def is_under(child: PathLike, parent: PathLike) -> bool:
    """True when child is parent or a path inside parent."""
    child_abs = os.path.normcase(os.path.abspath(os.fspath(child)))
    parent_abs = os.path.normcase(os.path.abspath(os.fspath(parent)))
    if child_abs == parent_abs:
        return True
    sep = os.sep
    return child_abs.startswith(parent_abs + sep)
