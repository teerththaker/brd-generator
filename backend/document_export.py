"""
Converts the Markdown BRD produced by Claude into downloadable .docx and
.pdf files. Kept intentionally dependency-light (python-docx + fpdf2) and
regex-free where possible so it's easy to extend.
"""

import io
import re
from typing import List

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from fpdf import FPDF


def _split_bold(text: str) -> List[tuple]:
    """Split a line on **bold** markers, returning (text, is_bold) chunks."""
    parts = []
    tokens = text.split("**")
    for i, token in enumerate(tokens):
        if token == "":
            continue
        parts.append((token, i % 2 == 1))
    return parts or [(text, False)]


def _add_markdown_paragraph(doc: Document, line: str):
    para = doc.add_paragraph()
    for chunk, is_bold in _split_bold(line):
        run = para.add_run(chunk)
        run.bold = is_bold
        run.font.size = Pt(11)


def _is_table_row(line: str) -> bool:
    return line.strip().startswith("|") and line.strip().endswith("|")


def _is_table_separator(line: str) -> bool:
    stripped = line.strip().strip("|")
    return bool(stripped) and all(c in "-: " for c in stripped)


def markdown_to_docx(markdown_text: str, title: str = "Business Requirements Document") -> bytes:
    """
    Convert a Markdown string into a formatted .docx file, returned as bytes
    ready to hand to Streamlit's download_button.
    """
    doc = Document()

    # Title page heading
    heading = doc.add_heading(title, level=0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

    lines = markdown_text.split("\n")
    i = 0
    n = len(lines)

    while i < n:
        raw_line = lines[i]
        line = raw_line.rstrip()

        if not line.strip():
            i += 1
            continue

        # Headings
        if line.startswith("#### "):
            doc.add_heading(line[5:].strip(), level=4)
        elif line.startswith("### "):
            doc.add_heading(line[4:].strip(), level=3)
        elif line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=2)
        elif line.startswith("# "):
            doc.add_heading(line[2:].strip(), level=1)

        # Tables
        elif _is_table_row(line):
            table_lines = []
            while i < n and _is_table_row(lines[i]):
                table_lines.append(lines[i].strip())
                i += 1
            i -= 1  # step back since outer loop will increment

            rows = [
                [cell.strip() for cell in row.strip("|").split("|")]
                for row in table_lines
                if not _is_table_separator(row)
            ]
            if rows:
                table = doc.add_table(rows=len(rows), cols=len(rows[0]))
                table.style = "Light Grid Accent 1"
                for r_idx, row_cells in enumerate(rows):
                    for c_idx, cell_text in enumerate(row_cells):
                        if c_idx < len(table.rows[r_idx].cells):
                            table.rows[r_idx].cells[c_idx].text = cell_text
                doc.add_paragraph("")

        # Bullet lists
        elif line.strip().startswith(("- ", "* ")):
            para = doc.add_paragraph(style="List Bullet")
            for chunk, is_bold in _split_bold(line.strip()[2:]):
                run = para.add_run(chunk)
                run.bold = is_bold

        # Numbered lists (e.g. "1. text" or "FR-1: text")
        elif re.match(r"^\d+\.\s", line.strip()):
            para = doc.add_paragraph(style="List Number")
            content = re.sub(r"^\d+\.\s", "", line.strip())
            for chunk, is_bold in _split_bold(content):
                run = para.add_run(chunk)
                run.bold = is_bold

        # Plain paragraph
        else:
            _add_markdown_paragraph(doc, line.strip())

        i += 1

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.read()


_UNICODE_REPLACEMENTS = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u2022": "-",
    "\u00a0": " ",
}


def _latin1_safe(text: str) -> str:
    """
    The built-in PDF core fonts (Helvetica/Courier) only support latin-1.
    Claude's Markdown output often contains smart quotes, en/em dashes, and
    other typographic characters, so normalize those and drop anything else
    that still doesn't fit rather than crashing the export.
    """
    for src, replacement in _UNICODE_REPLACEMENTS.items():
        text = text.replace(src, replacement)
    return text.encode("latin-1", errors="replace").decode("latin-1")


class _BRDPdf(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def markdown_to_pdf(markdown_text: str, title: str = "Business Requirements Document") -> bytes:
    """
    Convert Markdown to a simple, readable PDF. Tables are rendered as
    indented pipe-separated text rather than a full grid, keeping the
    converter lightweight and dependency-free beyond fpdf2.
    """
    pdf = _BRDPdf()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 10, _latin1_safe(title), align="C")
    pdf.ln(4)

    for raw_line in markdown_text.split("\n"):
        line = raw_line.rstrip()
        clean = _latin1_safe(line.strip().replace("**", ""))

        if not clean:
            pdf.ln(2)
            continue

        pdf.set_x(pdf.l_margin)

        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            pdf.multi_cell(0, 9, clean[2:])
        elif line.startswith("## "):
            pdf.set_font("Helvetica", "B", 14)
            pdf.multi_cell(0, 8, clean[3:])
        elif line.startswith("### "):
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 7, clean[4:])
        elif line.strip().startswith(("- ", "* ")):
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 6, f"    - {clean.lstrip('-* ').strip()}")
        elif _is_table_row(line):
            pdf.set_font("Courier", "", 9)
            pdf.multi_cell(0, 5, clean)
        else:
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 6, clean)

    return bytes(pdf.output(dest="S"))
