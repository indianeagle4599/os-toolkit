#!/usr/bin/env python3

"""
features.py - Extract folder profile features.

Features:
- Flatten nested profile JSON into CSV rows
- Preserve path, depth, size, file count, folder count, and folder name
"""

import json
import csv
import argparse


def flatten_profile(profile: dict, base_path: str = "", depth: int = 0):
    """
    Recursively flatten a nested profile into a list of dictionaries.
    Each entry contains path and folder-level stats + structural features.
    """
    rows = []
    stats = profile.copy()
    children = stats.pop("profile", {})
    name = base_path.replace("\\", "/").rsplit("/", 1)[-1] if base_path else ""

    row = {
        "path": base_path or ".",
        "depth": depth,
        "size_bytes": stats.get("size", 0),
        "files": stats.get("files", 0),
        "folders": stats.get("folders", 0),
        "name": name,
    }

    rows.append(row)

    for child_path, child_profile in children.items():
        rows.extend(flatten_profile(child_profile, child_path, depth + 1))

    return rows


def save_to_csv(rows, output_file):
    if not rows:
        print("⚠️ No data to write.")
        return

    keys = rows[0].keys()
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ CSV features saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract features from nested folder profile into CSV"
    )
    parser.add_argument("input", help="Path to input profile_nested.json")
    parser.add_argument(
        "-o", "--output", default="features.csv", help="Output CSV file"
    )

    args = parser.parse_args()

    with open(args.input, "r") as f:
        data = json.load(f)

    root_profile = data.get("", {})
    flattened = flatten_profile(root_profile)

    save_to_csv(flattened, args.output)


if __name__ == "__main__":
    main()
