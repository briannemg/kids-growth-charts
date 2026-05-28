"""
test_plotting.py

Unit tests for chart generation functions.

These tests verify that charts are created without errors and return
the correct types. They do not assert visual appearance — that is
verified by inspecting the output charts manually.
"""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest
from datetime import date

from growth_charts.models import Child, Measurement
from growth_charts.percentiles import load_all_tables
from growth_charts.plotting import (
    _build_band_pairs,
    _build_reference_curves,
    plot_growth_chart,
    plot_head_circumference_chart,
    plot_bmi_chart,
    plot_projection_over_time,
    save_charts,
    PERCENTILE_BANDS,
    BMI_PERCENTILE_BANDS,
)

# Use non-interactive backend so tests don't open windows
matplotlib.use("Agg")


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
    """A child with only infant measurements (WHO range only)."""
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
            Measurement(date=date(2021, 1, 1),  age_months=0.0,
                        weight_kg=3.5),
            Measurement(date=date(2021, 7, 1),  age_months=6.0,
                        height_cm=66.0, weight_kg=7.8),
            Measurement(date=date(2022, 1, 1),  age_months=12.0,
                        height_cm=74.0),
            Measurement(date=date(2023, 1, 1),  age_months=24.0,
                        height_cm=86.0, weight_kg=11.5),
        ],
    )


# ── Band pair tests ───────────────────────────────────────────────────────────

class TestBuildBandPairs:

    def test_returns_correct_number_of_pairs(self):
        """7 bands should produce 6 adjacent pairs."""
        pairs = _build_band_pairs(PERCENTILE_BANDS)
        assert len(pairs) == len(PERCENTILE_BANDS) - 1

    def test_bmi_bands_returns_correct_number_of_pairs(self):
        """8 BMI bands should produce 7 adjacent pairs."""
        pairs = _build_band_pairs(BMI_PERCENTILE_BANDS)
        assert len(pairs) == len(BMI_PERCENTILE_BANDS) - 1

    def test_pairs_are_adjacent(self):
        pairs = _build_band_pairs(PERCENTILE_BANDS)
        sorted_bands = sorted(PERCENTILE_BANDS)
        for i, ((lo, hi), _) in enumerate(pairs):
            assert lo == sorted_bands[i]
            assert hi == sorted_bands[i + 1]

    def test_alphas_peak_in_center(self):
        pairs = _build_band_pairs(PERCENTILE_BANDS)
        alphas = [alpha for _, alpha in pairs]
        center = len(alphas) // 2
        assert alphas[center] >= alphas[0]
        assert alphas[center] >= alphas[-1]

    def test_all_alphas_in_valid_range(self):
        pairs = _build_band_pairs(PERCENTILE_BANDS)
        for _, alpha in pairs:
            assert 0 < alpha <= 1.0

    def test_single_pair_does_not_crash(self):
        pairs = _build_band_pairs([10, 90])
        assert len(pairs) == 1


# ── Reference curve tests ─────────────────────────────────────────────────────

class TestBuildReferenceCurves:

    def test_returns_all_percentile_bands(self, tables):
        curves = _build_reference_curves("M", "height", tables, (0.0, 60.0))
        assert set(curves.keys()) == {5, 10, 25, 50, 75, 90, 95}

    def test_bmi_returns_bmi_percentile_bands(self, tables):
        curves = _build_reference_curves(
            "M", "bmi", tables, (24.0, 120.0),
            percentile_bands=BMI_PERCENTILE_BANDS
        )
        assert set(curves.keys()) == {5, 10, 25, 50, 75, 85, 90, 95}

    def test_head_circumference_curves_built(self, tables):
        curves = _build_reference_curves(
            "M", "head_circumference", tables, (0.0, 36.0)
        )
        assert set(curves.keys()) == {5, 10, 25, 50, 75, 90, 95}

    def test_curves_have_matching_array_lengths(self, tables):
        curves = _build_reference_curves("M", "height", tables, (24.0, 120.0))
        for pct, (ages, values) in curves.items():
            assert len(ages) == len(values)

    def test_higher_percentile_yields_larger_values(self, tables):
        curves = _build_reference_curves("M", "height", tables, (24.0, 60.0))
        p5_values = curves[5][1]
        p95_values = curves[95][1]
        assert all(
            p95 > p5
            for p95, p5 in zip(p95_values, p5_values)
            if not (np.isnan(p95) or np.isnan(p5))
        )

    def test_female_curves_shorter_than_male(self, tables):
        male_curves = _build_reference_curves("M", "height", tables, (60.0, 120.0))
        female_curves = _build_reference_curves("F", "height", tables, (60.0, 120.0))
        male_median = male_curves[50][1]
        female_median = female_curves[50][1]
        assert all(
            m > f
            for m, f in zip(male_median, female_median)
            if not (np.isnan(m) or np.isnan(f))
        )


