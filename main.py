"""
main.py

Entry point for the kids growth charts application.

Loads child growth data from a JSON file, calculates growth percentiles
using CDC and WHO reference data, generates height and weight charts,
produces adult height projections using all applicable methods, and
generates a markdown report for each child.

Usage:
    python main.py                               # uses data/dummy_data.json
    python main.py --data data/my_family.json    # use your own data file
    python main.py --output output/              # specify output directory
    python main.py --list                        # list children in data file
    python main.py --child "Alex"                # one child only
"""

import argparse
import sys
from pathlib import Path

from growth_charts.models import Child
from growth_charts.data_loader import load_data
from growth_charts.percentiles import get_percentile, load_all_tables, WHO_CDC_CUTOFF
from growth_charts.pdf_report import generate_pdf, WEASYPRINT_AVAILABLE
from growth_charts.plotting import save_charts
from growth_charts.reporting import generate_report
from growth_charts.units import (
    format_age,
    format_feet_inches,
    format_decimal_inches,
    format_lbs_oz,
    format_decimal_lbs,
    format_cm,
    ordinal,
)


# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_DATA_FILE = Path("data/dummy_data.json")
DEFAULT_OUTPUT_DIR = Path("output")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _print_summary(child: Child, tables: dict) -> None:
    """
    Print a summary of a child's latest measurements and percentiles
    to the console.

    Args:
        child (Child): The child to summarize.
        tables (dict): The loaded LMS tables from load_all_tables().
    """
    latest = child.latest_measurement
    if latest is None:
        print(f"  {child.name}: no measurements")
        return
    
    print(f"\n  {child.name}  ({child.sex})")
    print(f"  Age:     {format_age(child.dob, latest.date)}")
    
    if latest.height_cm is not None:
        height_cm: float = latest.height_cm
        height_pct = get_percentile(
            latest.age_months, height_cm, child.sex, "height", tables
        )
        height_pct_str = (
            f"  → {ordinal(round(height_pct))} percentile"
            if height_pct is not None else ""
        )
        print(f"  Height:  {format_feet_inches(height_cm)}"
              f"  ({format_decimal_inches(height_cm)})"
              f"  ({height_cm} cm) {height_pct_str}")

    if latest.weight_kg is not None:
        weight_kg: float = latest.weight_kg
        weight_pct = get_percentile(
            latest.age_months, weight_kg, child.sex, "weight", tables
        )
        weight_pct_str = (
            f"  →  {ordinal(round(weight_pct))} percentile"
            if weight_pct is not None else ""
        )
        print(f"  Weight:  {format_lbs_oz(weight_kg)}"
              f"  ({format_decimal_lbs(weight_kg)})"
              f"  ({weight_kg} kg){weight_pct_str}")

    if latest.head_circumference_cm is not None:
        hc_cm: float = latest.head_circumference_cm
        hc_pct = get_percentile(
            latest.age_months, hc_cm, child.sex, "head_circumference", tables
        )
        hc_pct_str = (
            f"  →  {ordinal(round(hc_pct))} percentile"
            if hc_pct is not None else ""
        )
        print(f"  Head:    {format_decimal_inches(hc_cm)}"
              f"  ({format_cm(hc_cm)}){hc_pct_str}")
        
    if latest.bmi is not None and latest.age_months >= WHO_CDC_CUTOFF:
        bmi: float = latest.bmi
        bmi_pct = get_percentile(
            latest.age_months, bmi, child.sex, "bmi", tables
        )
        bmi_pct_str = (
            f"  →  {ordinal(round(bmi_pct))} percentile"
            if bmi_pct is not None else ""
        )
        print(f"  BMI:     {bmi} kg/m²{bmi_pct_str}")
    
    
