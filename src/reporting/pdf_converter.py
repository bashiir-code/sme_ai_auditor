"""
pdf_converter.py
----------------
Creates immutable PDF compliance proofs from Markdown reports.

Essential for maintaining the "Auditor" experience:
Boards and regulators require static snapshots of compliance status.
"""

import os
import structlog
import markdown
from weasyprint import HTML, CSS

logger = structlog.get_logger(__name__)


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
            md_filepath: The absolute path to the generated markdown report.
            output_pdf_path: The target path where the PDF will be written.

        Returns:
            The absolute filepath to the finalized PDF.
            
        Raises:
            FileNotFoundError: If the markdown file does not exist.
            RuntimeError: If the PDF rendering engine fails.
        """
        if not os.path.exists(md_filepath):
            logger.error("Markdown file not found", md_filepath=md_filepath)
            raise FileNotFoundError(f"Input markdown file not found: {md_filepath}")

        logger.info("Starting PDF rendering", input=md_filepath, output=output_pdf_path)

        try:
            # 1. Read the Markdown
            with open(md_filepath, "r", encoding="utf-8") as f:
                md_content = f.read()

            # 2. Convert Markdown to unstyled HTML
            raw_html = markdown.markdown(
                md_content, 
                extensions=['tables', 'fenced_code']
            )

            # 3. Apply professional SME Auditor CSS styling
            styled_html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: sans-serif;
                        color: #1a202c;
                        line-height: 1.5;
                        margin: 0;
                    }}
                    h1 {{
                        color: #2d3748;
                        border-bottom: 1px solid #cbd5e0;
                        font-size: 24pt;
                    }}
                    h2 {{
                        color: #2d3748;
                        margin-top: 20pt;
                        font-size: 18pt;
                    }}
                    h3 {{
                        color: #4a5568;
                        font-size: 14pt;
                    }}
                    p, li {{
                        font-size: 11pt;
                    }}
                    code {{
                        background-color: #edf2f7;
                        padding: 1pt 3pt;
                        font-family: monospace;
                        font-size: 10pt;
                    }}
                    blockquote {{
                        border-left: 3pt solid #e2e8f0;
                        padding-left: 10pt;
                        margin: 10pt 0;
                        color: #718096;
                        font-style: italic;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 15pt 0;
                    }}
                    th, td {{
                        border: 1pt solid #e2e8f0;
                        padding: 8pt;
                        text-align: left;
                    }}
                    @page {{
                        size: A4;
                        margin: 2.5cm;
                        @bottom-center {{
                            content: "Audit Proof | Page " counter(page);
                            font-size: 9pt;
                            color: #a0aec0;
                        }}
                    }}
                </style>
            </head>
            <body>
                {raw_html}
            </body>
            </html>
            """

            # 4. Render to PDF
            pdf_doc = HTML(string=styled_html)
            
            # Ensure the output directory exists
            out_dir = os.path.dirname(os.path.abspath(output_pdf_path))
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)

            pdf_doc.write_pdf(output_pdf_path)
            
        except Exception as e:
            logger.error("WeasyPrint rendering failed", error=str(e), md_filepath=md_filepath)
            raise RuntimeError(f"Failed to convert Markdown to PDF: {e}") from e

        if not os.path.exists(output_pdf_path) or os.path.getsize(output_pdf_path) == 0:
             raise RuntimeError(f"Generated PDF is empty or missing: {output_pdf_path}")

        logger.info("PDF generated successfully", size_bytes=os.path.getsize(output_pdf_path))
        return os.path.abspath(output_pdf_path)
