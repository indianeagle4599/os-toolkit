#!/usr/bin/env python3

"""
profile.py - One-pass nested filesystem profiler.

Features:
- Build folder-level size, file count, and folder count profiles
- Export nested JSON profiles for later comparison
"""

import os
import json
import argparse
from typing import Dict


def blank_profile() -> Dict:
    return {"size": 0, "files": 0, "folders": 0, "profile": {}}


def rel_path(root: str, path: str) -> str:
    rel = os.path.relpath(path, root)
    return "" if rel == "." else rel


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
                f"[✓] {key or '.'} → size={profile['size']} | "
                f"files={profile['files']} | folders={profile['folders']}"
            )

    if verbosity >= 1:
        print(f"\n📁 Total folders scanned: {len(profile_map)}")

    return {"": profile_map.get("", blank_profile())}


def main():
    parser = argparse.ArgumentParser(description="One-pass nested filesystem profiler")
    parser.add_argument("root", help="Root directory to scan")
    parser.add_argument(
        "-o", "--output", default="profile_nested.json", help="Output JSON file"
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        type=int,
        choices=[0, 1, 2],
        default=1,
        help="Verbosity level",
    )

    args = parser.parse_args()
    root = os.path.abspath(args.root)

    if not os.path.isdir(root):
        raise NotADirectoryError(f"❌ {root} is not a valid directory")

    if args.verbosity >= 1:
        print(f"🔍 Scanning: {root}...")

    profile = generate_nested_profile(root, args.verbosity)

    with open(args.output, "w") as f:
        json.dump(profile, f, indent=2)

    if args.verbosity >= 1:
        print(f"\n✅ Nested profile saved to {args.output}")


if __name__ == "__main__":
    main()
