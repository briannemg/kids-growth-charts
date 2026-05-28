"""
test_adult_height.py

Unit tests for adult height projection functions.
"""

import pytest
from growth_charts.adult_height import (
    mid_parental_height,
    mid_parental_height_range,
    doubling_method_age,
    is_near_doubling_age,
    project_adult_height_doubling,
    project_adult_height_from_percentile,
    project_adult_height_from_current,
)
from growth_charts.percentiles import load_all_tables


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def tables():
    """Load all LMS tables once for the entire test module."""
    return load_all_tables()


# ── Mid-parental height tests ─────────────────────────────────────────────────

class TestMidParentalHeight:

    def test_male_target(self):
        """Boys: (180 + 165 + 13) / 2 = 179.0 cm"""
        assert mid_parental_height(180.0, 165.0, "M") == pytest.approx(179.0, abs=0.1)

    def test_female_target(self):
        """Girls: (180 + 165 - 13) / 2 = 166.0 cm"""
        assert mid_parental_height(180.0, 165.0, "F") == pytest.approx(166.0, abs=0.1)

    def test_male_taller_than_female_same_parents(self):
        """Male projection should always be taller than female for same parents."""
        male = mid_parental_height(175.0, 162.0, "M")
        female = mid_parental_height(175.0, 162.0, "F")
        assert male > female

    def test_male_female_difference_is_13cm(self):
        """The difference between male and female projections should be exactly 13 cm."""
        male = mid_parental_height(175.0, 162.0, "M")
        female = mid_parental_height(175.0, 162.0, "F")
        assert (male - female) == pytest.approx(13.0, abs=0.01)

    def test_invalid_sex_raises_error(self):
        with pytest.raises(ValueError, match="sex must be 'M' or 'F'"):
            mid_parental_height(180.0, 165.0, "X")

    def test_zero_father_height_raises_error(self):
        with pytest.raises(ValueError, match="father_cm must be greater than zero"):
            mid_parental_height(0.0, 165.0, "M")

    def test_zero_mother_height_raises_error(self):
        with pytest.raises(ValueError, match="mother_cm must be greater than zero"):
            mid_parental_height(180.0, 0.0, "F")


class TestMidParentalHeightRange:

    def test_range_is_17cm_wide(self):
        """Range should be ± 8.5 cm, so total width is 17 cm."""
        low, high = mid_parental_height_range(180.0, 165.0, "M")
        assert (high - low) == pytest.approx(17.0, abs=0.01)

    def test_range_centered_on_target(self):
        """Range midpoint should equal the MPH target."""
        target = mid_parental_height(180.0, 165.0, "M")
        low, high = mid_parental_height_range(180.0, 165.0, "M")
        assert (low + high) / 2 == pytest.approx(target, abs=0.01)

    def test_low_is_less_than_high(self):
        low, high = mid_parental_height_range(175.0, 162.0, "F")
        assert low < high


# ── Doubling method tests ─────────────────────────────────────────────────────

