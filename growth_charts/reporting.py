"""
reporting.py

Generates per-child markdown growth reports combining summary statistics,
embedded chart images, and a full measurements table.

Each report is saved as a .md file in the reports directory alongside
the charts directory under the main output directory.

Report structure per child:
  1. Summary - name, sex, DOB, MPH, doubling mehod, and most recent measurements
  2. Height chart
  3. Weight chart
  4. Head circumference chart (if data exists)
  5. BMI chart (if data exists)
  6. Projected adult height over time chart
  7. Measurements table - one row per measurement with all available values
  
Measurement heights are displayed as feet/inches and decimal inches.
Head circumference is displayed as decimal inches and centimeters.
Adult height projections are displayed as feet/inches only.

Date formatting uses strftime with a manual leading-zero strip for
cross-platform compatiblity (%d is Mac/Linux only, %#d is Windows only).

Markdown is styled for clean PDF rendering - centered title, HTML tables
with right-aligned label columns, and a standard markdown measurements table.
"""

from datetime import date
from pathlib import Path

from growth_charts.models import Child
from growth_charts.percentiles import get_percentile, WHO_CDC_CUTOFF
from growth_charts.adult_height import (
    mid_parental_height,
    mid_parental_height_range,
    project_adult_height_doubling,
    project_adult_height_from_current,
    is_near_doubling_age,
    doubling_method_age,
)
from growth_charts.units import (
    format_age,
    format_feet_inches,
    format_decimal_inches,
    format_cm,
    format_lbs_oz,
    format_decimal_lbs,
    ordinal,
)
from growth_charts.plotting import HC_MAX_AGE_MONTHS


# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_REPORTS_DIR = Path("output/reports")
DEFAULT_CHARTS_DIR = Path("output/charts")

# Alternating row shading for measurement table (light gray)
TABLE_ROW_EVEN = "#f9f9f9"
TABLE_ROW_ODD = "#ffffff"


# ── Formatting helpers ────────────────────────────────────────────────────────

def _format_date(d: date) -> str:
    """
    Format a date as a human readable string, e.g. 'March 15, 2018'.
    
    Uses strftime with manual leading-zero stripping for cross-platform
    compatibility - %-d works on Mac/Linux only, %#d on Windows only.

    Args:
        d (date): The date to format.

    Returns:
        str: Human-readable string with no leading zero on the day.
    """
    return d.strftime("%B %d, %Y").replace(" 0", " ")


def _format_percentile(pct: float | None) -> str:
    """
    Format a percentile value as an ordinal string, e.g. '45th'.

    Args:
        pct (float | None): Percentile value between 0 and 100, or None.

    Returns:
        str: Ordinal percentile string, or '-' if None.
    """
    if pct is None:
        return "-"
    return ordinal(round(pct))


def _format_projected_height(
    age_months: float,
    height_cm: float,
    sex: str,
    tables: dict,
) -> str:
    """
    Format the projected adult height for a single measurement as a string.
    
    Projected heights are shown in feet and inches only (one decimal place
    on inches) since projections don't warrant the precision of decimal inches
    or centimeters.

    Args:
        age_months (float): The child's age in months at measurement time.
        height_cm (float): The child's height in cm at measurement time.
        sex (str): 'M' for male or 'F' for female.
        tables (dict): The loaded LMS tables from load_all_tables().

    Returns:
        str: Formatted projected height in feet and inches, or '-' if
             unavailable.
    """
    proj = project_adult_height_from_current(age_months, height_cm, sex, tables)
    if proj is None:
        return "-"
    return format_feet_inches(proj)


# ── Data availability helpers ─────────────────────────────────────────────────

def _has_head_circumference(child: Child) -> bool:
    """
    Return True is the child has any head circumference measurements
    within the 0-36 month range.

    Args:
        child (Child): The child to check

    Returns:
        bool: True if head circumference data is available.
    """
    return any(
        m.head_circumference_cm is not None
        and m.age_months <= HC_MAX_AGE_MONTHS
        for m in child.measurements
    )
    
    
def _has_bmi(child: Child) -> bool:
    """
    Return True if the child has any BMI data at 24+ months
    (requires both height and weight).

    Args:
        child (Child): The child to check.

    Returns:
        bool: True if BMI data is available.
    """
    return any(
        m.bmi is not None and m.age_months >= WHO_CDC_CUTOFF
        for m in child.measurements
    )


# ── Section builders ──────────────────────────────────────────────────────────

