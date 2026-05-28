"""
test_units.py

Unit tests for all measurement conversion and formatting functions.
"""

import pytest
from datetime import date
from growth_charts.units import (
    feet_inches_to_cm,
    inches_to_cm,
    cm_to_feet_inches,
    cm_to_inches,
    lbs_oz_to_kg,
    lbs_to_kg,
    kg_to_lbs_oz,
    kg_to_lbs,
    format_feet_inches,
    format_decimal_inches,
    format_cm,
    format_lbs_oz,
    format_decimal_lbs,
    format_kg,
    format_age,
    ordinal,
)


# ── Height conversion tests ───────────────────────────────────────────────────

class TestHeightConversions:

    def test_feet_inches_to_cm_standard(self):
        assert feet_inches_to_cm(3, 2) == pytest.approx(96.52, abs=0.01)

    def test_feet_inches_to_cm_zero_feet(self):
        assert feet_inches_to_cm(0, 6) == pytest.approx(15.24, abs=0.01)

    def test_feet_inches_to_cm_negative_feet_raises(self):
        with pytest.raises(ValueError, match="feet must be non-negative"):
            feet_inches_to_cm(-1, 0)

    def test_feet_inches_to_cm_invalid_inches_raises(self):
        with pytest.raises(ValueError, match="inches must be between 0 and 11.99"):
            feet_inches_to_cm(3, 12)

    def test_inches_to_cm_standard(self):
        assert inches_to_cm(38.5) == pytest.approx(97.79, abs=0.01)

    def test_inches_to_cm_zero_raises(self):
        with pytest.raises(ValueError, match="inches must be greater than zero"):
            inches_to_cm(0)

    def test_cm_to_feet_inches_standard(self):
        feet, inches = cm_to_feet_inches(96.52)
        assert feet == 3
        assert inches == pytest.approx(2.0, abs=0.1)

    def test_cm_to_inches_standard(self):
        assert cm_to_inches(97.79) == pytest.approx(38.5, abs=0.1)

    def test_cm_to_inches_rounds_to_one_decimal(self):
        result = cm_to_inches(97.79)
        assert len(str(result).split(".")[-1]) <= 1

    def test_height_round_trip_feet_inches(self):
        original_feet, original_inches = 4, 6
        cm = feet_inches_to_cm(original_feet, original_inches)
        feet, inches = cm_to_feet_inches(cm)
        assert feet == original_feet
        assert inches == pytest.approx(original_inches, abs=0.1)


# ── Weight conversion tests ───────────────────────────────────────────────────

class TestWeightConversions:

    def test_lbs_oz_to_kg_standard(self):
        assert lbs_oz_to_kg(8, 4) == pytest.approx(3.742, abs=0.001)

    def test_lbs_oz_to_kg_zero_pounds(self):
        assert lbs_oz_to_kg(0, 8) == pytest.approx(0.227, abs=0.001)

    def test_lbs_oz_to_kg_negative_pounds_raises(self):
        with pytest.raises(ValueError, match="pounds must be non-negative"):
            lbs_oz_to_kg(-1, 0)

    def test_lbs_oz_to_kg_invalid_ounces_raises(self):
        with pytest.raises(ValueError, match="ounces must be between 0 and 15.99"):
            lbs_oz_to_kg(8, 16)

    def test_lbs_to_kg_standard(self):
        assert lbs_to_kg(22.5) == pytest.approx(10.206, abs=0.001)

    def test_lbs_to_kg_zero_raises(self):
        with pytest.raises(ValueError, match="pounds must be greater than zero"):
            lbs_to_kg(0)

    def test_kg_to_lbs_oz_standard(self):
        pounds, ounces = kg_to_lbs_oz(3.742)
        assert pounds == 8
        assert ounces == pytest.approx(4.0, abs=0.2)

    def test_kg_to_lbs_standard(self):
        assert kg_to_lbs(10.206) == pytest.approx(22.5, abs=0.1)

    def test_kg_to_lbs_rounds_to_one_decimal(self):
        result = kg_to_lbs(10.206)
        assert len(str(result).split(".")[-1]) <= 1

    def test_weight_round_trip_lbs_oz(self):
        original_lbs, original_oz = 15, 8
        kg = lbs_oz_to_kg(original_lbs, original_oz)
        pounds, ounces = kg_to_lbs_oz(kg)
        assert pounds == original_lbs
        assert ounces == pytest.approx(original_oz, abs=0.1)


# ── Atomic formatter tests ────────────────────────────────────────────────────