# ── Growth chart tests ────────────────────────────────────────────────────────

class TestPlotGrowthChart:

    def test_returns_figure(self, sample_child, tables):
        from matplotlib.figure import Figure
        fig = plot_growth_chart(sample_child, "height", tables)
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_weight_chart_returns_figure(self, sample_child, tables):
        from matplotlib.figure import Figure
        fig = plot_growth_chart(sample_child, "weight", tables)
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_infant_only_chart_returns_figure(self, infant_only_child, tables):
        from matplotlib.figure import Figure
        fig = plot_growth_chart(infant_only_child, "height", tables)
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_invalid_measure_raises_error(self, sample_child, tables):
        with pytest.raises(ValueError, match="measure must be 'height' or 'weight'"):
            plot_growth_chart(sample_child, "bmi", tables)

    def test_no_height_measurements_raises_error(self, tables):
        weight_only = Child(
            name="WeightOnly", sex="M", dob=date(2020, 1, 1),
            measurements=[
                Measurement(date=date(2021, 1, 1), age_months=12.0,
                            weight_kg=9.5),
            ],
        )
        with pytest.raises(ValueError, match="no height measurements"):
            plot_growth_chart(weight_only, "height", tables)

    def test_partial_measurements_plots_available_data(self, partial_child, tables):
        """Should plot without error even when some measurements lack height."""
        from matplotlib.figure import Figure
        fig = plot_growth_chart(partial_child, "height", tables)
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_chart_has_correct_title(self, sample_child, tables):
        fig = plot_growth_chart(sample_child, "height", tables)
        title = fig.axes[0].get_title()
        assert "Test Child" in title
        assert "Height" in title
        plt.close(fig)

    def test_female_chart_title_says_girls(self, infant_only_child, tables):
        fig = plot_growth_chart(infant_only_child, "height", tables)
        title = fig.axes[0].get_title()
        assert "Girls" in title
        plt.close(fig)

    def test_chart_has_no_legend(self, sample_child, tables):
        fig = plot_growth_chart(sample_child, "height", tables)
        legend = fig.axes[0].get_legend()
        assert legend is None
        plt.close(fig)

    def test_single_measurement_respects_min_age_range(self, tables):
        from growth_charts.plotting import MIN_AGE_RANGE_MONTHS
        newborn = Child(
            name="Newborn", sex="M", dob=date(2025, 1, 1),
            measurements=[
                Measurement(date=date(2025, 1, 1), age_months=0.0,
                            height_cm=50.0, weight_kg=3.4),
            ],
        )
        fig = plot_growth_chart(newborn, "height", tables)
        ax = fig.axes[0]
        x_min, x_max = ax.get_xlim()
        assert (x_max - x_min) >= MIN_AGE_RANGE_MONTHS
        plt.close(fig)


# ── Head circumference chart tests ────────────────────────────────────────────

