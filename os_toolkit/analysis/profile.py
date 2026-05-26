"""
profile — one-pass nested filesystem profiles (JSON).
"""

import json
import os
from typing import Dict

from os_toolkit.analysis.features import flatten_profile, write_features_csv
from os_toolkit.core.paths import rel_path


def blank_profile() -> Dict:
    return {"size": 0, "files": 0, "folders": 0, "profile": {}}


def generate_nested_profile(root: str, verbosity: int) -> Dict:
    profile_map = {}

    def on_error(error):
        if verbosity >= 2:
            print(f"[WARN] skipped directory: {error.filename} ({error.strerror})")

    for current_dir, dirs, files in os.walk(root, topdown=False, onerror=on_error):
        profile = blank_profile()

        for filename in files:
            path = os.path.join(current_dir, filename)
            try:
                profile["size"] += os.path.getsize(path)
                profile["files"] += 1
            except OSError as error:
                if verbosity >= 2:
                    print(f"[WARN] skipped file: {path} ({error.strerror})")

        for dirname in dirs:
            child_key = rel_path(root, os.path.join(current_dir, dirname))
            child = profile_map.get(child_key)
            if child is None:
                profile["folders"] += 1
                continue
            profile["size"] += child["size"]
            profile["files"] += child["files"]
            profile["folders"] += 1 + child["folders"]
            profile["profile"][child_key] = child

        key = rel_path(root, current_dir)
        profile_map[key] = profile
        if verbosity >= 2:
            print(
                f"[OK] {key or '.'} -> size={profile['size']} | "
                f"files={profile['files']} | folders={profile['folders']}"
            )

    if verbosity >= 1:
        print(f"\nTotal folders scanned: {len(profile_map)}")

    return {"": profile_map.get("", blank_profile())}


def write_profile_json(profile: Dict, output_path: str) -> str:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
    return output_path


def run_profile_to_dir(
    root: str, run_path: str, prefix: str = "", verbosity: int = 1
) -> tuple:
    """Scan root, write profile JSON and features CSV under run_path."""
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        raise NotADirectoryError(f"{root} is not a valid directory")

    if verbosity >= 1:
        print(f"Scanning: {root}...")

    profile = generate_nested_profile(root, verbosity)
    profile_path = os.path.join(run_path, f"{prefix}profile.json")
    write_profile_json(profile, profile_path)

    rows = flatten_profile(profile.get("", {}))
    features_path = os.path.join(run_path, f"{prefix}features.csv")
    write_features_csv(rows, features_path)

    if verbosity >= 1:
        print(f"Profile: {profile_path}")
        print(f"Features: {features_path}")

    return profile_path, features_path
