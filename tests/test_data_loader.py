"""
test_data_loader.py

Unit tests for the JSON data loader.
"""

import json
import pytest
from datetime import date
from pathlib import Path

from growth_charts.data_loader import load_data, _parse_date, _parse_measurement, _parse_child
from growth_charts.models import Child


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def valid_json(tmp_path) -> Path:
    """Write a minimal valid JSON data file and return its path."""
    data = {
        "family": {
            "father_height_cm": 180.0,
            "mother_height_cm": 165.0
        },
        "children": [
            {
                "name": "Test",
                "sex": "M",
                "dob": "2020-01-01",
                "measurements": [
                    {
                        "date": "2020-01-01",
                        "height_cm": 50.0,
                        "weight_kg": 3.4,
                        "head_circumference_cm": 34.5,
                    },
                    {
                        "date": "2021-01-01",
                        "height_cm": 75.0,
                        "weight_kg": 9.5,
                    },
                ]
            }
        ]
    }
    path = tmp_path / "test_data.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def partial_measurements_json(tmp_path) -> Path:
    """Write a JSON file with height-only and weight-only measurements."""
    data = {
        "children": [
            {
                "name": "Test",
                "sex": "F",
                "dob": "2021-06-01",
                "measurements": [
                    {"date": "2021-06-01", "weight_kg": 3.2},
                    {"date": "2021-09-01", "height_cm": 60.0},
                    {"date": "2022-06-01", "head_circumference_cm": 46.0},
                    {
                        "date": "2022-12-01",
                        "height_cm": 78.0,
                        "weight_kg": 10.5,
                    },
                ]
            }
        ]
    }
    path = tmp_path / "partial.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def no_family_json(tmp_path) -> Path:
    """Write a JSON file with no family block."""
    data = {
        "children": [
            {
                "name": "Test",
                "sex": "F",
                "dob": "2021-06-01",
                "measurements": [
                    {"date": "2021-06-01", "height_cm": 49.0, "weight_kg": 3.2},
                ]
            }
        ]
    }
    path = tmp_path / "no_family.json"
    path.write_text(json.dumps(data))
    return path


# ── Date parsing tests ────────────────────────────────────────────────────────

