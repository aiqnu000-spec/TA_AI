"""
1.2 (phần 1) - Chia văn bản thành các đoạn (chunk) có gối đầu (overlap).

Cách chia: gom theo đoạn văn -> nếu đoạn quá dài thì tách theo câu -> gom lại đến
~CHUNK_SIZE ký tự. Mỗi chunk giữ số trang để trích dẫn.
"""
import re
from dataclasses import dataclass

from .loaders import Segment
from .settings import CHUNK_OVERLAP, CHUNK_SIZE


@dataclass
class Chunk:
    text: str
    page: int | None
    index: int  # thứ tự chunk trong cả tài liệu (bắt đầu từ 1)


def _pieces(text: str, size: int):
    """Cắt văn bản thành các mảnh nhỏ hơn `size`, ưu tiên ranh giới đoạn rồi đến câu."""
    for para in re.split(r"\n\s*\n", text):
        para = " ".join(para.split())  # gộp xuống dòng thừa (PDF hay ngắt dòng giữa câu)
        if not para:
            continue
        if len(para) <= size:
            yield para
            continue
        for sent in re.split(r"(?<=[.!?…;:])\s+", para):
            while len(sent) > size:    # câu cực dài: cắt cứng
                yield sent[:size]
                sent = sent[size:]
            if sent:
                yield sent


def split_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks: list[str] = []
    cur = ""
    for piece in _pieces(text, size):
        if cur and len(cur) + 1 + len(piece) > size:
            chunks.append(cur)
            tail = cur[-overlap:] if overlap > 0 else ""
            sp = tail.find(" ")                 # bỏ nửa từ ở đầu phần gối đầu
            tail = tail[sp + 1:] if sp != -1 else ""
            cur = f"{tail} {piece}".strip()
        else:
            cur = f"{cur} {piece}" if cur else piece
    if cur:
        chunks.append(cur)
    return chunks


def make_chunks(segments: list[Segment]) -> list[Chunk]:
    out: list[Chunk] = []
    for seg in segments:
        for text in split_text(seg.text):
            out.append(Chunk(text=text, page=seg.page, index=len(out) + 1))
    return out
