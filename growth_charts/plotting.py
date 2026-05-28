"""
plotting.py

Chart generation for child growth data.

Produces the following chart types per child:
  1. Height-for-age - CDC/WHO reference curves, child's measurements as dots
  2. Weight-for-age - CDC/WHO reference curves, child's measurements as dots
  3. Head circumference-for-age - WHO 0-24 mo, CDC 24-36 mo (if data exists)
  4. BMI-for-age - CDC 2-20 years with clinical threshold lines (if data exists)
  5. Projected adult height over time - percentile projection at each measurement

All growth charts use gray reference percentile bands matching CDC aesthetics.
BMI charts use the same gray bands but add colored clinical threshold lines
at the 85th (overweight) and 95th (obese) percentiles.

Band shading and alpha values are derived automatically from PERCENTILE_BANDS
so that adding or removing percentiles requires no manual updates to the
chart code.

Measurements with missing height or weight are silently skipped on the
relevant charts - measurement without height is skipped on the height
chart but still appears on the weight chart is weight is present.
"""

import math
from pathlib import Path
from typing import Any, cast

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from scipy.interpolate import interp1d

from growth_charts.models import Child
from growth_charts.percentiles import WHO_CDC_CUTOFF
from growth_charts.units import (
    cm_to_inches,
    kg_to_lbs,
    format_feet_inches,
)


# ── Constants ─────────────────────────────────────────────────────────────────

# Percentile bands for height, weight, and head circumference charts
PERCENTILE_BANDS = [5, 10, 25, 50, 75, 90, 95]

# BMI percentile bands - includes 85th for clinical overweight threshold
BMI_PERCENTILE_BANDS = [5, 10, 25, 50, 75, 85, 90, 95]

# Minimum age range to display on growth charts (months).
MIN_AGE_RANGE_MONTHS = 12

# Maximum age for head circumference charts (months)
HC_MAX_AGE_MONTHS = 36.0

# Gray shades for growth chart reference lines
COLOR_BAND_FILL_GRAY = "#f0f0f0"
COLOR_BAND_LINE_GRAY = "#aaaaaa"
COLOR_MEDIAN_GRAY = "#666666"

# Colors for child measurement dots and projection charts
COLOR_MEASUREMENT = "#d7191c"
COLOR_PROJECTION = "#756bb1"
COLOR_MEDIAN = "#2c7bb6"
COLOR_WHO_CDC_LINE = "#cccccc"

# BMI clinical threshold colors
COLOR_BMI_OVERWEIGHT = "#f4a322"   # amber - 85th percentile
COLOR_BMI_OBESE = "#d7191c"        # red - 95th percentile

# Chart figure size
FIGURE_SIZE = (12, 7)

# Output directory for saved charts
DEFAULT_OUTPUT_DIR = Path("output/charts")


# ── Band pair helpers ─────────────────────────────────────────────────────────

def _build_band_pairs(
    percentile_bands: list[int],
) -> list[tuple[tuple[int, int], float]]:
    """
    Derive shaded band pairs and alpha values from a list of percentile bands.

    Sorts the bands, zips adjacent pairs, and assigns alpha values that
    taper from strongest in the center outward to the edges. This means
    adding or removing percentiles from PERCENTILE_BANDS automatically
    updates the shading without any manual changes.

    Args:
        percentile_bands (list[int]): Sorted or unsorted list of percentiles
                                      to draw on the chart.

    Returns:
        list[tuple[tuple[int, int], float]]: List of ((low, high), alpha)
                                             pairs for fill_between calls.
    """
    sorted_bands = sorted(percentile_bands)
    pairs = list(zip(sorted_bands, sorted_bands[1:]))
    n = len(pairs)

    alphas = []
    for i in range(n):
        # Distance from center as a fraction (0.0 = center, 1.0 = edge)
        distance_from_center = abs(i - (n - 1) / 2) / ((n - 1) / 2) if n > 1 else 0
        alpha = 0.30 - (0.15 * distance_from_center)
        alphas.append(round(alpha, 3))

    return list(zip(pairs, alphas))