class TestParseDate:

    def test_valid_date(self):
        assert _parse_date("2020-01-15") == date(2020, 1, 15)

    def test_invalid_format_raises_error(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            _parse_date("01/15/2020")

    def test_invalid_date_raises_error(self):
        with pytest.raises(ValueError):
            _parse_date("2020-13-01")


# ── Measurement parsing tests ─────────────────────────────────────────────────

class TestParseMeasurement:

    def test_full_measurement_parsed_correctly(self):
        dob = date(2020, 1, 1)
        data = {
            "date": "2021-01-01",
            "height_cm": 75.0,
            "weight_kg": 9.5,
            "head_circumference_cm": 46.0,
        }
        m = _parse_measurement(data, dob)
        assert m is not None
        assert m.height_cm == 75.0
        assert m.weight_kg == 9.5
        assert m.head_circumference_cm == 46.0

    def test_age_months_calculated_correctly(self):
        dob = date(2020, 1, 1)
        data = {"date": "2021-01-01", "height_cm": 75.0, "weight_kg": 9.5}
        m = _parse_measurement(data, dob)
        assert m is not None
        assert m.age_months == pytest.approx(12.0, abs=0.2)

    def test_height_only_measurement(self):
        dob = date(2020, 1, 1)
        data = {"date": "2021-01-01", "height_cm": 75.0}
        m = _parse_measurement(data, dob)
        assert m is not None
        assert m.height_cm == 75.0
        assert m.weight_kg is None

    def test_weight_only_measurement(self):
        dob = date(2020, 1, 1)
        data = {"date": "2021-01-01", "weight_kg": 9.5}
        m = _parse_measurement(data, dob)
        assert m is not None
        assert m.weight_kg == 9.5
        assert m.height_cm is None

    def test_head_circumference_only_measurement(self):
        dob = date(2020, 1, 1)
        data = {"date": "2020-07-01", "head_circumference_cm": 43.0}
        m = _parse_measurement(data, dob)
        assert m is not None
        assert m.head_circumference_cm == 43.0
        assert m.height_cm is None
        assert m.weight_kg is None

    def test_no_values_returns_none(self):
        dob = date(2020, 1, 1)
        data = {"date": "2021-01-01"}
        m = _parse_measurement(data, dob)
        assert m is None

    def test_missing_date_raises_error(self):
        dob = date(2020, 1, 1)
        with pytest.raises(KeyError):
            _parse_measurement({"height_cm": 67.0}, dob)

    def test_bmi_not_stored_in_json(self):
        """BMI should be computed as a property, never loaded from JSON."""
        dob = date(2020, 1, 1)
        data = {
            "date": "2022-01-01",
            "height_cm": 87.0,
            "weight_kg": 12.0,
            "bmi": 99.9,  # should be ignored
        }
        m = _parse_measurement(data, dob)
        assert m is not None
        # BMI should be calculated from height/weight, not the stored value
        assert m.bmi != 99.9
        assert m.bmi == pytest.approx(12.0 / (0.87 ** 2), abs=0.1)


# ── Child parsing tests ───────────────────────────────────────────────────────

class TestParseChild:

    def test_parses_name_and_sex(self):
        data = {
            "name": "Alex",
            "sex": "M",
            "dob": "2020-01-01",
            "measurements": []
        }
        child = _parse_child(data)
        assert child.name == "Alex"
        assert child.sex == "M"

    def test_parses_measurements(self):
        data = {
            "name": "Alex",
            "sex": "M",
            "dob": "2020-01-01",
            "measurements": [
                {"date": "2020-01-01", "height_cm": 50.0, "weight_kg": 3.4},
                {"date": "2021-01-01", "height_cm": 75.0, "weight_kg": 9.5},
            ]
        }
        child = _parse_child(data)
        assert len(child.measurements) == 2

    def test_parses_partial_measurements(self):
        """Measurements with only some fields should be included."""
        data = {
            "name": "Alex",
            "sex": "M",
            "dob": "2020-01-01",
            "measurements": [
                {"date": "2020-01-01", "weight_kg": 3.4},
                {"date": "2021-01-01", "height_cm": 75.0},
                {"date": "2021-07-01", "head_circumference_cm": 46.0},
            ]
        }
        child = _parse_child(data)
        assert len(child.measurements) == 3

    def test_skips_empty_measurements(self):
        """Measurements with no values should be skipped."""
        data = {
            "name": "Alex",
            "sex": "M",
            "dob": "2020-01-01",
            "measurements": [
                {"date": "2020-01-01", "height_cm": 50.0, "weight_kg": 3.4},
                {"date": "2020-07-01"},  # no values — should be skipped
            ]
        }
        child = _parse_child(data)
        assert len(child.measurements) == 1

    def test_empty_measurements_allowed(self):
        data = {
            "name": "Alex",
            "sex": "M",
            "dob": "2020-01-01",
            "measurements": [],
        }
        child = _parse_child(data)
        assert child.measurements == []


# ── load_data tests ───────────────────────────────────────────────────────────

class TestLoadData:

    def test_returns_correct_keys(self, valid_json):
        result = load_data(valid_json)
        assert "children" in result
        assert "father_cm" in result
        assert "mother_cm" in result

    def test_loads_parental_heights(self, valid_json):
        result = load_data(valid_json)
        assert result["father_cm"] == pytest.approx(180.0)
        assert result["mother_cm"] == pytest.approx(165.0)

    def test_loads_correct_number_of_children(self, valid_json):
        result = load_data(valid_json)
        assert len(result["children"]) == 1

    def test_children_are_child_objects(self, valid_json):
        result = load_data(valid_json)
        assert isinstance(result["children"][0], Child)

    def test_loads_head_circumference(self, valid_json):
        result = load_data(valid_json)
        first_measurement = result["children"][0].measurements[0]
        assert first_measurement.head_circumference_cm == pytest.approx(34.5)

    def test_loads_partial_measurements(self, partial_measurements_json):
        result = load_data(partial_measurements_json)
        measurements = result["children"][0].measurements
        assert len(measurements) == 4
        assert measurements[0].weight_kg == pytest.approx(3.2)
        assert measurements[0].height_cm is None
        assert measurements[1].height_cm == pytest.approx(60.0)
        assert measurements[1].weight_kg is None
        assert measurements[2].head_circumference_cm == pytest.approx(46.0)

    def test_missing_family_block_returns_none(self, no_family_json):
        result = load_data(no_family_json)
        assert result["father_cm"] is None
        assert result["mother_cm"] is None

    def test_file_not_found_raises_error(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_data(tmp_path / "nonexistent.json")

    def test_invalid_json_raises_error(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("this is not json {{{")
        with pytest.raises(Exception):
            load_data(bad_file)