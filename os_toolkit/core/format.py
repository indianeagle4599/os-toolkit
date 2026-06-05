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


def format_progress_bar(
    bytes_done: int,
    bytes_total: int,
    elapsed: float,
    files_done: int,
    total_files: int,
    *,
    bar_width: int = 20,
) -> str:
    """Render copy progress: bar, bytes, speed, ETA, and file counts."""
    if bytes_total <= 0:
        return f"{files_done} files"
    pct = min(bytes_done, bytes_total) / bytes_total
    filled = int(bar_width * pct)
    bar = "#" * filled + "-" * (bar_width - filled)
    speed = bytes_done / elapsed if elapsed > 0 and bytes_done > 0 else 0
    remaining = bytes_total - min(bytes_done, bytes_total)
    eta_str = (
        format_eta(int(remaining / speed))
        if speed > 0 and remaining > 0
        else "--:--"
    )
    br_show = min(bytes_done, bytes_total)
    files_part = (
        f"{files_done}/{total_files} files"
        if total_files
        else f"{files_done} files"
    )
    return (
        f"[{bar}] {pct * 100:5.1f}%  |  "
        f"{human_readable_size(br_show)} / {human_readable_size(bytes_total)}  |  "
        f"{human_readable_size(int(speed))}/s  |  "
        f"ETA {eta_str}  |  "
        f"{files_part}"
    )
