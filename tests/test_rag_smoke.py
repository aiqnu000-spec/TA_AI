"""
Test khói - chạy KHÔNG cần Ollama: thay embedding và LLM bằng bản giả.
Kiểm tra: đọc 4 định dạng, chia chunk, index tăng dần, xóa file, từ chối khi ngoài tài liệu.
Chạy:  pytest -q
"""
import hashlib
import math
import os
import re
import tempfile
import unicodedata
from pathlib import Path

from vesion_new.rag import embedder

_tmp = tempfile.mkdtemp()
os.environ["RAG_DOCS_DIR"] = str(Path(_tmp) / "docs")
os.environ["RAG_INDEX_DIR"] = str(Path(_tmp) / "index")

import pytest  # noqa: E402

from vesion_new.rag import query  # noqa: E402
from vesion_new.rag.chunker import split_text  # noqa: E402
from vesion_new.rag.ingest import ingest  # noqa: E402
from vesion_new.rag.loaders import normalize  # noqa: E402
from vesion_new.rag.settings import DOCS_DIR  # noqa: E402
from vesion_new.rag.store import Store  # noqa: E402

DIM = 256


def _words(t: str) -> list[str]:
    return re.findall(r"\w+", unicodedata.normalize("NFC", t).lower())


def fake_embed(texts):
    """Embedding giả: đếm từ băm vào 256 chiều -> câu chung nhiều từ thì giống nhau."""
    out = []
    for t in texts:
        v = [0.0] * DIM
        for w in _words(t):
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % DIM] += 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        out.append([x / n for x in v])
    return out


@pytest.fixture(scope="module")
def store():
    embedder.embed = fake_embed
    query._call_llm = lambda messages, on_token: "Bảo hành 24 tháng [1]"
    query.MIN_SCORE = 0.25

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "bao_hanh.txt").write_text(
        "Chính sách bảo hành\n\nThời hạn bảo hành sản phẩm là 24 tháng kể từ ngày mua hàng.", encoding="utf-8")
    (DOCS_DIR / "nau_an.md").write_text("# Nấu cơm\n\nVo gạo, cho nước, bấm nút nấu cơm.", encoding="utf-8")

    import docx
    d = docx.Document(); d.add_paragraph("Quy trình xin nghỉ phép: gửi đơn cho trưởng phòng trước ba ngày.")
    d.save(DOCS_DIR / "nghi_phep.docx")

    import pymupdf
    pdf = pymupdf.open(); page = pdf.new_page()
    page.insert_text((72, 72), "Hoa don dien tu: thue gia tri gia tang la muoi phan tram.")
    pdf.new_page()                                   # trang trắng -> phải bị bỏ qua
    pdf.save(DOCS_DIR / "hoa_don.pdf")

    s = Store()
    ingest(s)
    return s


def test_normalize_nfc():
    nfd = unicodedata.normalize("NFD", "Việt Nam")
    assert normalize(nfd) == "Việt Nam"


def test_chunker_respects_size():
    text = ". ".join(f"Câu số {i} có nội dung khá dài để thử chia đoạn" for i in range(200))
    chunks = split_text(text, size=300, overlap=50)
    assert len(chunks) > 5
    assert all(len(c) <= 360 for c in chunks)


def test_ingest_all_formats(store):
    names = {d.path for d in store.list_docs()}
    assert names == {"bao_hanh.txt", "nau_an.md", "nghi_phep.docx", "hoa_don.pdf"}
    assert all(d.status == "ok" for d in store.list_docs())
    assert store.stats()["chunks"] >= 4


def test_ask_finds_right_source(store):
    ans = query.ask(store, "Thời hạn bảo hành là bao lâu?")
    assert ans.found and ans.hits[0].source == "bao_hanh.txt"
    assert ans.cited[0][1].source == "bao_hanh.txt"


def test_pdf_has_page_number(store):
    hits = query.retrieve(store, "thuế giá trị gia tăng")
    top = next(h for h in hits if h.source == "hoa_don.pdf")
    assert top.page == 1


def test_refuses_out_of_scope(store):
    ans = query.ask(store, "Giá bitcoin hôm nay bao nhiêu zzz qqq")
    assert not ans.found and ans.text == query.NOT_FOUND


def test_incremental_and_delete(store):
    rep = ingest(store)
    assert rep.unchanged == 4 and rep.added == 0 and rep.updated == 0

    (DOCS_DIR / "nau_an.md").unlink()
    rep = ingest(store)
    assert rep.removed == 1
    assert "nau_an.md" not in {d.path for d in store.list_docs()}