class TestDoublingMethod:

    def test_doubling_age_male_is_24_months(self):
        assert doubling_method_age("M") == 24.0

    def test_doubling_age_female_is_18_months(self):
        assert doubling_method_age("F") == 18.0

    def test_doubling_age_invalid_sex_raises_error(self):
        with pytest.raises(ValueError, match="sex must be 'M' or 'F'"):
            doubling_method_age("X")

    def test_doubling_projects_correctly(self):
        """A boy who is 88 cm at age 2 should project to 176 cm."""
        assert project_adult_height_doubling(88.0, "M") == pytest.approx(176.0, abs=0.1)

    def test_doubling_girl_projects_correctly(self):
        """A girl who is 81 cm at 18 months should project to 162 cm."""
        assert project_adult_height_doubling(81.0, "F") == pytest.approx(162.0, abs=0.1)

    def test_doubling_zero_height_raises_error(self):
        with pytest.raises(ValueError, match="height_at_reference_age_cm must be greater than zero"):
            project_adult_height_doubling(0.0, "M")

    def test_doubling_invalid_sex_raises_error(self):
        with pytest.raises(ValueError, match="sex must be 'M' or 'F'"):
            project_adult_height_doubling(88.0, "X")

    def test_is_near_doubling_age_exact_match(self):
        assert is_near_doubling_age(24.0, "M") is True
        assert is_near_doubling_age(18.0, "F") is True

    def test_is_near_doubling_age_within_tolerance(self):
        assert is_near_doubling_age(23.0, "M") is True   # 1 month early
        assert is_near_doubling_age(25.5, "M") is True   # 1.5 months late

    def test_is_near_doubling_age_outside_tolerance(self):
        assert is_near_doubling_age(12.0, "M") is False  # way too young
        assert is_near_doubling_age(36.0, "M") is False  # way too old

    def test_is_near_doubling_age_invalid_sex_raises_error(self):
        with pytest.raises(ValueError, match="sex must be 'M' or 'F'"):
            is_near_doubling_age(24.0, "X")


# ── Percentile projection tests ───────────────────────────────────────────────

class TestProjectFromPercentile:

    def test_50th_percentile_male_reasonable_adult_height(self, tables):
        """A 50th percentile male should project to roughly 176 cm (5'9")."""
        result = project_adult_height_from_percentile(50.0, "M", tables)
        assert result is not None
        assert 170.0 < result < 182.0

    def test_50th_percentile_female_reasonable_adult_height(self, tables):
        """A 50th percentile female should project to roughly 163 cm (5'4")."""
        result = project_adult_height_from_percentile(50.0, "F", tables)
        assert result is not None
        assert 157.0 < result < 169.0

    def test_higher_percentile_gives_taller_projection(self, tables):
        """90th percentile should project taller than 50th percentile."""
        p50 = project_adult_height_from_percentile(50.0, "M", tables)
        p90 = project_adult_height_from_percentile(90.0, "M", tables)
        assert p90 is not None
        assert p50 is not None
        assert p90 > p50

    def test_male_taller_than_female_at_same_percentile(self, tables):
        """Male 50th percentile should project taller than female 50th percentile."""
        male = project_adult_height_from_percentile(50.0, "M", tables)
        female = project_adult_height_from_percentile(50.0, "F", tables)
        assert male is not None
        assert female is not None
        assert male > female

    def test_invalid_percentile_raises_error(self, tables):
        with pytest.raises(ValueError, match="current_percentile must be between"):
            project_adult_height_from_percentile(0.0, "M", tables)

    def test_percentile_over_100_raises_error(self, tables):
        with pytest.raises(ValueError, match="current_percentile must be between"):
            project_adult_height_from_percentile(100.0, "M", tables)

    def test_invalid_sex_raises_error(self, tables):
        with pytest.raises(ValueError, match="sex must be 'M' or 'F'"):
            project_adult_height_from_percentile(50.0, "X", tables)


# ── Current measurement projection tests ─────────────────────────────────────

class TestProjectFromCurrent:

    def test_returns_reasonable_adult_height(self, tables):
        """A typical 5-year-old male height should project to a reasonable adult height."""
        result = project_adult_height_from_current(60.0, 110.0, "M", tables)
        assert result is not None
        assert 150.0 < result < 200.0

    def test_taller_child_projects_taller_adult(self, tables):
        """A taller child at the same age should project to a taller adult height."""
        shorter = project_adult_height_from_current(60.0, 105.0, "M", tables)
        taller = project_adult_height_from_current(60.0, 115.0, "M", tables)
        assert shorter is not None
        assert taller is not None
        assert taller > shorter

    def test_female_projection(self, tables):
        result = project_adult_height_from_current(60.0, 108.0, "F", tables)
        assert result is not None
        assert 140.0 < result < 190.0