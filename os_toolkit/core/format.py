"""
format — human-readable sizes, durations, and transfer rates.
"""


def human_readable_size(size_bytes, *, extended_units: bool = False) -> str:
    """
    Convert byte count to a compact size string.

    extended_units: when True, sizes beyond TB render as PB (smart_zip lineage).
    """
    size = float(size_bytes)
    units = ("B", "KB", "MB", "GB", "TB")
    for unit in units:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        if unit != "TB":
            size /= 1024.0
    if extended_units:
        return f"{size:.1f} PB"
    return f"{size:.1f} TB"


def format_eta(eta_seconds: int) -> str:
    """Format seconds remaining as a compact ETA string."""
    eta = int(eta_seconds)
    if eta < 3600:
        return f"{eta // 60}:{eta % 60:02d}"
    if eta < 86400:
        return f"{eta // 3600}h {(eta % 3600) // 60:02d}m"
    if eta < 604800:
        return f"{eta // 86400}d {(eta % 86400) // 3600:02d}h"
    if eta < 31536000:
        return f"{eta // 604800}w {(eta % 604800) // 86400}d"
    return f"{eta // 31536000}y {(eta % 31536000) // 86400}d"
