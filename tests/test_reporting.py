"""
test_reporting.py

Unit tests for markdown report generation.
"""

import pytest
from datetime import date

from growth_charts.models import Child, Measurement
from growth_charts.percentiles import load_all_tables
from growth_charts.reporting import (
    generate_report,
    _format_percentile,
    _build_summary_section,
    _build_measurements_table,
    _has_head_circumference,
    _has_bmi,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def tables():
    """Load all LMS tables once for the entire test module."""
    return load_all_tables()


@pytest.fixture
def sample_child():
    """A child with full measurements spanning both WHO and CDC age ranges."""
    return Child(
        name="Test Child",
        sex="M",
        dob=date(2020, 1, 1),
        measurements=[
            Measurement(date=date(2020, 1, 1),  age_months=0.0,
                        height_cm=50.0, weight_kg=3.4,
                        head_circumference_cm=34.5),
            Measurement(date=date(2020, 7, 1),  age_months=6.0,
                        height_cm=67.0, weight_kg=7.5,
                        head_circumference_cm=43.0),
            Measurement(date=date(2021, 1, 1),  age_months=12.0,
                        height_cm=75.0, weight_kg=9.5,
                        head_circumference_cm=46.0),
            Measurement(date=date(2022, 1, 1),  age_months=24.0,
                        height_cm=87.0, weight_kg=12.0),
            Measurement(date=date(2023, 1, 1),  age_months=36.0,
                        height_cm=96.0, weight_kg=14.5),
            Measurement(date=date(2025, 1, 1),  age_months=60.0,
                        height_cm=110.0, weight_kg=18.5),
        ],
    )


@pytest.fixture
def infant_only_child():
    """A child with only infant measurements."""
    return Child(
        name="Infant",
        sex="F",
        dob=date(2024, 1, 1),
        measurements=[
            Measurement(date=date(2024, 1, 1), age_months=0.0,
                        height_cm=49.0, weight_kg=3.2,
                        head_circumference_cm=33.5),
            Measurement(date=date(2024, 7, 1), age_months=6.0,
                        height_cm=65.0, weight_kg=7.0,
                        head_circumference_cm=42.0),
            Measurement(date=date(2025, 1, 1), age_months=12.0,
                        height_cm=74.0, weight_kg=9.2,
                        head_circumference_cm=45.5),
        ],
    )


@pytest.fixture
def partial_child():
    """A child with some height-only and weight-only measurements."""
    return Child(
        name="Partial",
        sex="M",
        dob=date(2021, 1, 1),
        measurements=[
            Measurement(date=date(2021, 1, 1), age_months=0.0,
                        weight_kg=3.5),
            Measurement(date=date(2021, 7, 1), age_months=6.0,
                        height_cm=66.0, weight_kg=7.8),
            Measurement(date=date(2022, 1, 1), age_months=12.0,
                        height_cm=74.0),
            Measurement(date=date(2023, 1, 1), age_months=24.0,
                        height_cm=86.0, weight_kg=11.5),
        ],
    )


# ── Data availability helper tests ────────────────────────────────────────────

class TestDataAvailabilityHelpers:

    def test_has_head_circumference_true(self, sample_child):
        assert _has_head_circumference(sample_child) is True

    def test_has_head_circumference_false(self, partial_child):
        assert _has_head_circumference(partial_child) is False

    def test_has_bmi_true(self, sample_child):
        """sample_child has height and weight at 24+ months."""
        assert _has_bmi(sample_child) is True

    def test_has_bmi_false_infant_only(self, infant_only_child):
        """Infant-only child has no data at 24+ months."""
        assert _has_bmi(infant_only_child) is False

    def test_has_bmi_false_no_paired_measurements(self):
        """Child with height-only and weight-only at 24+ months has no BMI."""
        no_bmi = Child(
            name="NoBMI", sex="M", dob=date(2020, 1, 1),
            measurements=[
                Measurement(date=date(2022, 1, 1), age_months=24.0,
                            height_cm=87.0),
                Measurement(date=date(2022, 7, 1), age_months=30.0,
                            weight_kg=13.0),
            ],
        )
        assert _has_bmi(no_bmi) is False


# ── Formatting helper tests ───────────────────────────────────────────────────

class TestFormatPercentile:

    def test_standard_percentile(self):
        assert _format_percentile(45.3) == "45th"

    def test_none_returns_dash(self):
        assert _format_percentile(None) == "-"

    def test_first_percentile(self):
        assert _format_percentile(1.0) == "1st"

    def test_third_percentile(self):
        assert _format_percentile(3.0) == "3rd"

    def test_rounds_correctly(self):
        assert _format_percentile(74.6) == "75th"


# ── Summary section tests ─────────────────────────────────────────────────────

class TestBuildSummarySection:

    def test_contains_child_name(self, sample_child, tables):
        result = _build_summary_section(sample_child, tables, None, None)
        assert "Test Child" in result

    def test_contains_sex(self, sample_child, tables):
        result = _build_summary_section(sample_child, tables, None, None)
        assert "Male" in result

    def test_contains_dob(self, sample_child, tables):
        result = _build_summary_section(sample_child, tables, None, None)
        assert "January 1, 2020" in result

    def test_mph_shown_when_parental_heights_provided(self, sample_child, tables):
        result = _build_summary_section(sample_child, tables, 180.0, 165.0)
        assert "Mid-Parental Height Method" in result

    def test_mph_not_shown_without_parental_heights(self, sample_child, tables):
        result = _build_summary_section(sample_child, tables, None, None)
        assert "Mid-Parental Height Method" not in result

    def test_doubling_method_shown_when_applicable(self, sample_child, tables):
        result = _build_summary_section(sample_child, tables, None, None)
        assert "Doubling Method" in result

    def test_doubling_method_no_age_label(self, sample_child, tables):
        result = _build_summary_section(sample_child, tables, None, None)
        assert "measurement at" not in result

    def test_most_recent_measurements_shown(self, sample_child, tables):
        result = _build_summary_section(sample_child, tables, None, None)
        assert "Most Recent Measurements" in result

    def test_height_uses_feet_inches_format(self, sample_child, tables):
        result = _build_summary_section(sample_child, tables, None, None)
        assert "ft" in result
        assert "in" in result

    def test_weight_uses_lbs_oz_format(self, sample_child, tables):
        result = _build_summary_section(sample_child, tables, None, None)
        assert "lb" in result
        assert "oz" in result

    def test_head_circumference_shown_in_summary_when_latest_has_it(
        self, infant_only_child, tables
    ):
        """When the most recent measurement has HC data it should appear
        in the summary section."""
        result = _build_summary_section(infant_only_child, tables, None, None)
        assert "Head Circumference" in result

    def test_head_circumference_in_measurements_table_when_available(
        self, sample_child, tables
    ):
        """HC appears in the measurements table for early rows even when
        the most recent measurement doesn't have it."""
        result = _build_measurements_table(sample_child, tables)
        assert "Head Circ" in result

    def test_head_circumference_not_shown_when_unavailable(
        self, partial_child, tables
    ):
        result = _build_summary_section(partial_child, tables, None, None)
        assert "Head Circumference" not in result

    def test_bmi_shown_when_available(self, sample_child, tables):
        result = _build_summary_section(sample_child, tables, None, None)
        assert "BMI" in result

    def test_bmi_not_shown_for_infant_only(self, infant_only_child, tables):
        result = _build_summary_section(infant_only_child, tables, None, None)
        assert "BMI" not in result

    def test_label_column_is_right_aligned(self, sample_child, tables):
        result = _build_summary_section(sample_child, tables, None, None)
        assert 'align="right"' in result

    def test_no_metric_height_in_height_row(self, sample_child, tables):
        """Height row should not show raw cm value."""
        result = _build_summary_section(sample_child, tables, None, None)
        most_recent = result.split("Most Recent")[1]
        assert "110.0 cm" not in most_recent

    def test_female_shows_correct_sex(self, infant_only_child, tables):
        result = _build_summary_section(infant_only_child, tables, None, None)
        assert "Female" in result

    def test_partial_measurements_no_crash(self, partial_child, tables):
        result = _build_summary_section(partial_child, tables, None, None)
        assert "Partial" in result


# ── Measurements table tests ──────────────────────────────────────────────────

class TestBuildMeasurementsTable:

    def test_contains_standard_columns(self, sample_child, tables):
        result = _build_measurements_table(sample_child, tables)
        assert "Date of Measurement" in result
        assert "Age at Measurement" in result
        assert "Projected Adult Height" in result
        assert "Height (ft / in)" in result
        assert "Weight (lb / oz)" in result

    def test_contains_head_circumference_column_when_available(
        self, sample_child, tables
    ):
        result = _build_measurements_table(sample_child, tables)
        assert "Head Circ" in result

    def test_no_head_circumference_column_when_unavailable(
        self, partial_child, tables
    ):
        result = _build_measurements_table(partial_child, tables)
        assert "Head Circ" not in result

    def test_contains_bmi_column_when_available(self, sample_child, tables):
        result = _build_measurements_table(sample_child, tables)
        assert "BMI" in result

    def test_no_bmi_column_for_infant_only(self, infant_only_child, tables):
        result = _build_measurements_table(infant_only_child, tables)
        assert "BMI" not in result

    def test_contains_separator_row(self, sample_child, tables):
        result = _build_measurements_table(sample_child, tables)
        assert "|---|" in result

    def test_measurements_in_chronological_order(self, sample_child, tables):
        result = _build_measurements_table(sample_child, tables)
        jan_2020 = result.find("January 1, 2020")
        jan_2022 = result.find("January 1, 2022")
        assert jan_2020 < jan_2022

    def test_missing_values_show_dash(self, partial_child, tables):
        result = _build_measurements_table(partial_child, tables)
        assert "| - |" in result

    def test_no_string_splitting(self, sample_child, tables):
        """Verify no combined format strings appear — atomic formatters only."""
        result = _build_measurements_table(sample_child, tables)
        assert " ft " in result
        assert " in" in result
        assert " lb " in result

    def test_projected_heights_in_feet_inches_only(self, sample_child, tables):
        result = _build_measurements_table(sample_child, tables)
        assert "ft" in result


# ── generate_report tests ─────────────────────────────────────────────────────

class TestGenerateReport:

    def test_creates_report_file(self, sample_child, tables, tmp_path):
        path = generate_report(
            sample_child, tables,
            reports_dir=tmp_path / "reports",
            charts_dir=tmp_path / "charts",
        )
        assert path.exists()
        assert path.suffix == ".md"

    def test_report_filename_contains_child_name(self, sample_child, tables, tmp_path):
        path = generate_report(
            sample_child, tables,
            reports_dir=tmp_path / "reports",
            charts_dir=tmp_path / "charts",
        )
        assert "test_child" in path.name

    def test_report_contains_child_name(self, sample_child, tables, tmp_path):
        path = generate_report(
            sample_child, tables,
            reports_dir=tmp_path / "reports",
            charts_dir=tmp_path / "charts",
        )
        content = path.read_text()
        assert "Test Child" in content

    def test_report_contains_standard_sections(self, sample_child, tables, tmp_path):
        path = generate_report(
            sample_child, tables,
            reports_dir=tmp_path / "reports",
            charts_dir=tmp_path / "charts",
        )
        content = path.read_text()
        assert "## Summary" in content
        assert "## Height" in content
        assert "## Weight" in content
        assert "## Projected Adult Height Over Time" in content
        assert "## Measurements" in content

    def test_report_contains_head_circumference_section(
        self, sample_child, tables, tmp_path
    ):
        path = generate_report(
            sample_child, tables,
            reports_dir=tmp_path / "reports",
            charts_dir=tmp_path / "charts",
        )
        content = path.read_text()
        assert "## Head Circumference" in content

    def test_report_contains_bmi_section(self, sample_child, tables, tmp_path):
        path = generate_report(
            sample_child, tables,
            reports_dir=tmp_path / "reports",
            charts_dir=tmp_path / "charts",
        )
        content = path.read_text()
        assert "## BMI" in content

    def test_report_no_head_circumference_section_when_unavailable(
        self, partial_child, tables, tmp_path
    ):
        path = generate_report(
            partial_child, tables,
            reports_dir=tmp_path / "reports",
            charts_dir=tmp_path / "charts",
        )
        content = path.read_text()
        assert "## Head Circumference" not in content

    def test_report_does_not_contain_adult_projections_chart(
        self, sample_child, tables, tmp_path
    ):
        path = generate_report(
            sample_child, tables,
            reports_dir=tmp_path / "reports",
            charts_dir=tmp_path / "charts",
        )
        content = path.read_text()
        assert "test_child_adult_projection.png" not in content

    def test_report_contains_chart_image_links(self, sample_child, tables, tmp_path):
        path = generate_report(
            sample_child, tables,
            reports_dir=tmp_path / "reports",
            charts_dir=tmp_path / "charts",
        )
        content = path.read_text()
        assert "test_child_height.png" in content
        assert "test_child_weight.png" in content
        assert "test_child_projection_over_time.png" in content
        assert "test_child_head_circumference.png" in content
        assert "test_child_bmi.png" in content

    def test_report_title_is_centered(self, sample_child, tables, tmp_path):
        path = generate_report(
            sample_child, tables,
            reports_dir=tmp_path / "reports",
            charts_dir=tmp_path / "charts",
        )
        content = path.read_text()
        assert 'align="center"' in content

    def test_no_measurements_raises_error(self, tables, tmp_path):
        empty_child = Child(name="Empty", sex="M", dob=date(2020, 1, 1))
        with pytest.raises(ValueError, match="has no measurements"):
            generate_report(
                empty_child, tables,
                reports_dir=tmp_path / "reports",
                charts_dir=tmp_path / "charts",
            )

    def test_creates_reports_directory_if_missing(
        self, sample_child, tables, tmp_path
    ):
        new_reports_dir = tmp_path / "new_reports"
        assert not new_reports_dir.exists()
        generate_report(
            sample_child, tables,
            reports_dir=new_reports_dir,
            charts_dir=tmp_path / "charts",
        )
        assert new_reports_dir.exists()

    def test_partial_measurements_report_no_crash(
        self, partial_child, tables, tmp_path
    ):
        path = generate_report(
            partial_child, tables,
            reports_dir=tmp_path / "reports",
            charts_dir=tmp_path / "charts",
        )
        assert path.exists()