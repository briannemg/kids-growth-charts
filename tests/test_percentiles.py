"""
test_percentiles.py

Unit tests for percentile calculations using CDC and WHO LMS tables.

Known reference values for sanity-checking the LMS math are taken
directly from the CDC documentation examples.
"""

import pytest
from growth_charts.percentiles import (
    load_all_tables,
    get_percentile,
    get_percentile_series,
    _lms_to_zscore,
    _zscore_to_percentile,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def tables():
    """
    Load all LMS tables once for the entire test module.
    scope="module" means this runs once and is shared across all tests,
    keeping the test suite fast.
    """
    return load_all_tables()


# ── LMS math tests ────────────────────────────────────────────────────────────

class TestLMSMath:

    def test_lms_to_zscore_nonzero_l(self):
        """
        CDC documented example: 9-month male weighing 9.7 kg should
        produce a z-score of approximately 0.207.
        L=-0.1600954, M=9.476500305, S=0.11218624
        """
        z = _lms_to_zscore(9.7, L=-0.1600954, m=9.476500305, s=0.11218624)
        assert z == pytest.approx(0.207, abs=0.01)

    def test_lms_to_zscore_zero_l(self):
        """When L=0 the log formula is used instead."""
        z = _lms_to_zscore(10.0, L=0.0, m=10.0, s=0.1)
        assert z == pytest.approx(0.0, abs=0.001)

    def test_zscore_to_percentile_median(self):
        """Z-score of 0 should equal the 50th percentile."""
        assert _zscore_to_percentile(0.0) == pytest.approx(50.0, abs=0.1)

    def test_zscore_to_percentile_positive(self):
        """Z-score of 1.645 should equal approximately the 95th percentile."""
        assert _zscore_to_percentile(1.645) == pytest.approx(95.0, abs=0.1)

    def test_zscore_to_percentile_negative(self):
        """Z-score of -1.645 should equal approximately the 5th percentile."""
        assert _zscore_to_percentile(-1.645) == pytest.approx(5.0, abs=0.1)


# ── Table loading tests ───────────────────────────────────────────────────────

class TestTableLoading:

    def test_tables_loads_all_keys(self, tables):
        assert "cdc" in tables
        assert "who" in tables

    def test_cdc_has_expected_keys(self, tables):
        assert "height" in tables["cdc"]
        assert "weight" in tables["cdc"]
        assert "bmi" in tables["cdc"]
        assert "height_infant" in tables["cdc"]
        assert "weight_infant" in tables["cdc"]
        assert "head_circumference" in tables["cdc"]

    def test_who_has_expected_sex_keys(self, tables):
        assert "M" in tables["who"]["height"]
        assert "F" in tables["who"]["height"]
        assert "M" in tables["who"]["head_circumference"]
        assert "F" in tables["who"]["head_circumference"]

    def test_cdc_table_has_lms_columns(self, tables):
        df = tables["cdc"]["height"]
        for col in ("sex", "agemos", "l", "m", "s"):
            assert col in df.columns, f"Missing column: {col}"

    def test_cdc_bmi_table_has_lms_columns(self, tables):
        df = tables["cdc"]["bmi"]
        for col in ("sex", "agemos", "l", "m", "s"):
            assert col in df.columns, f"Missing column: {col}"

    def test_cdc_head_circumference_table_has_lms_columns(self, tables):
        df = tables["cdc"]["head_circumference"]
        for col in ("sex", "agemos", "l", "m", "s"):
            assert col in df.columns, f"Missing column: {col}"

    def test_who_table_has_lms_columns(self, tables):
        df = tables["who"]["height"]["M"]
        for col in ("agemos", "l", "m", "s"):
            assert col in df.columns, f"Missing column: {col}"

    def test_who_head_circumference_table_has_lms_columns(self, tables):
        df = tables["who"]["head_circumference"]["M"]
        for col in ("agemos", "l", "m", "s"):
            assert col in df.columns, f"Missing column: {col}"


# ── Height and weight percentile tests ───────────────────────────────────────

class TestGetPercentileHeightWeight:

    def test_median_value_returns_near_50th(self, tables):
        """
        A child whose height equals the M value at their age should be
        at approximately the 50th percentile.
        Using age 35.5 months, M=94.646370 from CDC stature table (sex=1).
        """
        result = get_percentile(35.5, 94.646370, "M", "height", tables)
        assert result == pytest.approx(50.0, abs=2.0)

    def test_who_used_under_24_months(self, tables):
        """Ages under 24 months should return a valid percentile using WHO data."""
        result = get_percentile(12.0, 75.0, "M", "height", tables)
        assert result is not None
        assert 0 < result < 100

    def test_cdc_used_at_24_months(self, tables):
        """Ages at exactly 24 months should use CDC data."""
        result = get_percentile(24.0, 86.0, "M", "height", tables)
        assert result is not None
        assert 0 < result < 100

    def test_cdc_used_over_24_months(self, tables):
        result = get_percentile(48.0, 102.0, "M", "height", tables)
        assert result is not None
        assert 0 < result < 100

    def test_female_height_percentile(self, tables):
        result = get_percentile(36.0, 94.0, "F", "height", tables)
        assert result is not None
        assert 0 < result < 100

    def test_weight_percentile(self, tables):
        result = get_percentile(12.0, 9.5, "M", "weight", tables)
        assert result is not None
        assert 0 < result < 100

    def test_tall_child_above_50th(self, tables):
        result = get_percentile(48.0, 115.0, "M", "height", tables)
        assert result is not None
        assert result > 50.0

    def test_short_child_below_50th(self, tables):
        result = get_percentile(48.0, 90.0, "M", "height", tables)
        assert result is not None
        assert result < 50.0


# ── Head circumference percentile tests ──────────────────────────────────────

class TestGetPercentileHeadCircumference:

    def test_who_used_under_24_months(self, tables):
        """Head circumference under 24 months should use WHO data."""
        result = get_percentile(6.0, 43.0, "M", "head_circumference", tables)
        assert result is not None
        assert 0 < result < 100

    def test_cdc_used_at_24_to_36_months(self, tables):
        """Head circumference 24–36 months should use CDC data."""
        result = get_percentile(30.0, 49.0, "M", "head_circumference", tables)
        assert result is not None
        assert 0 < result < 100

    def test_returns_none_beyond_36_months(self, tables):
        """Head circumference beyond 36 months has no reference data."""
        result = get_percentile(48.0, 50.0, "M", "head_circumference", tables)
        assert result is None

    def test_female_head_circumference(self, tables):
        result = get_percentile(6.0, 41.5, "F", "head_circumference", tables)
        assert result is not None
        assert 0 < result < 100

    def test_large_head_above_50th(self, tables):
        result = get_percentile(6.0, 46.0, "M", "head_circumference", tables)
        assert result is not None
        assert result > 50.0

    def test_small_head_below_50th(self, tables):
        result = get_percentile(6.0, 40.0, "M", "head_circumference", tables)
        assert result is not None
        assert result < 50.0


# ── BMI percentile tests ──────────────────────────────────────────────────────

class TestGetPercentileBMI:

    def test_bmi_returns_none_under_24_months(self, tables):
        """BMI percentiles are not available for children under 24 months."""
        result = get_percentile(12.0, 17.0, "M", "bmi", tables)
        assert result is None

    def test_bmi_at_24_months(self, tables):
        result = get_percentile(24.0, 16.5, "M", "bmi", tables)
        assert result is not None
        assert 0 < result < 100

    def test_bmi_over_24_months(self, tables):
        result = get_percentile(60.0, 15.5, "M", "bmi", tables)
        assert result is not None
        assert 0 < result < 100

    def test_high_bmi_above_50th(self, tables):
        """A BMI of 18 at age 5 should be well above the 50th percentile."""
        result = get_percentile(60.0, 18.0, "M", "bmi", tables)
        assert result is not None
        assert result > 50.0

    def test_low_bmi_below_50th(self, tables):
        """A BMI of 13 at age 5 should be below the 50th percentile."""
        result = get_percentile(60.0, 13.0, "M", "bmi", tables)
        assert result is not None
        assert result < 50.0

    def test_female_bmi_percentile(self, tables):
        result = get_percentile(60.0, 15.5, "F", "bmi", tables)
        assert result is not None
        assert 0 < result < 100


# ── Error handling tests ──────────────────────────────────────────────────────

class TestGetPercentileErrors:

    def test_invalid_measure_raises_error(self, tables):
        with pytest.raises(ValueError, match="measure must be one of"):
            get_percentile(24.0, 86.0, "M", "wingspan", tables)

    def test_invalid_sex_raises_error(self, tables):
        with pytest.raises(ValueError, match="sex must be 'M' or 'F'"):
            get_percentile(24.0, 86.0, "X", "height", tables)


# ── Percentile series tests ───────────────────────────────────────────────────

class TestGetPercentileSeries:

    def test_returns_correct_length(self, tables):
        ages = [12.0, 24.0, 36.0]
        heights = [75.0, 86.0, 96.0]
        result = get_percentile_series(ages, heights, "M", "height", tables)
        assert len(result) == 3

    def test_mismatched_lengths_raises_error(self, tables):
        with pytest.raises(ValueError, match="must have the same length"):
            get_percentile_series([12.0, 24.0], [75.0], "M", "height", tables)

    def test_all_values_in_valid_range(self, tables):
        ages = [6.0, 12.0, 24.0, 36.0, 60.0]
        heights = [67.0, 75.0, 86.0, 96.0, 110.0]
        results = get_percentile_series(ages, heights, "F", "height", tables)
        for r in results:
            assert r is not None
            assert 0 < r < 100

    def test_bmi_series_returns_none_under_24_months(self, tables):
        """BMI percentiles should be None for ages under 24 months."""
        ages = [6.0, 12.0, 24.0, 36.0]
        bmis = [17.0, 17.0, 16.5, 15.8]
        results = get_percentile_series(ages, bmis, "M", "bmi", tables)
        assert results[0] is None
        assert results[1] is None
        assert results[2] is not None
        assert results[3] is not None