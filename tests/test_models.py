"""
test_models.py

Unit tests for the Child and Measurement data classes.
"""

import pytest
from datetime import date
from growth_charts.models import Child, Measurement


# ── Measurement tests ─────────────────────────────────────────────────────────

class TestMeasurement:

    def test_valid_measurement_height_and_weight(self):
        m = Measurement(
            date=date(2024, 1, 1),
            age_months=12.0,
            height_cm=75.0,
            weight_kg=9.5,
        )
        assert m.height_cm == 75.0
        assert m.weight_kg == 9.5

    def test_valid_measurement_height_only(self):
        m = Measurement(
            date=date(2024, 1, 1),
            age_months=12.0,
            height_cm=75.0,
        )
        assert m.height_cm == 75.0
        assert m.weight_kg is None

    def test_valid_measurement_weight_only(self):
        m = Measurement(
            date=date(2024, 1, 1),
            age_months=12.0,
            weight_kg=9.5,
        )
        assert m.weight_kg == 9.5
        assert m.height_cm is None

    def test_valid_measurement_head_circumference_only(self):
        m = Measurement(
            date=date(2024, 1, 1),
            age_months=2.0,
            head_circumference_cm=38.5,
        )
        assert m.head_circumference_cm == 38.5
        assert m.height_cm is None
        assert m.weight_kg is None

    def test_valid_measurement_all_fields(self):
        m = Measurement(
            date=date(2024, 1, 1),
            age_months=6.0,
            height_cm=67.0,
            weight_kg=7.5,
            head_circumference_cm=43.0,
        )
        assert m.height_cm == 67.0
        assert m.weight_kg == 7.5
        assert m.head_circumference_cm == 43.0

    def test_no_measurements_raises_error(self):
        with pytest.raises(ValueError, match="at least one of"):
            Measurement(
                date=date(2024, 1, 1),
                age_months=12.0,
            )

    def test_negative_age_raises_error(self):
        with pytest.raises(ValueError, match="age_months must be non-negative"):
            Measurement(
                date=date(2024, 1, 1),
                age_months=-1.0,
                height_cm=75.0,
            )

    def test_zero_height_raises_error(self):
        with pytest.raises(ValueError, match="height_cm must be greater than zero"):
            Measurement(
                date=date(2024, 1, 1),
                age_months=12.0,
                height_cm=0.0,
            )

    def test_zero_weight_raises_error(self):
        with pytest.raises(ValueError, match="weight_kg must be greater than zero"):
            Measurement(
                date=date(2024, 1, 1),
                age_months=12.0,
                weight_kg=0.0,
            )

    def test_zero_head_circumference_raises_error(self):
        with pytest.raises(
            ValueError, match="head_circumference_cm must be greater than zero"
        ):
            Measurement(
                date=date(2024, 1, 1),
                age_months=2.0,
                head_circumference_cm=0.0,
            )

    def test_negative_height_raises_error(self):
        with pytest.raises(ValueError):
            Measurement(
                date=date(2024, 1, 1),
                age_months=12.0,
                height_cm=-5.0,
            )


# ── BMI property tests ────────────────────────────────────────────────────────

class TestBMIProperty:

    def test_bmi_calculated_when_height_and_weight_present(self):
        m = Measurement(
            date=date(2024, 1, 1),
            age_months=36.0,
            height_cm=96.0,
            weight_kg=14.5,
        )
        assert m.bmi == pytest.approx(15.7, abs=0.1)

    def test_bmi_none_when_height_missing(self):
        m = Measurement(
            date=date(2024, 1, 1),
            age_months=36.0,
            weight_kg=14.5,
        )
        assert m.bmi is None

    def test_bmi_none_when_weight_missing(self):
        m = Measurement(
            date=date(2024, 1, 1),
            age_months=36.0,
            height_cm=96.0,
        )
        assert m.bmi is None

    def test_bmi_formula_correct(self):
        """BMI = weight_kg / (height_m ** 2)"""
        m = Measurement(
            date=date(2024, 1, 1),
            age_months=60.0,
            height_cm=110.0,
            weight_kg=18.5,
        )
        expected = round(18.5 / (1.10 ** 2), 1)
        assert m.bmi == pytest.approx(expected, abs=0.01)

    def test_bmi_rounds_to_one_decimal(self):
        m = Measurement(
            date=date(2024, 1, 1),
            age_months=60.0,
            height_cm=110.0,
            weight_kg=18.5,
        )
        assert m.bmi is not None
        assert len(str(m.bmi).split(".")[-1]) <= 1


# ── Child tests ───────────────────────────────────────────────────────────────

class TestChild:

    def setup_method(self):
        """Create a reusable Child instance for each test."""
        self.dob = date(2020, 1, 1)
        self.child = Child(name="Alex", sex="M", dob=self.dob)

    def test_valid_child_creates_successfully(self):
        assert self.child.name == "Alex"
        assert self.child.sex == "M"

    def test_invalid_sex_raises_error(self):
        with pytest.raises(ValueError, match="sex must be 'M' or 'F'"):
            Child(name="Alex", sex="X", dob=self.dob)

    def test_empty_name_raises_error(self):
        with pytest.raises(ValueError, match="name must not be empty"):
            Child(name="   ", sex="M", dob=self.dob)

    def test_default_measurements_is_empty_list(self):
        assert self.child.measurements == []

    def test_age_months_at_one_year(self):
        one_year_later = date(2021, 1, 1)
        assert self.child.age_months_at(one_year_later) == pytest.approx(12.0, abs=0.2)

    def test_age_months_at_birth_is_zero(self):
        assert self.child.age_months_at(self.dob) == 0.0

    def test_latest_measurement_returns_none_when_empty(self):
        assert self.child.latest_measurement is None

    def test_latest_measurement_returns_most_recent(self):
        m1 = Measurement(
            date=date(2021, 1, 1),
            age_months=12.0,
            height_cm=75.0,
            weight_kg=9.5,
        )
        m2 = Measurement(
            date=date(2022, 1, 1),
            age_months=24.0,
            height_cm=87.0,
            weight_kg=12.0,
        )
        self.child.measurements = [m1, m2]
        assert self.child.latest_measurement == m2

    def test_latest_measurement_order_independent(self):
        """Latest measurement should be correct regardless of list order."""
        m1 = Measurement(
            date=date(2021, 1, 1),
            age_months=12.0,
            height_cm=75.0,
            weight_kg=9.5,
        )
        m2 = Measurement(
            date=date(2022, 1, 1),
            age_months=24.0,
            height_cm=87.0,
            weight_kg=12.0,
        )
        self.child.measurements = [m2, m1]
        assert self.child.latest_measurement == m2

    def test_latest_measurement_works_with_partial_measurements(self):
        """latest_measurement should work when measurements have optional fields."""
        m1 = Measurement(
            date=date(2021, 1, 1),
            age_months=12.0,
            weight_kg=9.5,
        )
        m2 = Measurement(
            date=date(2022, 1, 1),
            age_months=24.0,
            height_cm=87.0,
        )
        self.child.measurements = [m1, m2]
        assert self.child.latest_measurement == m2