# ── Reference curve helpers ───────────────────────────────────────────────────

def _build_reference_curves(
    sex: str,
    measure: str,
    tables: dict,
    age_range_months: tuple[float, float],
    percentile_bands: list[int] | None = None,
) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    """
    Build reference percentile curves across an age range using LMS tables.

    Generates smooth age points across the range and computes the height or
    weight value at each percentile for each age point. Uses linear
    interpolation between adjacent LMS table rows for smooth curves rather
    than snapping to the nearest row, which causes visible step artifacts.

    Args:
        sex (str): 'M' for male or 'F' for female.
        measure (str): 'height', 'weight', 'head_circumference', or 'bmi'.
        tables (dict): The loaded LMS tables from load_all_tables().
        age_range_months (tuple[float, float]): (min_age, max_age) in months.
        percentile_bands (list[int] | None): Percentile bands to compute.
                                             Defaults to PERCENTILE_BANDS.

    Returns:
        dict[int, tuple[np.ndarray, np.ndarray]]: Mapping of percentile to
            (ages_array, values_array) for plotting.
    """
    from scipy.stats import norm
    from growth_charts.percentiles import CDC_MALE
    
    if percentile_bands is None:
        percentile_bands = PERCENTILE_BANDS

    min_age, max_age = age_range_months
    ages = np.linspace(min_age, max_age, 300)
    curves: dict[int, tuple[np.ndarray, np.ndarray]] = {}

    # Pre-build interpolators for L, M, S for each source/sex combination
    # so we interpolate smoothly rather than snapping to nearest row
    def _build_interpolators(df, age_col: str = "agemos") -> dict[str, Any]:
        """Build cubic interpolators for L, M, S columns from a dataframe."""
        df_sorted = df.sort_values(age_col)
        age_vals = df_sorted[age_col].values
        return {
            "L": interp1d(age_vals, df_sorted["l"].values,
                         kind="linear", fill_value=cast(float, "extrapolate")),
            "M": interp1d(age_vals, df_sorted["m"].values,
                         kind="linear", fill_value=cast(float, "extrapolate")),
            "S": interp1d(age_vals, df_sorted["s"].values,
                         kind="linear", fill_value=cast(float, "extrapolate")),
        }
        
    # Build interpolators for the appropriate tables
    sex_code = CDC_MALE if sex == "M" else 2
    
    if measure == "bmi":
        cdc_df = tables["cdc"]["bmi"]
        cdc_interp = _build_interpolators(cdc_df[cdc_df["sex"] == sex_code])
        who_interp = None
    elif measure == "head_circumference":
        cdc_df = tables["cdc"]["head_circumference"]
        cdc_interp = _build_interpolators(cdc_df[cdc_df["sex"] == sex_code])
        who_interp = _build_interpolators(
            tables["who"]["head_circumference"][sex]
        )
    else:
        cdc_key = "height" if measure == "height" else "weight"
        cdc_df = tables["cdc"][cdc_key]
        cdc_interp = _build_interpolators(cdc_df[cdc_df["sex"] == sex_code])
        who_interp = _build_interpolators(tables["who"][measure][sex])

    for pct in percentile_bands:
        z = float(norm.ppf(pct / 100))
        values = []

        for age in ages:
            if measure == "bmi":
                interp = cdc_interp
            elif age < WHO_CDC_CUTOFF and who_interp is not None:
                interp = who_interp
            else:
                interp = cdc_interp
                
            L = float(interp["L"](age))
            m = float(interp["M"](age))
            s = float(interp["S"](age))

            if L != 0:
                val = m * ((1 + L * s * z) ** (1 / L))
            else:
                val = m * math.exp(s * z)
            values.append(val)

        curves[pct] = (ages, np.array(values))

    return curves


# ── Secondary axis formatters ─────────────────────────────────────────────────

