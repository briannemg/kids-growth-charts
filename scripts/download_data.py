"""
download_data.py

Downloads CDC and WHO growth chart LMS data from official CDC servers.

Sources:
  CDC (ages 2-20 years):  https://www.cdc.gov/growthcharts/cdc-data-files.htm
  WHO (birth-24 months):  https://www.cdc.gov/growthcharts/who-data-files.htm
  
Usage:
  python scripts/download_data.py              # Skip files that already exist
  python scripts/download_data.py --force      # Re-download everything
  python scripts/download_data.py --source cdc # Only CDC files
  python scripts/download_data.py --source who # Only WHO files
"""

import argparse
import sys
from pathlib import Path

import requests

# ── Output directory (relative to project root) ───────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "growth_charts" / "data"

# ── File manifest ─────────────────────────────────────────────────────────────
# Each entry: (local_filename, url, description)
#
# CDC NOTE: These CSVs contain a Sex column where 1 = Male, 2 = Female.
# The 2-to-20 files (statage, wtage) cover both sexes in a single file.
# The birth-to-36-month files (lenageinf, wtageinf) also cover both sexes.
#
# WHO NOTE: Files are split by sex (Boys/Girls) and hosted on CDC's FTP server.
# These are the WHO 2006 Child Growth Standards - they do not change.
CDC_FILES = [
    (
        "cdc_stature_for_age_2_20.csv",
        "https://www.cdc.gov/growthcharts/data/zscore/statage.csv",
        "CDC stature-for-age, 2–20 years (both sexes)",
    ),
    (
        "cdc_weight_for_age_2_20.csv",
        "https://www.cdc.gov/growthcharts/data/zscore/wtage.csv",
        "CDC weight-for-age, 2–20 years (both sexes)",
    ),
    (
        "cdc_length_for_age_0_36.csv",
        "https://www.cdc.gov/growthcharts/data/zscore/lenageinf.csv",
        "CDC length-for-age, birth–36 months (both sexes)",
    ),
    (
        "cdc_weight_for_age_0_36.csv",
        "https://www.cdc.gov/growthcharts/data/zscore/wtageinf.csv",
        "CDC weight-for-age, birth–36 months (both sexes)",
    ),
    (
        "cdc_head_circumference_0_36.csv",
        "https://www.cdc.gov/growthcharts/data/zscore/hcageinf.csv",
        "CDC head circumference-for-age, birth–36 months (both sexes)",
    ),
    (
        "cdc_bmi_for_age_2_20.csv",
        "https://www.cdc.gov/growthcharts/data/zscore/bmiagerev.csv",
        "CDC BMI-for-age, 2–20 years (both sexes)",
    ),
]

WHO_FILES = [
    (
        "who_length_for_age_boys.csv",
        "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/growthcharts/WHO-Boys-Length-for-age-Percentiles.csv",
        "WHO length-for-age, birth–24 months, boys",
    ),
    (
        "who_length_for_age_girls.csv",
        "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/growthcharts/WHO-Girls-Length-for-age-Percentiles.csv",
        "WHO length-for-age, birth–24 months, girls",
    ),
    (
        "who_weight_for_age_boys.csv",
        "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/growthcharts/WHO-Boys-Weight-for-age-Percentiles.csv",
        "WHO weight-for-age, birth–24 months, boys",
    ),
    (
        "who_weight_for_age_girls.csv",
        "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/growthcharts/WHO-Girls-Weight-for-age%20Percentiles.csv",
        "WHO weight-for-age, birth–24 months, girls",
    ),
    (
        "who_head_circumference_boys.csv",
        "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/growthcharts/WHO-Boys-Head-Circumference-for-age-Percentiles.csv",
        "WHO head circumference-for-age, birth–24 months, boys",
    ),
    (
        "who_head_circumference_girls.csv",
        "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/growthcharts/WHO-Girls-Head-Circumference-for-age-Percentiles.csv",
        "WHO head circumference-for-age, birth–24 months, girls",
    ),
]

ALL_FILES = {"cdc": CDC_FILES, "who": WHO_FILES}


# ── Helpers ───────────────────────────────────────────────────────────────────

def download_file(url: str, dest: Path, description: str) -> bool:
    """
    Download a single file from url to dest.
    Returns True on success, False on failure.

    Args:
        url (str): The URL to download from.
        dest (Path): The local file path to save the downloaded content.
        description (str): Human-readable label used in console output.

    Returns:
        bool: True if the file was downloaded and saved successfully,
              False if the request failed or the response content was too small.
    """
    print(f"  Downloading: {description}")
    print(f"    → {dest.name}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"    ✗ HTTP error: {e}")
        return False
    except requests.exceptions.ConnectionError:
        print("    ✗ Connection error - check your internet connection")
        return False
    except requests.exceptions.Timeout:
        print("    ✗ Request timed out")
        return False
    
    # Basic sanity check: CDC CSVs are never this small; likely are error page
    if len(response.content) < 500:
        print(f"    ✗ Response too small ({len(response.content)} bytes) - possible redirect or error page")
        return False
    
    dest.write_bytes(response.content)
    size_kb = len(response.content) / 1024
    print(f"    ✓ Saved ({size_kb:.1f} KB)")
    return True


def process_file_list(file_list: list, force: bool) -> tuple[int, int]:
    """
    Download files from a list of (filename, url, description) tuples.

    Args:
        file_list (list): List of tuples in the form (filename, url, description).
        force (bool): If True, re-download files that already exist locally.

    Returns:
        tuple[int, int]: A tuple of (success_count, skip_count) where
                         success_count is the number of files downloaded and
                         skip_count is the number of files skipped.
    """
    success = 0
    skipped = 0
    
    for filename, url, description in file_list:
        dest = DATA_DIR / filename
        
        if dest.exists() and not force:
            print(f"  Skipping (already exists): {filename}")
            skipped += 1
            continue
        
        ok = download_file(url, dest, description)
        if ok:
            success += 1
        else:
            # Don't leave partial/empty files behind
            if dest.exists() and dest.stat().st_size < 500:
                dest.unlink()
                
    return success, skipped
    
    
# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Download CDC and WHO growth chart LMS data files."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download files even if they already exist",
    )
    parser.add_argument(
        "--source",
        choices=["cdc", "who", "all"],
        default="all",
        help="Which data source to download (default: all)",
    )
    args = parser.parse_args()
    
    # Ensure the output directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Data directory: {DATA_DIR}\n")
    
    sources = ["cdc", "who"] if args.source == "all" else [args.source]
    
    total_success = 0
    total_skipped = 0
    total_files = 0
    
    for source in sources:
        file_list = ALL_FILES[source]
        total_files += len(file_list)
        label = "CDC" if source == "cdc" else "WHO"
        print(f"── {label} files ──────────────────────────────")
        ok, skipped = process_file_list(file_list, force=args.force)
        total_success += ok
        total_skipped += skipped
        print()
        
    # Summary
    failed = total_files - total_success - total_skipped
    print("── Summary ────────────────────────────────────")
    print(f"  Downloaded : {total_success}")
    print(f"  Skipped    : {total_skipped}  (use --force to re-download)")
    print(f"  Failed     : {failed}")
    
    if failed > 0:
        print("\n Some files failed. Check your internet connection and try again.")
        sys.exit(1)
    else:
        print("\n All done! Data files are ready in growth_charts/data/")
        

if __name__ == "__main__":
    main()