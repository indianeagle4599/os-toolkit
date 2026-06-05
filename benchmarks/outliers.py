"""
outliers — modified Z-score outlier detection via median absolute deviation.

MAD is used instead of standard deviation because it is robust to small
samples and non-normal distributions — both common in wall-time measurements.
"""

from typing import List, Sequence

MAD_SCALE = 1.4826
DEFAULT_THRESHOLD = 3.5


def _median(values) -> float:
    """Median via sorted list (no statistics module)."""
    if not isinstance(values, (list, tuple)):
        values = list(values)
    n = len(values)
    if n == 0:
        return 0.0
    ordered = sorted(values)
    mid = n // 2
    if n % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def median_abs_deviation(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    med = _median(values)
    return _median(abs(v - med) for v in values)


def modified_z_scores(values: Sequence[float]) -> List[float]:
    n = len(values)
    if n < 3:
        return [0.0] * n
    med = _median(values)
    mad = median_abs_deviation(values)
    if mad == 0:
        return [0.0 if v == med else 999.0 for v in values]
    return [MAD_SCALE * (v - med) / mad for v in values]


def outlier_flags(
    values: Sequence[float], *, threshold: float = DEFAULT_THRESHOLD
) -> List[bool]:
    return [abs(z) > threshold for z in modified_z_scores(values)]
