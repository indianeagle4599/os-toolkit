"""Registry validation: every dataset entry is complete before fetch time."""

from urllib.parse import urlparse

import pytest

from benchmarks.datasets import DATASETS

REQUIRED = ("name", "category", "expected_size_min", "license_name", "attribution")


def _primary_url(entry: dict) -> str:
    url = entry.get("url")
    if url:
        return url
    urls = entry.get("urls")
    if urls:
        return urls[0]
    pytest.fail(f"{entry.get('name')}: missing url or urls")


@pytest.mark.parametrize("entry", DATASETS, ids=[d["name"] for d in DATASETS])
def test_dataset_entry_complete(entry):
    for key in REQUIRED:
        assert entry.get(key), f"{entry['name']}: missing {key}"

    url = _primary_url(entry)
    parsed = urlparse(url)
    assert parsed.scheme in ("http", "https"), f"{entry['name']}: invalid URL scheme"
    assert parsed.netloc, f"{entry['name']}: invalid URL host"
    assert "TODO" not in url.upper()
    assert "placeholder" not in url.lower()

    assert entry["expected_size_min"] > 0