def _build_summary_section(
    child: Child,
    tables: dict,
    father_cm: float | None,
    mother_cm: float | None,
) -> str:
    """
    Build the summary section of the markdown report.
    
    Includes name, sex, DOB, mid-parental height (if available),
    doubling method result (if applicable), and most recent measurements.
    Head circumference and BMI are included in most recent measurements
    when available.

    Args:
        child (Child): The child to summarize.
        tables (dict): The loaded LMS tables from load_all_tables().
        father_cm (float | None): Father's height in cm.
        mother_cm (float | None): Mother's height in cm.

    Returns:
        str: Markdown string for the summary section.
    """
    sex_label = "Male" if child.sex == "M" else "Female"
    
    # Use HTML table for the summary block for better PDF rendering
    lines = [
        "## Summary\n",
        '<table>',
        f'<tr><td align="right"><strong>Name</strong></td><td>{child.name}</td></tr>',
        f'<tr><td align="right"><strong>Sex</strong></td><td>{sex_label}</td></tr>',
        f'<tr><td align="right"><strong>Date of Birth</strong></td>'
        f'<td>{_format_date(child.dob)}</td></tr>',
    ]
    
    # Mid-parental height
    if father_cm is not None and mother_cm is not None:
        mph = mid_parental_height(father_cm, mother_cm, child.sex)
        mph_low, mph_high = mid_parental_height_range(father_cm, mother_cm, child.sex)
        lines.append(
            f'<tr><td align="right"><strong>Adult Height Projection <br>Mid-Parental Height Method</strong></td>'
            f'<td>{format_feet_inches(mph_low)} – {format_feet_inches(mph_high)}'
            f' (target: {format_feet_inches(mph)})</td></tr>'
        )
        
    # Doubling method - find measurement closest to reference age
    ref_age = doubling_method_age(child.sex)
    near_measurements = [
        m for m in child.measurements
        if is_near_doubling_age(m.age_months, child.sex)
    ]
    if near_measurements:
        closest = min(near_measurements, key=lambda m: abs(m.age_months - ref_age))
        if closest.height_cm is not None:
            doubling_result = project_adult_height_doubling(
                closest.height_cm, child.sex
            )
            lines.append(
                f'<tr><td align="right"><strong>Adult Height Projection <br>Doubling Method</strong></td>'
                f'<td>{format_feet_inches(doubling_result)}</td></tr>'
            )
        
    lines.append('</table>\n')
    
    # Most recent measurements
    latest = child.latest_measurement
    if latest is not None:
        height_pct = (
            get_percentile(
                latest.age_months, latest.height_cm,
                child.sex, "height", tables
            )
            if latest.height_cm is not None else None
        )
        weight_pct = (
            get_percentile(
                latest.age_months, latest.weight_kg,
                child.sex, "weight", tables
            )
            if latest.weight_kg is not None else None
        )
        hc_pct = (
            get_percentile(
                latest.age_months, latest.head_circumference_cm,
                child.sex, "head_circumference", tables
            )
            if latest.head_circumference_cm is not None else None
        )
        bmi_pct = (
            get_percentile(
                latest.age_months, latest.bmi,
                child.sex, "bmi", tables
            )
            if latest.bmi is not None else None
        )
        proj = (
            project_adult_height_from_current(
                latest.age_months, latest.height_cm, child.sex, tables
            )
            if latest.height_cm is not None else None
        )
        proj_str = format_feet_inches(proj) if proj else "-"
        
        lines += [
            "### Most Recent Measurements\n",
            "<table>",
            f'<tr><td align="right"><strong>Date</strong></td>'
            f'<td colspan="3">{_format_date(latest.date)}</td></tr>',
            f'<tr><td align="right"><strong>Age</strong></td>'
            f'<td colspan="3">{format_age(child.dob, latest.date)}</td></tr>',
        ]
        
        if latest.height_cm is not None:
            lines.append(
                f'<tr><td align="right"><strong>Height</strong></td>'
                f'<td>{format_feet_inches(latest.height_cm)}</td>'
                f'<td>{format_decimal_inches(latest.height_cm)}</td>'
                f'<td>{_format_percentile(height_pct)} percentile</td></tr>'
            )
            
        if latest.weight_kg is not None:
            lines.append(
                f'<tr><td align="right"><strong>Weight</strong></td>'
                f'<td>{format_lbs_oz(latest.weight_kg)}</td>'
                f'<td>{format_decimal_lbs(latest.weight_kg)}</td>'
                f'<td>{_format_percentile(weight_pct)} percentile</td></tr>'
            )
            
        if latest.head_circumference_cm is not None:
            hc_in = format_decimal_inches(latest.head_circumference_cm)
            hc_cm = format_cm(latest.head_circumference_cm)
            lines.append(
                f'<tr><td align="right"><strong>Head Circumference</strong></td>'
                f'<td colspan="2">{hc_in} ({hc_cm})</td>'
                f'<td>{_format_percentile(hc_pct)} percentile</td></tr>'
            )
            
        if latest.bmi is not None and latest.age_months >= WHO_CDC_CUTOFF:
            lines.append(
                f'<tr><td align="right"><strong>BMI</strong></td>'
                f'<td colspan="2">{latest.bmi} kg/m²</td>'
                f'<td>{_format_percentile(bmi_pct)} percentile</td></tr>'
            )
            
        lines.append(
            f'<tr><td align="right"><strong>Projected Adult Height</strong></td>'
            f'<td colspan="3">{proj_str}</td></tr>'
        )
        
        lines.append("</table>\n")
        
    return "\n".join(lines)


