"""
pdf_report.py

Generates PDF growth reports from markdown report files.

Converts the markdown report to HTML, injects a polished CSS stylesheet
with Google Fonts, rewrites image paths to absolute file:// URIs so
WeasyPrint can embed the charts, and renders to a PDF file.

Font choices:
  Body/tables:  Open Sans    — clean, professional, readable
  Boys title:   Fredoka One  — bold, rounded, blocky and fun
  Girls title:  Pacifico     — flowing, cursive, frilly

Page setup:
  Size:    US Letter (8.5 × 11 inches)
  Margins: 0.75 inches on all sides
  Footer:  Child name and page numbers

Requires:
  pip install weasyprint markdown
  brew install pango  (Mac)
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

# Check weasyprint availability
WEASYPRINT_AVAILABLE = (
    importlib.util.find_spec("weasyprint") is not None
    and importlib.util.find_spec("markdown") is not None
)


# ── CSS stylesheet ────────────────────────────────────────────────────────────

def _build_css() -> str:
    """
    Build the CSS stylesheet for the PDF report.

    Uses locally downloaded fonts for reliable offline rendering.
    Open Sans is used for body text and tables.

    Returns:
        str: Complete CSS stylesheet as a string.
    """
    fonts_dir = Path(__file__).parent / "fonts"
    open_sans_regular = fonts_dir / "OpenSans-Regular.ttf"
    open_sans_semibold = fonts_dir / "OpenSans-SemiBold.ttf"
    open_sans_bold = fonts_dir / "OpenSans-Bold.ttf"

    font_faces = f"""
    @font-face {{
        font-family: 'Open Sans';
        font-weight: 400;
        src: url('file://{open_sans_regular}');
    }}
    @font-face {{
        font-family: 'Open Sans';
        font-weight: 600;
        src: url('file://{open_sans_semibold}');
    }}
    @font-face {{
        font-family: 'Open Sans';
        font-weight: 700;
        src: url('file://{open_sans_bold}');
    }}
    """

    return f"""
    {font_faces}

    /* ── Page setup ── */
    @page {{
        size: letter;
        margin: 0.75in;

        @bottom-center {{
            content: string(child-name) " — Growth Report  |  Page " counter(page) " of " counter(pages);
            font-family: 'Open Sans', sans-serif;
            font-size: 9pt;
            color: #888888;
            border-top: 1px solid #dddddd;
            padding-top: 6pt;
        }}
    }}

    /* ── Base typography ── */
    body {{
        font-family: 'Open Sans', sans-serif;
        font-size: 10.5pt;
        line-height: 1.5;
        color: #222222;
        background: white;
    }}

    /* ── Title ── */
    h1 {{
        font-family: 'Open Sans', sans-serif;
        font-size: 28pt;
        font-weight: 700;
        text-align: center;
        color: #2c3e50;
        margin-bottom: 4pt;
    }}

    /* Hidden element used only for footer string — contains child name only */
    .footer-name {{
        string-set: child-name content();
        position: absolute;
        visibility: hidden;
        font-size: 0;
    }}

    /* ── Generated date ── */
    .generated-date {{
        text-align: center;
        font-size: 9pt;
        color: #888888;
        margin-bottom: 16pt;
    }}

    /* ── Section headings ── */
    h2 {{
        font-family: 'Open Sans', sans-serif;
        font-size: 14pt;
        font-weight: 700;
        color: #2c3e50;
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 4pt;
        margin-top: 20pt;
        margin-bottom: 10pt;
        page-break-after: avoid;
    }}

    h3 {{
        font-family: 'Open Sans', sans-serif;
        font-size: 11pt;
        font-weight: 600;
        color: #34495e;
        margin-top: 14pt;
        margin-bottom: 6pt;
        page-break-after: avoid;
    }}

    /* ── Horizontal rules ── */
    hr {{
        border: none;
        border-top: 1px solid #e0e0e0;
        margin: 16pt 0;
    }}

    /* ── Charts ── */
    img {{
        width: 100%;
        display: block;
        margin: 8pt 0 16pt 0;
        page-break-inside: avoid;
        page-break-before: auto;
    }}

    h2 + p img,
    h2 + img {{
        page-break-before: avoid;
    }}

    /* ── Summary tables ── */
    table {{
        border-collapse: collapse;
        width: 100%;
        margin-bottom: 12pt;
        font-size: 8.5pt;
    }}

    td, th {{
        padding: 4pt 6pt;
        text-align: left;
        vertical-align: top;
        border: 1px solid #dddddd;
    }}

    th {{
        background-color: #e0e0e0;
        font-weight: 600;
        font-size: 8.5pt;
    }}

    tr:nth-child(even) td {{
        background-color: #f9f9f9;
    }}

    /* Right-align the label column in summary tables only */
    .summary-tables td:first-child {{
        text-align: right;
        font-weight: 600;
        white-space: nowrap;
        width: 35%;
    }}

    /* ── Measurements table — compact to fit all columns ── */
    .measurements-table table {{
        font-size: 6.5pt;
        width: 100%;
    }}

    .measurements-table th {{
        background-color: #2c3e50;
        color: white;
        font-size: 6.5pt;
        text-align: center;
        padding: 3pt 2pt;
    }}

    .measurements-table td {{
        padding: 3pt 2pt;
        font-size: 6.5pt;
    }}

    .measurements-table tr:nth-child(even) td {{
        background-color: #f0f4f8;
    }}

    /* ── Italic text ── */
    em {{
        color: #888888;
        font-style: italic;
    }}

    /* ── Page break control ── */
    .page-break {{
        page-break-before: always;
    }}
    """


# ── HTML builder ──────────────────────────────────────────────────────────────

def _markdown_to_html(md_content: str, child_name: str, sex: str) -> str:
    """
    Convert markdown content to a complete HTML document.

    Pre-processes the markdown to handle the centered title div that
    the python-markdown parser doesn't convert correctly. Extracts the
    title and generated date and renders them as styled HTML directly.
    The measurements table section is wrapped in a div for targeted styling.

    Args:
        md_content (str): The markdown report content.
        child_name (str): The child's name for the page title.
        sex (str): 'M' or 'F' — determines title font.

    Returns:
        str: Complete HTML document as a string.
    """
    import markdown as markdown_module

    # Extract and remove the centered title block before markdown conversion.
    # The block looks like:
    #   <div align="center">
    #   # Child Name — Growth Report
    #   *Generated on May 28, 2026*
    #   </div>
    title_html = ""
    title_pattern = re.compile(
        r'<div align="center">\s*\n'
        r'#\s+(.+?)\n'
        r'\*Generated on (.+?)\*\s*\n'
        r'</div>',
        re.DOTALL
    )
    match = title_pattern.search(md_content)
    if match:
        title_text = match.group(1).strip()
        generated_date = match.group(2).strip()
        # Extract just the child name (everything before " -")
        child_name_only = title_text.split(" -")[0].strip()
        title_html = (
            f'<h1>{title_text}</h1>\n'
            f'<span class="footer-name">{child_name_only}</span>\n'
            f'<p class="generated-date">'
            f'<em>Generated on {generated_date}</em></p>\n'
            f'<hr>\n'
        )
        md_content = title_pattern.sub("", md_content)

    # Convert remaining markdown to HTML with table support
    md = markdown_module.Markdown(extensions=["tables", "extra"])
    body_html = md.convert(md_content)

    # Wrap the measurements table section for targeted CSS
    body_html = body_html.replace(
        "<h2>Measurements</h2>",
        '</div><div class="measurements-table"><h2>Measurements</h2>'
    )
    body_html = body_html.replace(
        "<h2>Summary</h2>",
        '<div class="summary-tables"><h2>Summary</h2>'
    )
    body_html = body_html.replace(
        "<h2>Height</h2>",
        '</div><h2>Height</h2>'
    )

    css = _build_css()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{child_name} — Growth Report</title>
    <style>
{css}
    </style>
</head>
<body>
<div>
{title_html}
{body_html}
</div>
</body>
</html>"""


