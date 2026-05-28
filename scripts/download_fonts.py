"""
download_fonts.py

Downloads Google Fonts required for PDF report generation.

Fonts are saved to growth_charts/fonts/ and referenced locally by
WeasyPrint during PDF rendering. This avoids network requests during
PDF generation and ensures fonts render correctly offline.

Fonts downloaded:
  Open Sans       - body text and tables (Regular, SemiBold, Bold)
  
Usage:
    python scripts/download_fonts.py
    python scripts/download_fonts.py --force  # re-download existing files
"""

import argparse
import sys
from pathlib import Path

import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

FONTS_DIR = Path(__file__).parent.parent / "growth_charts" / "fonts"

FONT_FILES = [
    (
        "OpenSans-Regular.ttf",
        "https://raw.githubusercontent.com/googlefonts/opensans/main/fonts/ttf/OpenSans-Regular.ttf",
        "Open Sans Regular",
    ),
    (
        "OpenSans-SemiBold.ttf",
        "https://raw.githubusercontent.com/googlefonts/opensans/main/fonts/ttf/OpenSans-SemiBold.ttf",
        "Open Sans SemiBold",
    ),
    (
        "OpenSans-Bold.ttf",
        "https://raw.githubusercontent.com/googlefonts/opensans/main/fonts/ttf/OpenSans-Bold.ttf",
        "Open Sans Bold",
    ),
]


def download_font(filename: str, url: str, description: str) -> bool:
    """
    Download a single font file.

    Args:
        filename (str): The local filename to save to.
        url (str): The URL to download from.
        description (str): Human-readable label for console output.

    Returns:
        bool: True on success, False on failure.
    """
    print(f"  Downloading: {description}")
    print(f"    → {filename}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"    ✗ HTTP error: {e}")
        return False
    except requests.exceptions.ConnectionError:
        print("    ✗ Connection error — check your internet connection")
        return False
    except requests.exceptions.Timeout:
        print("    ✗ Request timed out")
        return False

    if len(response.content) < 1000:
        print("    ✗ Response too small — possible error")
        return False
    
    dest = FONTS_DIR / filename
    dest.write_bytes(response.content)
    size_kb = len(response.content) / 1024
    print(f"    ✓ Saved ({size_kb:.1f} KB)")
    return True


def main() -> None:
    """Download all font files."""
    parser = argparse.ArgumentParser(
        description="Download Google Fonts for PDF report generation."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download files even if they already exist",
    )
    args = parser.parse_args()
    
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Fonts directory: {FONTS_DIR}\n")
    print("── Font files ─────────────────────────────────")
    
    success = 0
    skipped = 0
    
    for filename, url, description in FONT_FILES:
        dest = FONTS_DIR / filename
        if dest.exists() and not args.force:
            print(f"  Skipping (already exists): {filename}")
            skipped += 1
            continue
        ok = download_font(filename, url, description)
        if ok:
            success += 1
        else:
            if dest.exists() and dest.stat().st_size < 1000:
                dest.unlink()
                
    failed = len(FONT_FILES) - success - skipped
    print("\n── Summary ────────────────────────────────────")
    print(f"  Downloaded : {success}")
    print(f"  Skipped    : {skipped}  (use --force to re-download)")
    print(f"  Failed     : {failed}")

    if failed > 0:
        print("\n  Some fonts failed. Check your internet connection and try again.")
        sys.exit(1)
    else:
        print("\n  All done! Font files are ready in growth_charts/fonts/")
        
        
if __name__ == "__main__":
    main()