"""
1.2 (phần 3) - Lưu trữ: ChromaDB (vector) + SQLite (sổ theo dõi tài liệu).

- ChromaDB giữ các chunk + vector để tìm kiếm.
- SQLite `manifest.db` giữ thông tin từng FILE (hash, dung lượng, trạng thái...)
  để lần sau chỉ xử lý file mới/đã sửa - quan trọng khi có hàng nghìn file,
  và là nguồn dữ liệu cho lệnh /docs ở giai đoạn 2.
"""
import sqlite3
from dataclasses import dataclass
from datetime import datetime

import chromadb

from .chunker import Chunk
from .settings import INDEX_DIR

_ADD_BATCH = 500  # Chroma giới hạn số bản ghi mỗi lần add


@dataclass
class DocRow:
    path: str          # đường dẫn tương đối so với thư mục kho
    sha256: str
    size: int
    mtime: int
    n_chunks: int
    status: str        # ok | empty | needs_ocr | error
    note: str
    indexed_at: str


@dataclass
class Hit:
    text: str
    source: str
    page: int          # 0 nếu không có số trang
    chunk: int
    score: float       # cosine similarity, càng gần 1 càng giống

    @property
    def label(self) -> str:
        where = f"trang {self.page}" if self.page else f"đoạn {self.chunk}"
        return f"{self.source} - {where}"


class Store:
    def __init__(self) -> None:
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        self._chroma = chromadb.PersistentClient(path=str(INDEX_DIR / "chroma"))
        self.col = self._chroma.get_or_create_collection(
            "docs", metadata={"hnsw:space": "cosine"}
        )
        self.db = sqlite3.connect(INDEX_DIR / "manifest.db")
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS docs (
                   path TEXT PRIMARY KEY, sha256 TEXT, size INTEGER, mtime INTEGER,
                   n_chunks INTEGER, status TEXT, note TEXT, indexed_at TEXT)"""
        )
        self.db.commit()

    # ---- sổ tài liệu -------------------------------------------------------
    def get_doc(self, path: str) -> DocRow | None:
        row = self.db.execute("SELECT * FROM docs WHERE path=?", (path,)).fetchone()
        return DocRow(*row) if row else None

    def list_docs(self) -> list[DocRow]:
        rows = self.db.execute("SELECT * FROM docs ORDER BY path").fetchall()
        return [DocRow(*r) for r in rows]

    def _save_doc(self, d: DocRow) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO docs VALUES (?,?,?,?,?,?,?,?)",
            (d.path, d.sha256, d.size, d.mtime, d.n_chunks, d.status, d.note, d.indexed_at),
        )
        self.db.commit()

    def touch_doc(self, path: str, mtime: int) -> None:
        """File đổi ngày sửa nhưng nội dung y hệt -> chỉ cập nhật mtime."""
        self.db.execute("UPDATE docs SET mtime=? WHERE path=?", (mtime, path))
        self.db.commit()

    # ---- ghi / xóa ---------------------------------------------------------
    def replace_doc(self, path: str, sha256: str, size: int, mtime: int,
                    chunks: list[Chunk], vectors: list[list[float]],
                    status: str = "ok", note: str = "") -> None:
        # Xóa chunk cũ TRƯỚC, ghi chunk mới, rồi mới cập nhật sổ.
        # Nếu chương trình chết giữa chừng, sổ chưa cập nhật => lần sau tự làm lại.
        self.col.delete(where={"source": path})
        for i in range(0, len(chunks), _ADD_BATCH):
            part = chunks[i:i + _ADD_BATCH]
            self.col.add(
                ids=[f"{path}::{c.index}" for c in part],
                documents=[c.text for c in part],
                embeddings=vectors[i:i + _ADD_BATCH],
                metadatas=[{"source": path, "page": c.page or 0, "chunk": c.index} for c in part],
            )
        self._save_doc(DocRow(path, sha256, size, mtime, len(chunks), status, note,
                              datetime.now().isoformat(timespec="seconds")))

    def mark_doc(self, path: str, sha256: str, size: int, mtime: int,
                 status: str, note: str = "") -> None:
        """Ghi nhận file không có chunk nào (rỗng / scan / lỗi)."""
        self.col.delete(where={"source": path})
        self._save_doc(DocRow(path, sha256, size, mtime, 0, status, note,
                              datetime.now().isoformat(timespec="seconds")))

    def delete_doc(self, path: str) -> None:
        self.col.delete(where={"source": path})
        self.db.execute("DELETE FROM docs WHERE path=?", (path,))
        self.db.commit()

    # ---- truy vấn ----------------------------------------------------------
    def query(self, vector: list[float], k: int) -> list[Hit]:
        if self.col.count() == 0:
            return []
        res = self.col.query(query_embeddings=[vector], n_results=k)
        hits = []
        for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            hits.append(Hit(text, meta["source"], int(meta["page"]), int(meta["chunk"]),
                            score=1.0 - float(dist)))
        return hits

    def stats(self) -> dict:
        docs = self.list_docs()
        by_status: dict[str, int] = {}
        for d in docs:
            by_status[d.status] = by_status.get(d.status, 0) + 1
        return {"files": len(docs), "chunks": self.col.count(), "by_status": by_status}
