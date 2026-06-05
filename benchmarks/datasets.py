"""
datasets — registry of optional corpus sources for fetch_corpus.py.
"""

from typing import List, TypedDict


class DatasetEntry(TypedDict, total=False):
    name: str
    category: str
    url: str
    urls: List[str]
    license_name: str
    license_url: str
    attribution: str
    expected_size_min: int
    extract_subdir: str
    note: str


DATASETS: List[DatasetEntry] = [
    {
        "name": "python_stdlib_lib",
        "category": "code",
        "url": "https://github.com/python/cpython/archive/refs/tags/v3.13.0.tar.gz",
        "expected_size_min": 20_000_000,
        "extract_subdir": "cpython-3.13.0/Lib",
        "license_name": "PSF License",
        "license_url": "https://docs.python.org/3/license.html",
        "attribution": "Python standard library (cpython Lib/)",
    },
    {
        "name": "gutenberg_top100",
        "category": "plain_text",
        "urls": [
            "https://www.gutenberg.org/cache/epub/1342/pg1342.txt",
            "https://www.gutenberg.org/cache/epub/11/pg11.txt",
            "https://www.gutenberg.org/cache/epub/2701/pg2701.txt",
            "https://www.gutenberg.org/cache/epub/84/pg84.txt",
            "https://www.gutenberg.org/cache/epub/1080/pg1080.txt",
            "https://www.gutenberg.org/cache/epub/2542/pg2542.txt",
            "https://www.gutenberg.org/cache/epub/345/pg345.txt",
            "https://www.gutenberg.org/cache/epub/98/pg98.txt",
            "https://www.gutenberg.org/cache/epub/74/pg74.txt",
            "https://www.gutenberg.org/cache/epub/2600/pg2600.txt",
        ],
        "expected_size_min": 5_000_000,
        "license_name": "Public Domain",
        "license_url": "https://www.gutenberg.org/policy/terms_of_use.html",
        "attribution": "Project Gutenberg",
    },
    {
        "name": "coco2017_val_subset",
        "category": "images",
        # HTTPS on images.cocodataset.org fails cert verification (hostname mismatch, 2026-05).
        "url": "http://images.cocodataset.org/zips/val2017.zip",
        "expected_size_min": 700_000_000,
        "note": "~778 MB compressed, ~5000 JPEG images",
        "license_name": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": "COCO Consortium",
    },
    {
        "name": "librispeech_dev_clean",
        "category": "audio",
        "url": "https://www.openslr.org/resources/12/dev-clean.tar.gz",
        "expected_size_min": 300_000_000,
        "license_name": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": "LibriSpeech",
    },
    {
        "name": "linux_kernel_src",
        "category": "code",
        "url": "https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.6.1.tar.xz",
        "expected_size_min": 130_000_000,
        "note": "Many small text files, deep tree structure",
        "license_name": "GPL-2.0",
        "license_url": "https://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
        "attribution": "Linux kernel",
    },
    {
        "name": "newsgroups_20",
        "category": "plain_text",
        "url": "http://qwone.com/~jason/20Newsgroups/20news-bydate.tar.gz",
        "expected_size_min": 13_000_000,
        "license_name": "Public Domain",
        "license_url": "",
        "attribution": "20 Newsgroups corpus",
    },
    {
        "name": "scipy_lectures",
        "category": "code",
        "url": "https://github.com/scipy-lectures/scientific-python-lectures/archive/refs/heads/main.tar.gz",
        "expected_size_min": 5_000_000,
        "license_name": "CC BY",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": "SciPy lectures contributors",
    },
]
