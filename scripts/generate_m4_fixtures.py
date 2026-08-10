from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


FONT_CANDIDATES = (
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/PingFang.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
)
DOCX_FONT = "Arial Unicode MS"
PDF_FONT_NAME = "PolicyCJK"


@dataclass(frozen=True)
class PolicyBlock:
    kind: str
    text: str


def parse_markdown(path: Path) -> list[PolicyBlock]:
    blocks: list[PolicyBlock] = []
    skipping_explanation = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            skipping_explanation = False
            continue
        if line.startswith(">"):
            skipping_explanation = True
            continue
        if skipping_explanation:
            continue
        if line.startswith("# "):
            blocks.append(PolicyBlock("title", line.removeprefix("# ").strip()))
        elif line.startswith("## "):
            blocks.append(PolicyBlock("chapter", line.removeprefix("## ").strip()))
        else:
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
            blocks.append(PolicyBlock("body", clean))
    if not blocks or blocks[0].kind != "title":
        raise ValueError(f"制度测试文件缺少一级标题：{path}")
    return blocks


def _set_run_font(run, name: str, size: int, bold: bool = False, color: str = "000000") -> None:
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)


def write_docx(blocks: list[PolicyBlock], output_path: Path) -> None:
    document = Document()
    section = document.sections[0]
    section.start_type = WD_SECTION.NEW_PAGE
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.right_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    normal = document.styles["Normal"]
    normal.font.name = DOCX_FONT
    normal.font.size = Pt(11)
    normal._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), DOCX_FONT)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.1

    heading = document.styles["Heading 1"]
    heading.font.name = DOCX_FONT
    heading.font.size = Pt(16)
    heading.font.bold = True
    heading.font.color.rgb = RGBColor.from_string("2E74B5")
    heading._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), DOCX_FONT)
    heading.paragraph_format.space_before = Pt(16)
    heading.paragraph_format.space_after = Pt(8)
    heading.paragraph_format.keep_with_next = True

    for block in blocks:
        if block.kind == "title":
            paragraph = document.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_after = Pt(14)
            _set_run_font(paragraph.add_run(block.text), DOCX_FONT, 18, bold=True, color="0B2545")
        elif block.kind == "chapter":
            document.add_paragraph(block.text, style="Heading 1")
        else:
            paragraph = document.add_paragraph(block.text, style="Normal")
            paragraph.paragraph_format.first_line_indent = Inches(0.35)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)


def _pdf_font_path() -> Path:
    for candidate in FONT_CANDIDATES:
        if candidate.exists() and candidate.suffix.lower() == ".ttf":
            return candidate
    raise FileNotFoundError("未找到可嵌入 PDF 的中文 TrueType 字体")


def write_pdf(blocks: list[PolicyBlock], output_path: Path) -> None:
    if PDF_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(PDF_FONT_NAME, str(_pdf_font_path())))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
        title=blocks[0].text,
        author="制度智能审查系统测试数据",
    )
    base = getSampleStyleSheet()
    body = ParagraphStyle(
        "PolicyBody",
        parent=base["BodyText"],
        fontName=PDF_FONT_NAME,
        fontSize=11,
        leading=15,
        spaceAfter=6,
        firstLineIndent=22,
        textColor=HexColor("#000000"),
        wordWrap="CJK",
    )
    chapter = ParagraphStyle(
        "PolicyChapter",
        parent=body,
        fontSize=16,
        leading=20,
        spaceBefore=16,
        spaceAfter=8,
        firstLineIndent=0,
        textColor=HexColor("#2E74B5"),
        keepWithNext=True,
    )
    title = ParagraphStyle(
        "PolicyTitle",
        parent=body,
        fontSize=18,
        leading=23,
        spaceAfter=14,
        firstLineIndent=0,
        alignment=TA_CENTER,
        textColor=HexColor("#0B2545"),
    )
    styles = {"title": title, "chapter": chapter, "body": body}
    story = []
    for block in blocks:
        story.append(Paragraph(html.escape(block.text), styles[block.kind]))
        if block.kind == "title":
            story.append(Spacer(1, 2))
    document.build(story)


def generate_all(source_root: Path, output_root: Path) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    sources = sorted(source_root.rglob("待审查_*.md"))
    if len(sources) != 4:
        raise ValueError(f"应找到 4 份待审制度 Markdown，实际找到 {len(sources)} 份")
    for source in sources:
        blocks = parse_markdown(source)
        stem = source.stem
        docx_path = output_root / f"{stem}.docx"
        pdf_path = output_root / f"{stem}.pdf"
        write_docx(blocks, docx_path)
        write_pdf(blocks, pdf_path)
        pairs.append((docx_path, pdf_path))
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 M4 DOCX 和文字 PDF 测试文件")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    generate_all(args.source_root, args.output_root)


if __name__ == "__main__":
    main()
