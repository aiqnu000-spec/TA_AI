"""
FR/1.1 - Đọc và làm sạch tài liệu: PDF, DOCX, TXT, MD.

Mỗi file -> danh sách Segment. PDF tách theo TRANG để sau này trích dẫn "trang N".
PDF scan (ảnh) chưa hỗ trợ OCR ở giai đoạn 1: trang không có chữ sẽ bị bỏ qua và đếm lại.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

MIN_PAGE_CHARS = 20  # trang có ít chữ hơn mức này coi là trang ảnh/scan


@dataclass
class Segment:
    text: str
    page: int | None = None  # số trang (PDF); None với DOCX/TXT/MD


@dataclass
class LoadResult:
    segments: list[Segment] = field(default_factory=list)
    skipped_pages: int = 0   # số trang không đọc được chữ (nghi là scan)
    total_pages: int = 0


def normalize(text: str) -> str:
    """Làm sạch văn bản. Bước NFC rất quan trọng với tiếng Việt: cùng một chữ 'ệ'
    có thể được lưu ở dạng tổ hợp hoặc dựng sẵn, nếu không chuẩn hóa thì tìm kiếm
    và so khớp từ khóa sẽ lệch."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00ad", "")            # dấu gạch nối mềm
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_pdf(path: Path) -> LoadResult:
    import pymupdf  # import trễ để file khác vẫn chạy được nếu thiếu thư viện

    res = LoadResult()
    with pymupdf.open(path) as doc:
        res.total_pages = doc.page_count
        for i, page in enumerate(doc, start=1):
            text = normalize(page.get_text("text"))
            if len(text) < MIN_PAGE_CHARS:
                res.skipped_pages += 1
                continue
            res.segments.append(Segment(text, page=i))
    return res


def load_docx(path: Path) -> LoadResult:
    from docx import Document

    doc = Document(str(path))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:                       # bảng: mỗi hàng một dòng "a | b | c"
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    text = normalize("\n\n".join(parts))
    return LoadResult([Segment(text)] if text else [])


def _read_text_file(path: Path) -> str:
    # Thứ tự thử: UTF-8 (có/không BOM) -> UTF-16 -> cp1258 (bảng mã tiếng Việt của Windows)
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-16", "cp1258"):
        try:
            return raw.decode(enc)
        except UnicodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def load_text(path: Path) -> LoadResult:
    text = normalize(_read_text_file(path))
    return LoadResult([Segment(text)] if text else [])


_LOADERS = {
    ".pdf": load_pdf,
    ".docx": load_docx,
    ".txt": load_text,
    ".md": load_text,
}


def load_file(path: Path) -> LoadResult:
    loader = _LOADERS.get(path.suffix.lower())
    if loader is None:
        raise ValueError(f"Định dạng chưa hỗ trợ: {path.suffix}")
    return loader(path)
