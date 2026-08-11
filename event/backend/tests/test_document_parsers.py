import importlib
import re
from pathlib import Path

import fitz
import pytest
from docx import Document


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPOSITORY_ROOT / "制度审查测试数据集" / "生成文件"


def parser_api():
    try:
        parsers = importlib.import_module("app.parsers")
        segmenter = importlib.import_module("app.parsers.segmenter")
    except ModuleNotFoundError as exc:
        pytest.fail(f"M4 解析模块尚未实现：{exc}")
    return parsers, segmenter


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", value)


def parse_clauses(path: Path):
    parsers, segmenter = parser_api()
    paragraphs = parsers.parser_for(path).extract(path)
    return segmenter.ClauseSegmenter().segment(paragraphs)


@pytest.mark.parametrize(
    "stem",
    [
        "待审查_章程配套制度_含上下级口径冲突",
        "待审查_综合审查样例",
        "待审查_资金与关联交易_含关联冲突",
        "待审查_重大事项管理_含流程冲突",
    ],
)
def test_docx_and_pdf_produce_matching_article_numbers_and_text(stem):
    docx_clauses = parse_clauses(FIXTURE_ROOT / f"{stem}.docx")
    pdf_clauses = parse_clauses(FIXTURE_ROOT / f"{stem}.pdf")

    assert [item.original_no for item in docx_clauses] == [item.original_no for item in pdf_clauses]
    assert [normalize(item.content) for item in docx_clauses] == [normalize(item.content) for item in pdf_clauses]


def test_segmenter_preserves_number_gap_heading_path_and_reference_text():
    clauses = parse_clauses(FIXTURE_ROOT / "待审查_综合审查样例.docx")

    assert [item.original_no for item in clauses] == [
        "第一条",
        "第二条",
        "第三条",
        "第四条",
        "第五条",
        "第六条",
        "第七条",
        "第八条",
        "第九条",
        "第十一条",
        "第十二条",
        "第十三条",
        "第十四条",
    ]
    ninth = next(item for item in clauses if item.original_no == "第九条")
    assert ninth.heading_path == ["第三章 审批与备案"]
    assert "《专项事项管理制度》第十八条" in ninth.content


def test_docx_extractor_ignores_table_text(tmp_path):
    path = tmp_path / "table.docx"
    document = Document()
    document.add_paragraph("第一章 总则")
    document.add_paragraph("第一条 正文条款。")
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "第二条 表格内容不得被解析。"
    document.save(path)

    clauses = parse_clauses(path)

    assert [item.original_no for item in clauses] == ["第一条"]
    assert "表格内容" not in clauses[0].content


def test_blank_pdf_is_rejected_as_scanned_without_ocr(tmp_path):
    parsers, _ = parser_api()
    path = tmp_path / "scanned.pdf"
    with fitz.open() as document:
        document.new_page()
        document.save(path)

    with pytest.raises(parsers.ScannedPdfError, match="扫描"):
        parsers.parser_for(path).extract(path)


def test_pdf_visual_line_wrap_does_not_insert_spaces_inside_chinese_words():
    clauses = parse_clauses(
        FIXTURE_ROOT / "待审查_重大事项管理_含流程冲突.pdf"
    )
    fifth = next(item for item in clauses if item.original_no == "第五条")

    assert "部门负责人" in fifth.content
    assert "负 责人" not in fifth.content


@pytest.mark.parametrize("name", ["制度.doc", "制度.png", "制度.txt"])
def test_unsupported_document_type_is_rejected(name, tmp_path):
    parsers, _ = parser_api()
    path = tmp_path / name
    path.write_bytes(b"not a supported document")

    with pytest.raises(parsers.UnsupportedDocumentError, match="仅支持"):
        parsers.parser_for(path)


@pytest.mark.parametrize("suffix", [".docx", ".pdf"])
def test_corrupt_supported_document_has_readable_parse_error(suffix, tmp_path):
    parsers, _ = parser_api()
    path = tmp_path / f"broken{suffix}"
    path.write_bytes(b"broken")

    with pytest.raises(parsers.DocumentParseError, match="无法解析"):
        parsers.parser_for(path).extract(path)
