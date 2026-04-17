import io

from docx import Document
from pypdf import PdfReader


def extract_text_from_file(filename: str, content: bytes) -> str:
    lower = filename.lower()
    if lower.endswith('.pdf'):
        return _extract_pdf(content)
    if lower.endswith('.docx'):
        return _extract_docx(content)

    # Fallback for text-like files (or if extension is missing).
    try:
        return content.decode('utf-8', errors='ignore')
    except Exception:
        return ''


def _extract_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    pages = [page.extract_text() or '' for page in reader.pages]
    return '\n'.join(pages)


def _extract_docx(content: bytes) -> str:
    document = Document(io.BytesIO(content))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return '\n'.join(paragraphs)
