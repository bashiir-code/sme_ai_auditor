"""
pdf_converter.py
----------------
Creates immutable PDF compliance proofs from Markdown reports.
Professional EU regulatory report style — structured, clean, no emoji.
"""

import os
import re
import structlog
import markdown
from weasyprint import HTML

logger = structlog.get_logger(__name__)

# ── Risk tier colour mapping (used to inject a coloured banner) ───────────────
RISK_COLOURS = {
    "prohibited": {"bg": "#7f1d1d", "fg": "#fee2e2", "label": "PROHIBITED"},
    "high":       {"bg": "#7c2d12", "fg": "#fed7aa", "label": "HIGH RISK"},
    "limited":    {"bg": "#713f12", "fg": "#fef9c3", "label": "LIMITED RISK"},
    "minimal":    {"bg": "#14532d", "fg": "#dcfce7", "label": "MINIMAL RISK"},
}


def _detect_risk(html_body: str) -> dict:
    """Scan the HTML for the risk level keyword and return colour config."""
    lower = html_body.lower()
    for key, cfg in RISK_COLOURS.items():
        if key in lower:
            return cfg
    return {"bg": "#1e3a5f", "fg": "#e0f2fe", "label": "RISK LEVEL ASSESSED"}


CSS = """
/* ── PAGE SETUP ──────────────────────────────────────────────────────── */
@page {
    size: A4;
    margin: 2.4cm 2.6cm 2.8cm 2.6cm;

    @top-left {
        content: "SME AI Auditor";
        font-family: Helvetica, Arial, sans-serif;
        font-size: 7.5pt;
        font-weight: 700;
        color: #94a3b8;
        padding-bottom: 4pt;
        border-bottom: 0.5pt solid #e2e8f0;
    }
    @top-right {
        content: "EU AI Act & Data Act Compliance Report";
        font-family: Helvetica, Arial, sans-serif;
        font-size: 7.5pt;
        color: #94a3b8;
        padding-bottom: 4pt;
        border-bottom: 0.5pt solid #e2e8f0;
    }
    @bottom-left {
        content: "CONFIDENTIAL — For internal use only";
        font-family: Helvetica, Arial, sans-serif;
        font-size: 7pt;
        color: #cbd5e1;
    }
    @bottom-right {
        content: "Page " counter(page) " of " counter(pages);
        font-family: Helvetica, Arial, sans-serif;
        font-size: 7pt;
        color: #cbd5e1;
    }
}

/* ── BASE TYPOGRAPHY ─────────────────────────────────────────────────── */
body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.65;
    color: #1e293b;
    background: #ffffff;
    margin: 0;
    padding: 0;
}

/* ── HEADINGS ────────────────────────────────────────────────────────── */
h1 {
    font-size: 20pt;
    font-weight: 800;
    color: #0f172a;
    border-bottom: 2.5pt solid #1e3a5f;
    padding-bottom: 8pt;
    margin-top: 0;
    margin-bottom: 18pt;
    letter-spacing: -0.01em;
    page-break-after: avoid;
}

h2 {
    font-size: 13pt;
    font-weight: 700;
    color: #ffffff;
    background-color: #1e3a5f;
    padding: 7pt 12pt;
    margin-top: 26pt;
    margin-bottom: 12pt;
    border-radius: 3pt;
    page-break-after: avoid;
}

h3 {
    font-size: 11pt;
    font-weight: 700;
    color: #1e3a5f;
    margin-top: 18pt;
    margin-bottom: 6pt;
    padding-bottom: 3pt;
    border-bottom: 1pt solid #e2e8f0;
    page-break-after: avoid;
}

p {
    font-size: 10.5pt;
    color: #334155;
    margin-bottom: 8pt;
}

li {
    font-size: 10.5pt;
    color: #334155;
    margin-bottom: 4pt;
}

strong {
    font-weight: 700;
    color: #0f172a;
}

em {
    color: #64748b;
    font-style: italic;
}

hr {
    border: none;
    border-top: 1pt solid #e2e8f0;
    margin: 22pt 0;
}

/* ── INLINE CODE & MONOSPACE ─────────────────────────────────────────── */
code {
    font-family: "Courier New", Courier, monospace;
    font-size: 8.5pt;
    background: #f1f5f9;
    border: 0.5pt solid #cbd5e1;
    border-radius: 2pt;
    padding: 1pt 4pt;
    color: #0369a1;
}

/* ── BLOCKQUOTE (used for notes / disclaimers) ───────────────────────── */
blockquote {
    border-left: 3.5pt solid #3b82f6;
    background: #f0f7ff;
    margin: 14pt 0;
    padding: 10pt 14pt;
    border-radius: 0 4pt 4pt 0;
}

blockquote p {
    margin: 0;
    font-size: 10pt;
    color: #1e3a5f;
    font-style: italic;
}

/* ── TABLES ──────────────────────────────────────────────────────────── */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 14pt 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
}

thead tr {
    background: #1e3a5f;
    color: #ffffff;
}

th {
    padding: 8pt 10pt;
    font-size: 8.5pt;
    font-weight: 700;
    text-align: left;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    border: none;
}

td {
    padding: 7pt 10pt;
    border-bottom: 0.5pt solid #e2e8f0;
    color: #334155;
    vertical-align: top;
}

tbody tr:nth-child(even) {
    background: #f8fafc;
}

/* Colour-code PASS/FAIL cells */
td:contains("PASS") { color: #15803d; font-weight: 700; }
td:contains("FAIL") { color: #b91c1c; font-weight: 700; }

/* ── STATUS BANNER (injected via Python below HTML body) ─────────────── */
.status-banner {
    padding: 12pt 18pt;
    border-radius: 5pt;
    margin: 18pt 0;
    font-size: 11.5pt;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-align: center;
    page-break-inside: avoid;
}

.status-approved {
    background: #14532d;
    color: #dcfce7;
    border: 1pt solid #16a34a;
}

.status-blocked {
    background: #7f1d1d;
    color: #fee2e2;
    border: 1pt solid #dc2626;
}

/* ── RISK BADGE (inline coloured pill in the scorecard table) ────────── */
.risk-prohibited { background:#7f1d1d; color:#fee2e2; padding:2pt 8pt; border-radius:10pt; font-size:8.5pt; font-weight:700; }
.risk-high       { background:#7c2d12; color:#fed7aa; padding:2pt 8pt; border-radius:10pt; font-size:8.5pt; font-weight:700; }
.risk-limited    { background:#713f12; color:#fef9c3; padding:2pt 8pt; border-radius:10pt; font-size:8.5pt; font-weight:700; }
.risk-minimal    { background:#14532d; color:#dcfce7; padding:2pt 8pt; border-radius:10pt; font-size:8.5pt; font-weight:700; }

/* ── PRIORITY LABELS in remediation table ────────────────────────────── */
td:contains("HIGH")   { color: #b91c1c; font-weight: 700; }
td:contains("MEDIUM") { color: #b45309; font-weight: 700; }
td:contains("LOW")    { color: #1d4ed8; font-weight: 700; }
"""


