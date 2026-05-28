"""Analyze profile artifacts — specs/analyze_profile.md."""

import json
import os

from os_toolkit.analysis.profile import run_profile_to_dir
from os_toolkit.analysis.runs import write_manifest


def test_profile_writes_json_and_csv(usage_tree, runs_root):
    """Guarantee: profile JSON and features CSV under run directory."""
    run_path = str(runs_root / "test_run")
    os.makedirs(run_path, exist_ok=True)
    profile_path, csv_path = run_profile_to_dir(
        str(usage_tree), run_path, prefix="", verbosity=0
    )
    assert os.path.isfile(profile_path)
    assert os.path.isfile(csv_path)
    with open(profile_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "" in data
    assert data[""]["files"] >= 1


def test_manifest_records_outputs(usage_tree, runs_root):
    run_path = str(runs_root / "manifest_run")
    os.makedirs(run_path, exist_ok=True)
    run_profile_to_dir(str(usage_tree), run_path, prefix="", verbosity=0)
    write_manifest(
        run_path,
        {
            "command": "analyze.profile",
            "inputs": {"root": str(usage_tree)},
            "outputs": {"profile": os.path.join(run_path, "profile.json")},
        },
    )
    manifest = runs_root / "manifest_run" / "manifest.json"
    assert manifest.is_file()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["command"] == "analyze.profile"
