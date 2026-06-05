"""
End-to-end usability tests — user-visible CLI and bench behavior.

Bounded subprocess timeouts; mark slow tests >10s with @pytest.mark.slow.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from benchmarks import fetch_corpus

REPO_ROOT = Path(__file__).resolve().parents[1]

JSONL_REQUIRED = (
    "tool",
    "scenario_id",
    "corpus_signature",
    "wall_time_sec",
    "bytes_per_sec",
    "exit_status",
)
TRANSFER_EXTRA = ("physical_id_src", "physical_id_dst", "same_physical_device")

PRO_SCRIPTS = (
    ("file_transfer_pro.py", "Parallel directory copy"),
    ("disk_analyzer_pro.py", "Disk Analyzer"),
    ("smart_zip_pro.py", "zip"),
    ("analyze_pro.py", "Analyze Pro"),
)

JUST_EXE = shutil.which("just") or shutil.which("just.cmd")


def _require_just():
    if not JUST_EXE:
        pytest.skip("just not installed")


BAD_CORPUS = (
    "C:\\nonexistent_os_toolkit_corpus_xyz"
    if sys.platform == "win32"
    else "/nonexistent_os_toolkit_corpus_xyz"
)


def _run(cmd, timeout: float, cwd=None):
    return subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
    )


def _load_jsonl(path: Path):
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines]


@pytest.mark.slow
def test_just_check_passes():
    _require_just()
    proc = _run([JUST_EXE, "check"], timeout=180)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_just_list_shows_recipes():
    _require_just()
    proc = _run([JUST_EXE, "--list"], timeout=30)
    assert proc.returncode == 0, proc.stderr
    text = proc.stdout
    for recipe in ("check", "bench", "transfer", "analyze", "bench-fetch"):
        assert recipe in text, f"missing recipe {recipe} in just --list"


def test_fetch_corpus_handles_bad_url_gracefully(tmp_path, monkeypatch, capsys):
    manifest = tmp_path / "toolkit_manifest.json"
    from benchmarks import corpus as corpus_mod

    monkeypatch.setattr(fetch_corpus, "CACHE_ROOT", tmp_path / "cache")
    monkeypatch.setattr(corpus_mod, "MANIFEST_PATH", manifest)

    bad = {
        "name": "broken_test_ds",
        "category": "structured",
        "url": "https://httpbin.org/status/404",
        "expected_size_min": 1,
        "license_name": "test",
        "attribution": "test",
    }
    good = {
        "name": "good_test_ds",
        "category": "code",
        "url": "https://example.com/ok",
        "expected_size_min": 1,
        "license_name": "test",
        "attribution": "test",
    }

    def fake_fetch(entry, force):
        if entry["name"] == bad["name"]:
            return fetch_corpus._fail(
                {
                    "name": bad["name"],
                    "status": "pending",
                    "size_bytes": 0,
                    "hash": "",
                    "fetched_at": fetch_corpus._utc_now(),
                },
                "HTTP 404 for https://httpbin.org/status/404",
            )
        return {
            "name": good["name"],
            "status": "ok",
            "size_bytes": 100,
            "hash": "abc",
            "fetched_at": fetch_corpus._utc_now(),
        }

    monkeypatch.setattr(fetch_corpus, "DATASETS", [bad, good])
    monkeypatch.setattr(fetch_corpus, "fetch_one", fake_fetch)
    monkeypatch.setattr(sys, "argv", ["fetch_corpus"])

    fetch_corpus.main()
    captured = capsys.readouterr()
    assert "404" in captured.out or "404" in captured.err
    assert "[fail] broken_test_ds" in captured.out

    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["datasets"]["broken_test_ds"]["status"] == "failed"
    assert data["datasets"]["good_test_ds"]["status"] == "ok"


def test_bench_transfer_preserves_user_corpus(tmp_path):
    user_corpus = tmp_path / "user_corpus"
    user_corpus.mkdir()
    marker = user_corpus / "keep_me.txt"
    marker.write_text("x", encoding="utf-8")
    out = tmp_path / "transfer.jsonl"

    proc = _run(
        [
            sys.executable,
            "-m",
            "benchmarks.run_transfer",
            "--corpus",
            str(user_corpus),
            "--ignore-manifest",
            "--output",
            str(out),
        ],
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert marker.is_file(), "user --corpus path must survive bench transfer"


@pytest.mark.parametrize(
    "module",
    [
        "benchmarks.run_transfer",
        "benchmarks.run_analysis",
        "benchmarks.run_zip",
    ],
)
def test_bench_runners_validate_corpus_path(module):
    proc = _run(
        [sys.executable, "-m", module, "--corpus", BAD_CORPUS],
        timeout=30,
    )
    combined = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "corpus path not found" in combined.lower()
    assert "Traceback" not in combined


@pytest.mark.parametrize("script,needle", PRO_SCRIPTS)
def test_root_pro_help_works(script, needle):
    proc = _run([sys.executable, script, "--help"], timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert needle.lower() in proc.stdout.lower()


def test_jsonl_outputs_have_required_fields(tmp_path):
    out_t = tmp_path / "transfer.jsonl"
    out_a = tmp_path / "analysis.jsonl"
    out_z = tmp_path / "zip.jsonl"

    for module, out in (
        ("benchmarks.run_transfer", out_t),
        ("benchmarks.run_analysis", out_a),
        ("benchmarks.run_zip", out_z),
    ):
        proc = _run(
            [
                sys.executable,
                "-m",
                module,
                "--ignore-manifest",
                "--output",
                str(out),
            ],
            timeout=30,
        )
        assert proc.returncode == 0, f"{module}: {proc.stderr}"
        records = _load_jsonl(out)
        assert records, f"{module}: no JSONL lines"
        for rec in records:
            for key in JSONL_REQUIRED:
                assert key in rec, f"{module} missing {key} in {rec.get('tool')}"
            if module == "benchmarks.run_transfer":
                for key in TRANSFER_EXTRA:
                    assert key in rec