def _add_height_secondary_axis(ax: Axes, label: str = "Height (in)") -> None:
    """
    Add a secondary y-axis showing height in decimal inches.

    Args:
        ax (Axes): The primary matplotlib axes with cm on the y-axis.
        label (str): The y-axis label. Defaults to "Height (in)".
    """
    ax2 = ax.twinx()
    y_min, y_max = ax.get_ylim()
    ax2.set_ylim(y_min, y_max)

    cm_ticks = ax.get_yticks()
    cm_ticks = [t for t in cm_ticks if y_min <= t <= y_max]
    labels = []
    for cm in cm_ticks:
        if cm > 0:
            labels.append(f"{cm_to_inches(cm)} in")
        else:
            labels.append("")
    ax2.set_yticks(cm_ticks)
    ax2.set_yticklabels(labels, fontsize=8)
    ax2.set_ylabel(label, fontsize=9)


def _add_weight_secondary_axis(ax: Axes) -> None:
    """
    Add a secondary y-axis showing weight in decimal pounds.

    Args:
        ax (Axes): The primary matplotlib axes with kg on the y-axis.
    """
    ax2 = ax.twinx()
    y_min, y_max = ax.get_ylim()
    ax2.set_ylim(y_min, y_max)

    kg_ticks = ax.get_yticks()
    kg_ticks = [t for t in kg_ticks if y_min <= t <= y_max]
    labels = []
    for kg in kg_ticks:
        if kg > 0:
            labels.append(f"{kg_to_lbs(kg)} lb")
        else:
            labels.append("")
    ax2.set_yticks(kg_ticks)
    ax2.set_yticklabels(labels, fontsize=8)
    ax2.set_ylabel("Weight (lb)", fontsize=9)
    
    
def _add_age_secondary_x_axis(ax: Axes, age_min: float, age_max: float) -> None:
    """
    Add a secondary x-axis showing age in years along the top of the chart.

    Args:
        ax (Axes): The primary matplotlib axes with age in months on x-axis.
        age_min (float): Minimum age in months displayed on the chart.
        age_max (float): Maximum age in months displayed on the chart.
    """
    ax2 = ax.twiny()
    ax2.set_xlim(age_min / 12, age_max / 12)
    
    # Place year ticks at whole year boundaries
    year_min = math.ceil(age_min / 12)
    year_max = math.floor(age_max / 12)
    year_ticks = list(range(year_min, year_max + 1))
    ax2.set_xticks(year_ticks)
    ax2.set_xticklabels([str(y) for y in year_ticks], fontsize=8)
    ax2.set_xlabel("Age (years)", fontsize=9)


# ── Shared chart helpers ──────────────────────────────────────────────────────

def _plot_reference_bands_and_lines(
    ax: Axes,
    curves: dict[int, tuple[np.ndarray, np.ndarray]],
    band_pairs: list[tuple[tuple[int, int], float]],
    clinical_bands: dict[int, str] | None = None,
) -> None:
    """
    Draw shaded percentile bands and reference lines on a chart axes.
    
    Standard bands are drawn in gray. Clinical threshold bands (for BMI)
    are drawn in their designated colors with labels.

    Args:
        ax (Axes): The matplotlib axes to draw on.
        curves (dict[int, tuple[np.ndarray, np.ndarray]]): Percentile curves from
                                                           _build_reference_curves().
        band_pairs (list[tuple[tuple[int, int], float]]): Band pairs from
                                                          _build_band_pairs().
        clinical_bands (dict[int, str] | None, optional): Mapping of percentile to color for
                                                          clinical threshold lines. If None,
                                                          all lines are drawn in gray.
                                                          Defaults to None.
    """
    # Shaded bands
    for (lo, hi), alpha in band_pairs:
        ax.fill_between(
            curves[lo][0],
            curves[lo][1],
            curves[hi][1],
            alpha=alpha,
            color=COLOR_BAND_FILL_GRAY,
            linewidth=0,
        )
        
    # Percentile reference lines
    for pct, (pct_ages, pct_values) in curves.items():
        # Use clinical color if this is a threshold percentile
        if clinical_bands and pct in clinical_bands:
            color = clinical_bands[pct]
            lw = 2.0
            ls = "--"
        else:
            color = COLOR_MEDIAN_GRAY if pct == 50 else COLOR_BAND_LINE_GRAY
            lw = 1.5 if pct == 50 else 0.8
            ls = "--" if pct == 50 else "-"
            
        ax.plot(pct_ages, pct_values, color=color, linewidth=lw, linestyle=ls)
        
        # Label at the right end of each curve
        valid = ~np.isnan(pct_values)
        if valid.any():
            label_color = clinical_bands[pct] if (
                clinical_bands and pct in clinical_bands
            ) else COLOR_BAND_LINE_GRAY
            ax.annotate(
                f"{pct}th",
                xy=(pct_ages[valid][-1], pct_values[valid][-1]),
                xytext=(4, 0),
                textcoords="offset points",
                fontsize=7,
                color=label_color,
                va="center",
                fontweight="bold" if (
                    clinical_bands and pct in clinical_bands
                ) else "normal"
            )
            