class TestHeightFormatters:

    def test_format_feet_inches(self):
        result = format_feet_inches(96.52)
        assert "ft" in result
        assert "in" in result
        assert "3 ft" in result

    def test_format_feet_inches_zero_raises(self):
        with pytest.raises(ValueError, match="cm must be greater than zero"):
            format_feet_inches(0.0)

    def test_format_decimal_inches(self):
        result = format_decimal_inches(97.79)
        assert "in" in result
        assert "38.5" in result

    def test_format_decimal_inches_zero_raises(self):
        with pytest.raises(ValueError, match="cm must be greater than zero"):
            format_decimal_inches(0.0)

    def test_format_cm(self):
        result = format_cm(50.0)
        assert "cm" in result
        assert "50.0" in result

    def test_format_cm_rounds_to_one_decimal(self):
        result = format_cm(50.123)
        assert "50.1" in result

    def test_format_cm_zero_raises(self):
        with pytest.raises(ValueError, match="cm must be greater than zero"):
            format_cm(0.0)


class TestWeightFormatters:

    def test_format_lbs_oz(self):
        result = format_lbs_oz(3.742)
        assert "lb" in result
        assert "oz" in result
        assert "8 lb" in result

    def test_format_lbs_oz_zero_raises(self):
        with pytest.raises(ValueError, match="kg must be greater than zero"):
            format_lbs_oz(0.0)

    def test_format_decimal_lbs(self):
        result = format_decimal_lbs(10.206)
        assert "lb" in result
        assert "22.5" in result

    def test_format_decimal_lbs_zero_raises(self):
        with pytest.raises(ValueError, match="kg must be greater than zero"):
            format_decimal_lbs(0.0)

    def test_format_kg(self):
        result = format_kg(3.742)
        assert "kg" in result
        assert "3.7" in result

    def test_format_kg_rounds_to_one_decimal(self):
        result = format_kg(3.742)
        assert "3.7" in result

    def test_format_kg_zero_raises(self):
        with pytest.raises(ValueError, match="kg must be greater than zero"):
            format_kg(0.0)


# ── Age formatting tests ──────────────────────────────────────────────────────

class TestFormatAge:

    def test_zero_days(self):
        d = date(2020, 1, 1)
        assert format_age(d, d) == "0 days"

    def test_single_day(self):
        assert format_age(date(2020, 1, 1), date(2020, 1, 2)) == "1 day"

    def test_multiple_days(self):
        assert format_age(date(2020, 1, 1), date(2020, 1, 5)) == "4 days"

    def test_exactly_one_month(self):
        assert format_age(date(2020, 1, 1), date(2020, 2, 1)) == "1 month"

    def test_months_only(self):
        assert format_age(date(2020, 1, 1), date(2020, 7, 1)) == "6 months"

    def test_months_and_days(self):
        assert format_age(date(2020, 1, 1), date(2020, 7, 8)) == "6 months 7 days"

    def test_exactly_one_year(self):
        assert format_age(date(2020, 1, 1), date(2021, 1, 1)) == "1 year"

    def test_years_only(self):
        assert format_age(date(2020, 1, 1), date(2022, 1, 1)) == "2 years"

    def test_years_and_months(self):
        assert format_age(date(2020, 1, 1), date(2021, 3, 1)) == "1 year 2 months"

    def test_years_months_days(self):
        assert format_age(
            date(2020, 1, 1), date(2021, 3, 13)
        ) == "1 year 2 months 12 days"

    def test_omits_zero_months(self):
        assert format_age(date(2020, 1, 1), date(2021, 1, 6)) == "1 year 5 days"

    def test_measurement_before_dob_raises_error(self):
        with pytest.raises(ValueError, match="cannot be before dob"):
            format_age(date(2020, 6, 1), date(2020, 1, 1))

    def test_month_boundary_borrowing(self):
        assert format_age(date(2020, 1, 31), date(2020, 3, 1)) == "1 month 1 day"


# ── Ordinal formatting tests ──────────────────────────────────────────────────

class TestOrdinal:

    def test_first(self):
        assert ordinal(1) == "1st"

    def test_second(self):
        assert ordinal(2) == "2nd"

    def test_third(self):
        assert ordinal(3) == "3rd"

    def test_fourth(self):
        assert ordinal(4) == "4th"

    def test_eleventh(self):
        assert ordinal(11) == "11th"

    def test_twelfth(self):
        assert ordinal(12) == "12th"

    def test_thirteenth(self):
        assert ordinal(13) == "13th"

    def test_twenty_first(self):
        assert ordinal(21) == "21st"

    def test_twenty_second(self):
        assert ordinal(22) == "22nd"

    def test_one_hundredth(self):
        assert ordinal(100) == "100th"

    def test_one_hundred_eleventh(self):
        assert ordinal(111) == "111th"

    def test_zero(self):
        assert ordinal(0) == "0th"

    def test_negative_raises_error(self):
        with pytest.raises(ValueError, match="n must be non-negative"):
            ordinal(-1)