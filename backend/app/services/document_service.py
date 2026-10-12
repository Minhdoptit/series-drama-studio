import pdfplumber
import pathlib


def extract_text(file_path: str, ext: str) -> str:
    ext = ext.lower()
    if ext == "pdf":
        return _extract_pdf(file_path)
    elif ext == "docx":
        return _extract_docx(file_path)
    elif ext in ["txt", "md"]:
        return pathlib.Path(file_path).read_text(encoding="utf-8", errors="ignore")
    return ""


def _extract_pdf(file_path: str) -> str:
    texts = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texts.append(t)
    except Exception as e:
        return f"[Lỗi đọc PDF: {e}]"
    return "\n\n".join(texts)


def _extract_docx(file_path: str) -> str:
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        return f"[Lỗi đọc DOCX: {e}]"


def count_tokens(text: str) -> int:
    """Rough estimate: 1 token ≈ 4 characters"""
    return len(text) // 4