class TestPlotHeadCircumferenceChart:

    def test_returns_figure(self, sample_child, tables):
        from matplotlib.figure import Figure
        fig = plot_head_circumference_chart(sample_child, tables)
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_infant_only_returns_figure(self, infant_only_child, tables):
        from matplotlib.figure import Figure
        fig = plot_head_circumference_chart(infant_only_child, tables)
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_no_head_circumference_raises_error(self, tables):
        no_hc = Child(
            name="NoHC", sex="M", dob=date(2020, 1, 1),
            measurements=[
                Measurement(date=date(2021, 1, 1), age_months=12.0,
                            height_cm=75.0, weight_kg=9.5),
            ],
        )
        with pytest.raises(ValueError, match="no head circumference measurements"):
            plot_head_circumference_chart(no_hc, tables)

    def test_measurements_beyond_36_months_raises_error(self, tables):
        """A child with only post-36-month measurements should raise an error."""
        old_child = Child(
            name="Old", sex="M", dob=date(2018, 1, 1),
            measurements=[
                Measurement(date=date(2021, 1, 1), age_months=36.1,
                            head_circumference_cm=50.0),
            ],
        )
        with pytest.raises(ValueError, match="no head circumference measurements"):
            plot_head_circumference_chart(old_child, tables)

    def test_chart_title_contains_child_name(self, sample_child, tables):
        fig = plot_head_circumference_chart(sample_child, tables)
        title = fig.axes[0].get_title()
        assert "Test Child" in title
        assert "Head Circumference" in title
        plt.close(fig)

    def test_female_chart_title_says_girls(self, infant_only_child, tables):
        fig = plot_head_circumference_chart(infant_only_child, tables)
        title = fig.axes[0].get_title()
        assert "Girls" in title
        plt.close(fig)


# ── BMI chart tests ───────────────────────────────────────────────────────────

class TestPlotBMIChart:

    def test_returns_figure(self, sample_child, tables):
        from matplotlib.figure import Figure
        fig = plot_bmi_chart(sample_child, tables)
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_no_bmi_data_raises_error(self, tables):
        no_bmi = Child(
            name="NoBMI", sex="M", dob=date(2020, 1, 1),
            measurements=[
                Measurement(date=date(2021, 1, 1), age_months=12.0,
                            height_cm=75.0),
            ],
        )
        with pytest.raises(ValueError, match="no BMI data"):
            plot_bmi_chart(no_bmi, tables)

    def test_bmi_under_24_months_raises_error(self, tables):
        """BMI chart requires data at 24+ months."""
        infant = Child(
            name="Infant", sex="M", dob=date(2023, 1, 1),
            measurements=[
                Measurement(date=date(2023, 7, 1), age_months=6.0,
                            height_cm=67.0, weight_kg=7.5),
            ],
        )
        with pytest.raises(ValueError, match="no BMI data"):
            plot_bmi_chart(infant, tables)

    def test_chart_title_contains_child_name(self, sample_child, tables):
        fig = plot_bmi_chart(sample_child, tables)
        title = fig.axes[0].get_title()
        assert "Test Child" in title
        assert "BMI" in title
        plt.close(fig)

    def test_chart_has_legend_with_clinical_thresholds(self, sample_child, tables):
        """BMI chart should have a legend showing overweight and obese thresholds."""
        fig = plot_bmi_chart(sample_child, tables)
        legend = fig.axes[0].get_legend()
        assert legend is not None
        legend_texts = [t.get_text() for t in legend.get_texts()]
        assert any("Overweight" in t for t in legend_texts)
        assert any("Obese" in t for t in legend_texts)
        plt.close(fig)

    def test_female_chart_title_says_girls(self, tables):
        girl = Child(
            name="Girl", sex="F", dob=date(2020, 1, 1),
            measurements=[
                Measurement(date=date(2022, 1, 1), age_months=24.0,
                            height_cm=86.0, weight_kg=11.5),
                Measurement(date=date(2023, 1, 1), age_months=36.0,
                            height_cm=95.0, weight_kg=14.0),
            ],
        )
        fig = plot_bmi_chart(girl, tables)
        title = fig.axes[0].get_title()
        assert "Girls" in title
        plt.close(fig)


