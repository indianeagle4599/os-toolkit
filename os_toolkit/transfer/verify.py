"""
verify — post-copy size checks used during resume/skip logic.
"""

import os


def destination_matches_size(dst_path: str, expected_size: int) -> bool:
    return os.path.exists(dst_path) and os.path.getsize(dst_path) == expected_size
