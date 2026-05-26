"""
features — flatten nested profiles to CSV rows.
"""

import csv
from typing import List


def flatten_profile(profile: dict, base_path: str = "", depth: int = 0) -> List[dict]:
    rows = []
    stats = profile.copy()
    children = stats.pop("profile", {})
    name = base_path.replace("\\", "/").rsplit("/", 1)[-1] if base_path else ""

    rows.append(
        {
            "path": base_path or ".",
            "depth": depth,
            "size_bytes": stats.get("size", 0),
            "files": stats.get("files", 0),
            "folders": stats.get("folders", 0),
            "name": name,
        }
    )

    for child_path, child_profile in children.items():
        rows.extend(flatten_profile(child_profile, child_path, depth + 1))

    return rows


def write_features_csv(rows: List[dict], output_path: str) -> str:
    if not rows:
        raise ValueError("No feature rows to write.")
    keys = rows[0].keys()
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    return output_path