# ── Projection over time chart tests ──────────────────────────────────────────

class TestPlotProjectionOverTime:

    def test_returns_figure(self, sample_child, tables):
        from matplotlib.figure import Figure
        fig = plot_projection_over_time(sample_child, tables)
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_returns_figure_with_parental_heights(self, sample_child, tables):
        from matplotlib.figure import Figure
        fig = plot_projection_over_time(
            sample_child, tables, father_cm=180.0, mother_cm=165.0
        )
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_no_height_measurements_raises_error(self, tables):
        weight_only = Child(
            name="WeightOnly", sex="M", dob=date(2020, 1, 1),
            measurements=[
                Measurement(date=date(2021, 1, 1), age_months=12.0,
                            weight_kg=9.5),
            ],
        )
        with pytest.raises(ValueError, match="no height measurements"):
            plot_projection_over_time(weight_only, tables)

    def test_chart_title_contains_child_name(self, sample_child, tables):
        fig = plot_projection_over_time(sample_child, tables)
        title = fig.axes[0].get_title()
        assert "Test Child" in title
        plt.close(fig)

    def test_y_axis_is_zoomed(self, sample_child, tables):
        fig = plot_projection_over_time(sample_child, tables)
        ax = fig.axes[0]
        y_min, _ = ax.get_ylim()
        assert y_min > 0
        plt.close(fig)

    def test_female_chart_title_says_girls(self, infant_only_child, tables):
        fig = plot_projection_over_time(infant_only_child, tables)
        title = fig.axes[0].get_title()
        assert "Girls" in title
        plt.close(fig)


# ── Save charts tests ─────────────────────────────────────────────────────────

class TestSaveCharts:

    def test_saves_all_charts_for_full_data(self, sample_child, tables, tmp_path):
        """Child with height, weight, head circumference, and BMI data
        should produce 5 charts."""
        saved = save_charts(sample_child, tables, output_dir=tmp_path)
        assert len(saved) == 5
        for path in saved:
            assert path.exists()
            assert path.suffix == ".png"

    def test_saves_only_available_charts(self, tables, tmp_path):
        """Child with weight-only data should only produce a weight chart."""
        weight_only = Child(
            name="WeightOnly", sex="M", dob=date(2020, 1, 1),
            measurements=[
                Measurement(date=date(2021, 1, 1), age_months=12.0,
                            weight_kg=9.5),
                Measurement(date=date(2022, 1, 1), age_months=24.0,
                            weight_kg=12.0),
            ],
        )
        saved = save_charts(weight_only, tables, output_dir=tmp_path)
        filenames = [p.name for p in saved]
        assert any("weight" in f for f in filenames)
        assert not any("height" in f for f in filenames)
        assert not any("bmi" in f for f in filenames)
        assert not any("head_circumference" in f for f in filenames)
        assert not any("projection" in f for f in filenames)

    def test_saved_filenames_contain_child_name(self, sample_child, tables, tmp_path):
        saved = save_charts(sample_child, tables, output_dir=tmp_path)
        for path in saved:
            assert "test_child" in path.name

    def test_creates_output_directory_if_missing(self, sample_child, tables, tmp_path):
        new_dir = tmp_path / "new_subdir"
        assert not new_dir.exists()
        save_charts(sample_child, tables, output_dir=new_dir)
        assert new_dir.exists()

    def test_head_circumference_chart_not_saved_beyond_36_months(
        self, tables, tmp_path
    ):
        """Head circumference chart should not be saved if all HC measurements
        are beyond 36 months."""
        old_child = Child(
            name="Old", sex="M", dob=date(2018, 1, 1),
            measurements=[
                Measurement(date=date(2021, 4, 1), age_months=39.0,
                            height_cm=100.0, weight_kg=15.0,
                            head_circumference_cm=50.0),
            ],
        )
        saved = save_charts(old_child, tables, output_dir=tmp_path)
        filenames = [p.name for p in saved]
        assert not any("head_circumference" in f for f in filenames)