def _build_charts_section(
    child: Child,
    charts_dir: Path,
    reports_dir: Path,
) -> str:
    """
    Build the charts section of the markdown report with embedded images.
    
    Image paths are relative from the reports directory to the charts
    directory so the links work correctly on GitHub and locally.

    Args:
        child (Child): The child the charts belong to.
        charts_dir (Path): Directory where the chart images are saved.
        reports_dir (Path): Directory where the report will be saved.

    Returns:
        str: Markdown string for the charts section.
    """
    name_slug = child.name.lower().replace(" ", "_")
    
    # Build the relative path from the reports dir to the charts dir.
    # e.g. output/reports -> output/charts becomes ../charts
    try:
        rel_path = Path(
            "../" + charts_dir.resolve().relative_to(
                reports_dir.resolve().parent
            ).as_posix()
        )
    except ValueError:
        # Fallback to absolute path if dirs don't share a common parent
        rel_path = charts_dir.resolve()
        
    def img(filename: str, alt: str) -> str:
        return f"![{alt}]({rel_path}/{filename})"
    
    lines = [
        "## Height\n",
        img(f"{name_slug}_height.png", f"{child.name} Height Chart"),
        "",
        "## Weight\n",
        img(f"{name_slug}_weight.png", f"{child.name} Weight Chart"),
        "",
    ]
    
    if _has_head_circumference(child):
        lines += [
            "## Head Circumference\n",
            img(f"{name_slug}_head_circumference.png",
                f"{child.name} Head Circumference Chart"),
            "",
        ]
        
    if _has_bmi(child):
        lines += [
            "## BMI\n",
            img(f"{name_slug}_bmi.png", f"{child.name} BMI Chart"),
            "",
        ]
        
    lines += [
        "## Projected Adult Height Over Time\n",
        img(f"{name_slug}_projection_over_time.png",
            f"{child.name} Projection Over Time"),
        "",
    ]
    
    return "\n".join(lines)