def _add_who_cdc_transition_line(
    ax: Axes,
    age_min: float,
    age_max: float,
) -> None:
    """
    Draw a subtle vertical line at the WHO-to-CDC transition at 24 months,
    if the chart's age range spans that boundary.

    Args:
        ax (Axes): The matplotlib axes to draw on.
        age_min (float): Minimum age in months displayed on the chart.
        age_max (float): Maximum age in months displayed on the chart.
    """
    if age_min < WHO_CDC_CUTOFF < age_max:
        ax.axvline(
            WHO_CDC_CUTOFF,
            color=COLOR_WHO_CDC_LINE,
            linewidth=1.0,
            linestyle=":",
        )
        ax.text(
            WHO_CDC_CUTOFF + 0.5,
            ax.get_ylim()[0],
            "WHO ← | → CDC",
            fontsize=7,
            color=COLOR_WHO_CDC_LINE,
            va="bottom",
        )


# ── Growth chart ──────────────────────────────────────────────────────────────

def plot_growth_chart(
    child: Child,
    measure: str,
    tables: dict,
) -> Figure:
    """
    Plot a height-for-age or weight-for-age growth chart for a single child.
    
    Styled to match CDC aesthetics:
      - Smooth gray percentile reference curves with shaded bands
      - Child's measurements as plain dots (no connecting lines)
      - Measurements missing the relevant value are silently skipped
      - No annotations on data points
      - No legend
      - Twin x-axis showing age in years along the top
      - Right y-axis in decimal inches (height) or decimal pounds (weight)
      - Subtle vertical line at the WHO-to-CDC transition at 24 months
      
    The displayed age range is always at least MIN_AGE_RANGE_MONTHS wide
    to prevent overly narrow charts for children with few measurements.

    Args:
        child (Child): The child to plot.
        measure (str): 'height' or 'weight'.
        tables (dict): The loaded LMS tables from load_all_tables().

    Returns:
        Figure: The completed matplotlib figure.

    Raises:
        ValueError: If measure is not 'height' or 'weight'.
        ValueError: If the child has no measurements.
    """
    if measure not in ("height", "weight"):
        raise ValueError("measure must be 'height' or 'weight'")
    
    # Filter to measurements that have the requested value
    sorted_measurements = sorted(child.measurements, key=lambda m: m.date)
    if measure == "height":
        valid_measurements = [m for m in sorted_measurements
                              if m.height_cm is not None]
    else:
        valid_measurements = [m for m in sorted_measurements
                              if m.weight_kg is not None]
        
    if not valid_measurements:
        raise ValueError(
            f"Child '{child.name}' has no {measure} measurements"
        )

    ages = [m.age_months for m in valid_measurements]
    values: list[float] = [
        m.height_cm for m in valid_measurements if m.height_cm is not None
    ] if measure == "height" else [
        m.weight_kg for m in valid_measurements if m.weight_kg is not None
    ]

    # ── Age range ─────────────────────────────────────────────────────────────
    padding = max(3.0, (max(ages) - min(ages)) * 0.05)
    age_min = max(0.0, min(ages) - padding)
    age_max = min(
        240.0,
        max(max(ages) + padding, min(ages) + MIN_AGE_RANGE_MONTHS),
    )

    # ── Build reference curves and band pairs ─────────────────────────────────
    curves = _build_reference_curves(
        child.sex, measure, tables, (age_min, age_max)
    )
    band_pairs = _build_band_pairs(PERCENTILE_BANDS)

    # ── Plot ──────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)

    _plot_reference_bands_and_lines(ax, curves, band_pairs)
    _add_who_cdc_transition_line(ax, age_min, age_max)

    ax.plot(
        ages, values, "o",
        color=COLOR_MEASUREMENT,
        markersize=6,
        zorder=5,
    )

    # ── Labels and formatting ─────────────────────────────────────────────────
    measure_label = "Height" if measure == "height" else "Weight"
    unit_label = "cm" if measure == "height" else "kg"
    sex_label = "Boys" if child.sex == "M" else "Girls"

    ax.set_title(
        f"{child.name} — {measure_label}-for-Age ({sex_label})",
        fontsize=14,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Age (months)", fontsize=11)
    ax.set_ylabel(f"{measure_label} ({unit_label})", fontsize=11)
    ax.grid(True, alpha=0.3, linewidth=0.5)
    ax.set_xlim(age_min, age_max + 6)  # extra room for percentile labels

    # Secondary axis with US units
    if measure == "height":
        _add_height_secondary_axis(ax)
    else:
        _add_weight_secondary_axis(ax)
    _add_age_secondary_x_axis(ax, age_min, age_max + 6)

    fig.tight_layout()
    return fig


# ── Head circumference chart ──────────────────────────────────────────────────

def plot_head_circumference_chart(
    child: Child,
    tables: dict,
) -> Figure:
    """
    Plot a head circumference-for-age chart for a single child.
    
    Uses WHO reference data for ages 0-24 months and CDC data for
    24-36 months. Measurements beyong 36 months are not plotted since
    no reference data is available.
    
    Styled to match CDC chart aesthetics:
      - Smooth gray percentile reference curves with shaded bands
      - Child's measurements as plain dots
      - No annotations, no legend
      - Twin x-axis showing age in years
      - Right y-axis in decimal inches

    Args:
        child (Child): The child to plot.
        tables (dict): The loaded LMS tables from load_all_tables().

    Returns:
        Figure: The completed matplotlib figure.
    
    Raises:
        ValueError: If the child has no head circumference measurements
                    within the 0-36 month range.
    """
    sorted_measurements = sorted(child.measurements, key=lambda m: m.date)
    valid_measurements = [
        m for m in sorted_measurements
        if m.head_circumference_cm is not None
        and m.age_months <= HC_MAX_AGE_MONTHS
    ]
    
    if not valid_measurements:
        raise ValueError(
            f"Child '{child.name}' has no head circumference measurements "
            "within the 0-36 month range"
        )
        
    ages = [m.age_months for m in valid_measurements]
    values: list[float] = [
        m.head_circumference_cm for m in valid_measurements
        if m.head_circumference_cm if not None
    ]
    
    # ── Age range ─────────────────────────────────────────────────────────────
    padding = max(2.0, (max(ages) - min(ages)) * 0.05)
    age_min = max(0.0, min(ages) - padding)
    age_max = min(
        HC_MAX_AGE_MONTHS,
        max(max(ages) + padding, min(ages) + MIN_AGE_RANGE_MONTHS),
    )
    
    curves = _build_reference_curves(
        child.sex, "head_circumference", tables, (age_min, age_max)
    )
    band_pairs = _build_band_pairs(PERCENTILE_BANDS)
    
    # ── Plot ──────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    
    _plot_reference_bands_and_lines(ax, curves, band_pairs)
    _add_who_cdc_transition_line(ax, age_min, age_max)
    
    ax.plot(
        ages, values, "o",
        color=COLOR_MEASUREMENT,
        markersize=6,
        zorder=5,
    )
    
    # ── Labels and formatting ─────────────────────────────────────────────────
    sex_label = "Boys" if child.sex == "M" else "Girls"

    ax.set_title(
        f"{child.name} — Head Circumference-for-Age ({sex_label})",
        fontsize=14,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Age (months)", fontsize=11)
    ax.set_ylabel("Head Circumference (cm)", fontsize=11)
    ax.grid(True, alpha=0.3, linewidth=0.5)
    ax.set_xlim(age_min, age_max + 3)

    _add_height_secondary_axis(ax, label="Head Circumference (in)")
    _add_age_secondary_x_axis(ax, age_min, age_max + 3)

    fig.tight_layout()
    return fig


# ── BMI chart ─────────────────────────────────────────────────────────────────

def plot_bmi_chart(
    child: Child,
    tables: dict,
) -> Figure:
    """
    Plot a BMI-for-age chart for a single child.

    Uses CDC reference data for ages 24–240 months. BMI is calculated
    automatically from height and weight measurements.

    Clinical threshold lines are drawn in color:
      - 85th percentile (amber) — overweight threshold
      - 95th percentile (red)   — obese threshold

    All other percentile lines are drawn in gray matching CDC chart aesthetics.
    No secondary y-axis since BMI is unitless.

    Args:
        child (Child): The child to plot.
        tables (dict): The loaded LMS tables from load_all_tables().

    Returns:
        Figure: The completed matplotlib figure.

    Raises:
        ValueError: If the child has no BMI measurements at 24+ months.
    """
    sorted_measurements = sorted(child.measurements, key=lambda m: m.date)
    valid_measurements = [
        m for m in sorted_measurements
        if m.bmi is not None and m.age_months >= WHO_CDC_CUTOFF
    ]

    if not valid_measurements:
        raise ValueError(
            f"Child '{child.name}' has no BMI data available at 24+ months. "
            f"Both height and weight are required to calculate BMI."
        )

    ages = [m.age_months for m in valid_measurements]
    values: list[float] = [m.bmi for m in valid_measurements if m.bmi is not None]

    # ── Age range ─────────────────────────────────────────────────────────────
    padding = max(3.0, (max(ages) - min(ages)) * 0.05)
    age_min = max(WHO_CDC_CUTOFF, min(ages) - padding)
    age_max = min(240.0, max(max(ages) + padding, min(ages) + MIN_AGE_RANGE_MONTHS))

    curves = _build_reference_curves(
        child.sex, "bmi", tables, (age_min, age_max),
        percentile_bands=BMI_PERCENTILE_BANDS,
    )
    band_pairs = _build_band_pairs(BMI_PERCENTILE_BANDS)
    
    # Clinical threshold colors for 85th and 95th percentiles
    clinical_bands = {
        85: COLOR_BMI_OVERWEIGHT,
        95: COLOR_BMI_OBESE,
    }

    # ── Plot ──────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)

    _plot_reference_bands_and_lines(ax, curves, band_pairs, clinical_bands)

    ax.plot(
        ages, values, "o",
        color=COLOR_MEASUREMENT,
        markersize=6,
        zorder=5,
    )

    # ── Clinical threshold legend ─────────────────────────────────────────────
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color=COLOR_BMI_OVERWEIGHT, linewidth=2,
               linestyle="--", label="85th — Overweight threshold"),
        Line2D([0], [0], color=COLOR_BMI_OBESE, linewidth=2,
               linestyle="--", label="95th — Obese threshold"),
    ]
    ax.legend(handles=legend_elements, fontsize=9, loc="upper right")

    # ── Labels and formatting ─────────────────────────────────────────────────
    sex_label = "Boys" if child.sex == "M" else "Girls"

    ax.set_title(
        f"{child.name} — BMI-for-Age ({sex_label})",
        fontsize=14,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Age (months)", fontsize=11)
    ax.set_ylabel("BMI (kg/m²)", fontsize=11)
    ax.grid(True, alpha=0.3, linewidth=0.5)
    ax.set_xlim(age_min, age_max + 6)

    _add_age_secondary_x_axis(ax, age_min, age_max + 6)

    fig.tight_layout()
    return fig


# ── Projected adult height over time chart ────────────────────────────────────

def plot_projection_over_time(
    child: Child,
    tables: dict,
    father_cm: float | None = None,
    mother_cm: float | None = None,
) -> Figure:
    """
    Plot how the projected adult height changes across all measurements.
    
    Draws a line connecting the percentile-based adult height projection
    at each measurement point, showing how the projection stabilizes over
    time as more data becomes available.
    
    Optional reference lines are drawn when parental heights are provided:
      - A horizontal dashed line for the mid-parental height (MPH) target
      - A shaded band for the MPH range (± 8.5 cm)
      
    A horizontal dotted line is drawn for the doubling method result if
    a measurement near the reference age exists.
    
    The Y axis is zoomed to the realistic range of projections rather
    than starting at zero, making trends easier to read.
    
    Annotations show projected heights in feet and inches only.

    Args:
        child (Child): The child to plot projections for.
        tables (dict): The loaded LMS tables from load_all_tables().
        father_cm (float | None, optional): Father's height in cm. Required
                                            for MPH line. Defaults to None.
        mother_cm (float | None, optional): Mother's height in cm. Required
                                            for MPH line. Defaults to None.

    Returns:
        Figure: The completed matplotlib figure.
        
    Raises:
        ValueError: If the child has no measurements.
    """
    if not any(m.height_cm is not None for m in child.measurements):
        raise ValueError(
            f"Child '{child.name}' has no height measurements for projection"
        )
    
    from growth_charts.adult_height import (
        project_adult_height_from_current,
        project_adult_height_doubling,
        mid_parental_height,
        mid_parental_height_range,
        is_near_doubling_age,
        doubling_method_age,
    )
    
    # ── Build projection series ───────────────────────────────────────────────
    sorted_measurements = sorted(child.measurements, key=lambda m: m.date)
    ages = []
    projections = []
    
    for m in sorted_measurements:
        if m.height_cm is None:
            continue
        height_cm: float = m.height_cm
        proj = project_adult_height_from_current(
            m.age_months, height_cm, child.sex, tables
        )
        if proj is not None:
            ages.append(m.age_months)
            projections.append(proj)
            
    # ── Optional reference values ─────────────────────────────────────────────
    mph_target = None
    mph_low = None
    mph_high = None
    if father_cm is not None and mother_cm is not None:
        mph_target = mid_parental_height(father_cm, mother_cm, child.sex)
        mph_low, mph_high = mid_parental_height_range(father_cm, mother_cm, child.sex)
        
    doubling_result = None
    doubling_age_label = None
    ref_age = doubling_method_age(child.sex)
    near_measurements = [
        m for m in sorted_measurements
        if is_near_doubling_age(m.age_months, child.sex)
    ]
    if near_measurements:
        closest = min(near_measurements, key=lambda m: abs(m.age_months - ref_age))
        if closest.height_cm is None:
            doubling_result = None
        else:
            height_cm: float = closest.height_cm
            doubling_result = project_adult_height_doubling(height_cm, child.sex)
            doubling_age_label = f"{closest.age_months:.0f} mo"
        
    # ── Plot ──────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    
    # MPH shaded range
    if mph_low is not None and mph_high is not None:
        ax.axhspan(
            mph_low,
            mph_high,
            alpha=0.10,
            color=COLOR_PROJECTION,
            label=f"MPH range ({format_feet_inches(mph_low)}-{format_feet_inches(mph_high)})",
        )
        
    # MPH target line
    if mph_target is not None:
        ax.axhline(
            mph_target,
            color=COLOR_PROJECTION,
            linewidth=1.5,
            linestyle="--",
            label=f"Mid-parental height ({format_feet_inches(mph_target)})",
        )
        
    # Doubling method line
    if doubling_result is not None:
        ax.axhline(
            doubling_result,
            color=COLOR_MEDIAN,
            linewidth=1.5,
            linestyle=":",
            label=f"Doubling method at {doubling_age_label} ({format_feet_inches(doubling_result)})",
        )
        
    # Projection series
    ax.plot(
        ages,
        projections,
        "o",
        color=COLOR_MEASUREMENT,
        markersize=6,
        zorder=5,
        label="Percentile projection",
    )
    
    # Annotate each point with projected height in US customary units
    for age, proj in zip(ages, projections):
        ax.annotate(
            format_feet_inches(proj),
            xy=(age, proj),
            xytext=(0, 10),
            textcoords="offset points",
            fontsize=7,
            color=COLOR_MEASUREMENT,
            ha="center",
            fontweight="bold",
        )

    # ── Y axis zoom ───────────────────────────────────────────────────────────
    all_values = projections[:]
    if mph_target is not None:
        all_values.append(mph_target)
    if doubling_result is not None:
        all_values.append(doubling_result)
        
    y_min = min(all_values) - 10
    y_max = max(all_values) + 10
    ax.set_ylim(y_min, y_max)
    
    # ── Labels and formatting ─────────────────────────────────────────────────
    sex_label = "Boys" if child.sex == "M" else "Girls"
    ax.set_title(
        f"{child.name} - Projected Adult Height Over Time ({sex_label})",
        fontsize=14,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Age (months)", fontsize=11)
    ax.set_ylabel("Projected Adult Height (cm)", fontsize=11)
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, alpha=0.3, linewidth=0.5)
    
    # Secondary y-axis with US units
    _add_height_secondary_axis(ax, label="Projected Height (in)")
    
    fig.tight_layout()
    return fig


# ── Save helpers ──────────────────────────────────────────────────────────────

def save_charts(
    child: Child,
    tables: dict,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    father_cm: float | None = None,
    mother_cm: float | None = None,
) -> list[Path]:
    """
    Generate and save all applicable charts for a child.

    Charts are generated conditionally based on available data:
      - Height chart: saved if any measurement has height_cm
      - Weight chart: saved if any measurement has weight_kg
      - Head circumference chart: saved if any measurement has
        head_circumference_cm within the 0–36 month range
      - BMI chart: saved if any measurement at 24+ months has both
        height_cm and weight_kg
      - Projection over time: saved if any measurement has height_cm

    Args:
        child (Child): The child to generate charts for.
        tables (dict): The loaded LMS tables from load_all_tables().
        output_dir (Path): Directory to save charts in. Created if absent.
                           Defaults to output/charts/.
        father_cm (float | None): Father's height in cm for MPH projection.
        mother_cm (float | None): Mother's height in cm for MPH projection.

    Returns:
        list[Path]: List of paths to the saved chart files.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []
    name_slug = child.name.lower().replace(" ", "_")

    # Height chart
    if any(m.height_cm is not None for m in child.measurements):
        fig = plot_growth_chart(child, "height", tables)
        path = output_dir / f"{name_slug}_height.png"
        fig.savefig(path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        saved.append(path)
        print(f"  Saved: {path}")

    # Weight chart
    if any(m.weight_kg is not None for m in child.measurements):
        fig = plot_growth_chart(child, "weight", tables)
        path = output_dir / f"{name_slug}_weight.png"
        fig.savefig(path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        saved.append(path)
        print(f"  Saved: {path}")

    # Head circumference chart
    if any(
        m.head_circumference_cm is not None and m.age_months <= HC_MAX_AGE_MONTHS
        for m in child.measurements
    ):
        fig = plot_head_circumference_chart(child, tables)
        path = output_dir / f"{name_slug}_head_circumference.png"
        fig.savefig(path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        saved.append(path)
        print(f"  Saved: {path}")

    # BMI chart
    if any(
        m.bmi is not None and m.age_months >= WHO_CDC_CUTOFF
        for m in child.measurements
    ):
        fig = plot_bmi_chart(child, tables)
        path = output_dir / f"{name_slug}_bmi.png"
        fig.savefig(path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        saved.append(path)
        print(f"  Saved: {path}")

    # Projection over time
    if any(m.height_cm is not None for m in child.measurements):
        fig = plot_projection_over_time(child, tables, father_cm, mother_cm)
        path = output_dir / f"{name_slug}_projection_over_time.png"
        fig.savefig(path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        saved.append(path)
        print(f"  Saved: {path}")

    return saved