def _rewrite_image_paths(html: str, base_dir: Path) -> str:
    """
    Rewrite relative image paths in HTML to absolute file:// URIs.

    WeasyPrint requires absolute paths to embed local images. The markdown
    report uses relative paths like ../charts/alex_height.png which need
    to be resolved relative to the reports directory.

    Args:
        html (str): The HTML content with potentially relative image paths.
        base_dir (Path): The directory the report file lives in, used as
                         the base for resolving relative paths.

    Returns:
        str: HTML content with all image src attributes using absolute paths.
    """

    def replace_src(match: re.Match) -> str:
        src = match.group(1)
        # Skip already-absolute paths and http URLs
        if src.startswith(("http://", "https://", "file://", "/")):
            return match.group(0)
        abs_path = (base_dir / src).resolve()
        return f'src="file://{abs_path}"'

    return re.sub(r'src="([^"]*)"', replace_src, html)


# ── Public API ────────────────────────────────────────────────────────────────

def generate_pdf(
    report_path: Path,
    sex: str,
    output_path: Path | None = None,
) -> Path:
    """
    Generate a PDF from a markdown growth report file.

    Reads the markdown report, converts it to styled HTML, resolves
    image paths, and renders to PDF using WeasyPrint.

    Args:
        report_path (Path): Path to the markdown report file.
        sex (str): The child's sex ('M' or 'F'). Reserved for future
                   use — currently unused since all reports use Open Sans.
        output_path (Path | None): Path to save the PDF. If None, saves
                                   alongside the markdown file with .pdf
                                   extension.

    Returns:
        Path: Path to the saved PDF file.

    Raises:
        ImportError: If weasyprint or markdown are not installed.
        FileNotFoundError: If the markdown report file does not exist.
    """
    if not WEASYPRINT_AVAILABLE:
        raise ImportError(
            "PDF generation requires weasyprint and markdown. "
            "Install them with: pip install weasyprint markdown\n"
            "On Mac you also need: brew install pango"
        )

    # Deferred imports — only reached when WEASYPRINT_AVAILABLE is True
    from weasyprint import HTML as WeasyHTML, CSS as WeasyCSS  # type: ignore[import]
    from weasyprint.text.fonts import FontConfiguration as WeasyFontConfig  # type: ignore[import]

    report_path = Path(report_path)
    if not report_path.exists():
        raise FileNotFoundError(f"Report file not found: {report_path}")

    if output_path is None:
        output_path = report_path.with_suffix(".pdf")

    md_content = report_path.read_text(encoding="utf-8")

    child_name = "Growth Report"
    for line in md_content.splitlines():
        if line.startswith("# "):
            child_name = line[2:].split(" —")[0].strip()
            break

    html = _markdown_to_html(md_content, child_name, sex)
    html = _rewrite_image_paths(html, report_path.parent)

    font_config = WeasyFontConfig()
    html_obj = WeasyHTML(string=html, base_url=str(report_path.parent))
    css_obj = WeasyCSS(string=_build_css(), font_config=font_config)
    html_obj.write_pdf(
        str(output_path),
        stylesheets=[css_obj],
        font_config=font_config,
    )

    return output_path