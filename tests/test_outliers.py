"""Modified Z-score outlier detection — benchmarks/outliers.py."""

from benchmarks.outliers import modified_z_scores, outlier_flags


def test_modified_z_small_n_returns_zeros():
    assert modified_z_scores([1.0, 2.0]) == [0.0, 0.0]


def test_outlier_flags_mad_zero_no_false_on_median():
    values = [10.0, 10.0, 10.0, 50.0]
    flags = outlier_flags(values)
    assert flags.count(True) == 1


def test_outlier_flags_stable_cluster():
    values = [100.0, 101.0, 99.0, 100.5, 98.0]
    assert not any(outlier_flags(values))


def test_outlier_flags_detects_spike():
    values = [10.0, 10.0, 10.0, 10.0, 100.0]
    flags = outlier_flags(values)
    assert flags[-1]
    assert not any(flags[:-1])