def _build_html(raw_html: str) -> str:
    """Wrap rendered Markdown in a fully styled HTML document."""
    risk_cfg = _detect_risk(raw_html)

    # Inject a coloured risk banner right after the first <hr> (after the
    # "Report Information" table) so it sits prominently.
    risk_banner = (
        f'<div class="status-banner" '
        f'style="background:{risk_cfg["bg"]};color:{risk_cfg["fg"]};'
        f'border:1pt solid {risk_cfg["bg"]};">'
        f'Risk Classification: {risk_cfg["label"]}'
        f'</div>'
    )
    # Insert after the first </table>
    raw_html = raw_html.replace("</table>", f"</table>{risk_banner}", 1)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>{CSS}</style>
</head>
<body>
{raw_html}
</body>
</html>"""


class PDFConverter:
    """
    Renders Markdown into a professional, styled PDF using WeasyPrint.
    """

    def __init__(self):
        logger.info("PDFConverter initialized")

    def convert_markdown_to_pdf(self, md_filepath: str, output_pdf_path: str) -> str:
        """
        Convert a Markdown file to a styled PDF.

        Args:
            md_filepath: Path to the source Markdown file.
            output_pdf_path: Destination path for the generated PDF.

        Returns:
            Absolute path to the generated PDF.
        """
        if not os.path.exists(md_filepath):
            raise FileNotFoundError(f"Markdown file not found: {md_filepath}")

        logger.info("Starting PDF rendering", input=md_filepath, output=output_pdf_path)

        try:
            with open(md_filepath, "r", encoding="utf-8") as f:
                md_content = f.read()

            raw_html = markdown.markdown(
                md_content,
                extensions=["tables", "fenced_code"]
            )

            styled_html = _build_html(raw_html)

            out_dir = os.path.dirname(os.path.abspath(output_pdf_path))
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)

            HTML(string=styled_html).write_pdf(output_pdf_path)

        except Exception as e:
            logger.error("PDF rendering failed", error=str(e))
            raise RuntimeError(f"Failed to convert Markdown to PDF: {e}") from e

        if not os.path.exists(output_pdf_path) or os.path.getsize(output_pdf_path) == 0:
            raise RuntimeError(f"Generated PDF is empty or missing: {output_pdf_path}")

        logger.info("PDF generated successfully", size_bytes=os.path.getsize(output_pdf_path))
        return os.path.abspath(output_pdf_path)