def _build_measurements_table(
    child: Child,
    tables: dict,
) -> str:
    """
    Build the measurements table section of the markdown report.

    Uses a standard markdown table for maximum GitHub and VSCode
    compatibility. Head circumference and BMI columns are only included
    if at least one measurement has that value.

    Columns:
      Date of Measurement | Age at Measurement | ft / in | in |
      Height % | lb / oz | lb | Weight % | Projected Adult Height

    Measurement heights are shown in feet/inches and decimal inches.
    Projected adult heights are shown in feet/inches only.

    Args:
        child (Child): The child whose measurements to tabulate.
        tables (dict): The loaded LMS tables from load_all_tables().

    Returns:
        str: Markdown table string for the measurements section.
    """
    show_hc = _has_head_circumference(child)
    show_bmi = _has_bmi(child)
    
    header = (
        "| Date of Measurement | Age at Measurement "
        "| Height (ft / in) | Height (in) | Height % "
        "| Weight (lb / oz) | Weight (lb) | Weight % "
    )
    separator = "|---|---|---|---|---|---|---|---"
    
    if show_hc:
        header += "| Head Circ (in / cm) | Head Circ % "
        separator += "|---|---"
        
    if show_bmi:
        header += "| BMI | BMI % "
        separator += "|---|---"
        
    header += "| Projected Adult Height |"
    separator += "|---|"
    
    lines = [
        "## Measurements \n",
        header,
        separator,
    ]
    
    sorted_measurements = sorted(child.measurements, key=lambda m: m.date)
    
    for m in sorted_measurements:
        height_pct = (
            get_percentile(m.age_months, m.height_cm,
                           child.sex, "height", tables)
            if m.height_cm is not None else None
        )
        weight_pct = (
            get_percentile(m.age_months, m.weight_kg,
                           child.sex, "weight", tables)
            if m.weight_kg is not None else None
        )
        proj_str = (
            _format_projected_height(
                m.age_months, m.height_cm, child.sex, tables
            )
            if m.height_cm is not None else "-"
        )
        
        # Height columns
        if m.height_cm is not None:
            h_ft_in = format_feet_inches(m.height_cm)
            h_in = format_decimal_inches(m.height_cm)
            height_pct_str = _format_percentile(height_pct)
        else:
            h_ft_in = "-"
            h_in = "-"
            height_pct_str = "-"
            
        # Weight columns
        if m.weight_kg is not None:
            w_lbs_oz = format_lbs_oz(m.weight_kg)
            w_lbs = format_decimal_lbs(m.weight_kg)
            weight_pct_str = _format_percentile(weight_pct)
        else:
            w_lbs_oz = "-"
            w_lbs = "-"
            weight_pct_str = "-"
            
        row = (
            f"| {_format_date(m.date)} "
            f"| {format_age(child.dob, m.date)} "
            f"| {h_ft_in} "
            f"| {h_in} "
            f"| {height_pct_str} "
            f"| {w_lbs_oz} "
            f"| {w_lbs} "
            f"| {weight_pct_str} "
        )
        
        # Head circumference columns
        if show_hc:
            if (m.head_circumference_cm is not None
                and m.age_months <= HC_MAX_AGE_MONTHS):
                hc_in = format_decimal_inches(m.head_circumference_cm)
                hc_cm = format_cm(m.head_circumference_cm)
                hc_pct = get_percentile(
                    m.age_months, m.head_circumference_cm,
                    child.sex, "head_circumference", tables
                )
                hc_str = f"{hc_in} ({hc_cm})"
                hc_pct_str = _format_percentile(hc_pct)
            else:
                hc_str = "-"
                hc_pct_str = "-"
            row += f"| {hc_str} | {hc_pct_str} "
            
        # BMI columns
        if show_bmi:
            if m.bmi is not None and m.age_months >= WHO_CDC_CUTOFF:
                bmi_pct = get_percentile(
                    m.age_months, m.bmi, child.sex, "bmi", tables
                )
                bmi_str = f"{m.bmi}"
                bmi_pct_str = _format_percentile(bmi_pct)
            else:
                bmi_str = "-"
                bmi_pct_str = "-"
            row += f"| {bmi_str} | {bmi_pct_str} "
            
        row += f"| {proj_str} |"
        lines.append(row)
        
    lines.append("")
    return "\n".join(lines)


# ── Public API ────────────────────────────────────────────────────────────────

def generate_report(
    child: Child,
    tables: dict,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    charts_dir: Path = DEFAULT_CHARTS_DIR,
    father_cm: float | None = None,
    mother_cm: float | None = None,
) -> Path:
    """
    Generate a markdown growth report for a single child and save it to disk.
    
    The report includes a summary with most recent measurements, embedded
    chart images (conditionally including head circumference and BMI charts),
    and a full measurements table with all available values and percentiles.

    Args:
        child (Child): The child to generate the report for.
        tables (dict): The loaded LMS tables from load_all_tables().
        reports_dir (Path, optional): Directory to save the report in.
                                      Defaults to output/reports/.
        charts_dir (Path, optional): Directory where chart images are saved.
                                     Defaults to output/charts/.
        father_cm (float | None, optional): Father's height in cm for MPH calculation.
                                            Defaults to None.
        mother_cm (float | None, optional): Mother's height in cm for MPH calculation.
                                            Defaults to None.

    Returns:
        Path: The path to the saved report file.
        
    Raises:
        ValueError: If the child has no measurements.
    """
    if not child.measurements:
        raise ValueError(f"Child '{child.name}' has no measurements")
    
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    sections = [
        '<div align="center">\n',
        f"# {child.name} - Growth Report\n",
        f"*Generated on {_format_date(date.today())}*\n",
        "</div>\n",
        _build_summary_section(child, tables, father_cm, mother_cm),
        _build_charts_section(child, charts_dir, reports_dir),
        _build_measurements_table(child, tables),
    ]
    
    content = "\n".join(sections)
    name_slug = child.name.lower().replace(" ", "_")
    report_path = reports_dir / f"{name_slug}_report.md"
    report_path.write_text(content, encoding="utf-8")
    
    return report_path