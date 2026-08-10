import re
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPOSITORY_ROOT / "制度审查测试数据集"
GENERATOR = REPOSITORY_ROOT / "scripts" / "generate_m4_fixtures.py"


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value)


def extract_docx_text(path: Path) -> str:
    from docx import Document

    return "\n".join(paragraph.text for paragraph in Document(path).paragraphs if paragraph.text.strip())


def extract_pdf_text(path: Path) -> str:
    import fitz

    with fitz.open(path) as document:
        return "\n".join(page.get_text("text") for page in document)


def test_generator_creates_four_matching_docx_and_text_pdf_pairs(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
            "--source-root",
            str(SOURCE_ROOT),
            "--output-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    docx_files = sorted(tmp_path.glob("*.docx"))
    pdf_files = sorted(tmp_path.glob("*.pdf"))
    assert len(docx_files) == len(pdf_files) == 4

    for docx_path, pdf_path in zip(docx_files, pdf_files, strict=True):
        assert docx_path.stem == pdf_path.stem
        docx_text = extract_docx_text(docx_path)
        pdf_text = extract_pdf_text(pdf_path)
        assert "第一章" in docx_text
        assert "说明：本文件为制度审查测试用人工构造样例" not in docx_text
        assert normalize_text(docx_text) == normalize_text(pdf_text)