def _generate_for_child(
    child: Child,
    tables: dict,
    charts_dir: Path,
    reports_dir: Path,
    father_cm: float | None,
    mother_cm: float | None,
    generate_pdf_flag: bool = False,
) -> None:
    """
    Generate and save all charts and the markdown report for a single child.
    Optionally generates a PDF version of the report.

    Args:
        child (Child): The child to generate output for.
        tables (dict): The loaded LMS tables from load_all_tables().
        charts_dir (Path): Directory to save chart images in.
        reports_dir (Path): Directory to save the markdown report in.
        father_cm (float | None): Father's height in cm for MPH projection.
        mother_cm (float | None): Mother's height in cm for MPH projection.
        generate_pdf_flag (bool): If True, also generate a PDF report.
    """
    print(f"\n Generating charts for {child.name}...")
    save_charts(
        child=child,
        tables=tables,
        output_dir=charts_dir,
        father_cm=father_cm,
        mother_cm=mother_cm
    )
    
    print(f"  Generating report for {child.name}...")
    report_path = generate_report(
        child=child,
        tables=tables,
        reports_dir=reports_dir,
        charts_dir=charts_dir,
        father_cm=father_cm,
        mother_cm=mother_cm
    )
    print(f"  Saved: {report_path}")
    
    if generate_pdf_flag:
        if not WEASYPRINT_AVAILABLE:
            print("  Skipping PDF - weasyprint not installed.")
            print("  Run: pip install weasyprint markdown && brew install pango")
        else:
            print(f"  Generating PDF for {child.name}...")
            pdf_path = generate_pdf(report_path, child.sex)
            print(f"  Saved: {pdf_path}")
    
    
# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    """
    Main entry point. Parses arguments, loads data, and generates all output.
    """
    parser = argparse.ArgumentParser(
        description="Generate CDC/WHO growth charts and adult height projections."
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help=f"Path to the JSON data file (default: {DEFAULT_DATA_FILE})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Root output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--child",
        type=str,
        default=None,
        help="Generate output for a single child by name only",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all children in the data file and exit",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Also generate a PDF version of each report (requires weasyprint)",
    )
    args = parser.parse_args()
    
    # ── Derived output paths ──────────────────────────────────────────────────
    charts_dir = args.output / "charts"
    reports_dir = args.output / "reports"
    
    # ── Load data file ────────────────────────────────────────────────────────
    print(f"\nLoading data from {args.data}...")
    try:
        data = load_data(args.data)
    except FileNotFoundError as e:
        print(f"\n Error: {e}")
        print("  Run 'python main.py --data <path>' to specify a different file.")
        sys.exit(1)
        
    children = data["children"]
    father_cm = data["father_cm"]
    mother_cm = data["mother_cm"]
    
    if not children:
        print("\n No children found in data file.")
        sys.exit(1)
        
    # ── List mode ─────────────────────────────────────────────────────────────
    if args.list:
        print(f"\nChildren in {args.data}:")
        for child in children:
            n = len(child.measurements)
            print(f"  - {child.name}  ({n} measurement{'s' if n != 1 else ''})")
        sys.exit(0)
        
    # ── Load LMS tables ───────────────────────────────────────────────────────
    print("Loading CDC/WHO reference tables...")
    try:
        tables = load_all_tables()
    except FileNotFoundError as e:
        print(f"\n Error: {e}")
        print("  Run 'python scripts/download_data.py' to download the reference data.")
        sys.exit(1)
        
    if args.pdf and not WEASYPRINT_AVAILABLE:
        print("\n  Warning: --pdf requested but weasyprint is not installed.")
        print("  Run: pip install weasyprint markdown && brew install pango")
        print("  Continuing without PDF generation...\n")    
        
    # ── Filter to requested child if --child was given ────────────────────────
    if args.child:
        matches = [c for c in children if c.name.lower() == args.child.lower()]
        if not matches:
            names = ", ".join(c.name for c in children)
            print(f"\n Error: No child names '{args.child}' found.")
            print(f"  Available: {names}")
            sys.exit(1)
        children = matches
        
    # ── Print summaries ───────────────────────────────────────────────────────
    print("\n── Latest measurements ──────────────────────────────────────────")
    for child in children:
        _print_summary(child, tables)
        
    # ── Generate charts and reports ───────────────────────────────────────────
    print("\n── Generating charts and reports ────────────────────────────────")
    for child in children:
        _generate_for_child(
            child, tables, charts_dir, reports_dir,
            father_cm, mother_cm,
            generate_pdf_flag=args.pdf,
        )
        
    # ── Done ──────────────────────────────────────────────────────────────────
    print("\n── Done ─────────────────────────────────────────────────────────")
    print(f"  Charts saved to: {charts_dir.resolve()}")
    print(f"  Reports saved to: {reports_dir.resolve()}\n")
    
    
    
if __name__ == "__main__":
    main()