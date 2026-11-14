"""
1.1 + 1.2 - Quét thư mục kho, chỉ xử lý file mới/đã sửa/đã xóa (cơ sở cho /reindex sau này).
"""
import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import embedder
from .chunker import make_chunks
from .loaders import load_file
from .settings import DOCS_DIR, SUPPORTED_EXT
from .store import Store

log = logging.getLogger(__name__)

# Trạng thái "đã xử lý xong, không cần thử lại nếu file không đổi".
# Riêng "error" thì lần chạy sau sẽ thử lại.
_FINAL_STATUS = {"ok", "empty", "needs_ocr"}


@dataclass
class Report:
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    errors: list[str] = field(default_factory=list)
    needs_ocr: list[str] = field(default_factory=list)


def scan_files(root: Path = DOCS_DIR) -> list[Path]:
    files = []
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in SUPPORTED_EXT:
            continue
        if p.name.startswith("~$"):      # file tạm của Word khi đang mở
            continue
        files.append(p)
    return sorted(files)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def ingest(store: Store, force: bool = False,
           progress: Callable[[str], None] = lambda _msg: None) -> Report:
    report = Report()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    files = scan_files()
    seen: set[str] = set()

    for n, path in enumerate(files, start=1):
        rel = path.relative_to(DOCS_DIR).as_posix()
        seen.add(rel)
        st = path.stat()
        size, mtime = st.st_size, int(st.st_mtime)
        old = store.get_doc(rel)

        # Kiểm tra nhanh bằng dung lượng + ngày sửa (không cần đọc file)
        if (old and not force and old.status in _FINAL_STATUS
                and old.size == size and old.mtime == mtime):
            report.unchanged += 1
            continue

        digest = _sha256(path)
        # Ngày sửa đổi nhưng nội dung y hệt -> bỏ qua
        if old and not force and old.status in _FINAL_STATUS and old.sha256 == digest:
            store.touch_doc(rel, mtime)
            report.unchanged += 1
            continue

        progress(f"[{n}/{len(files)}] {rel}")
        try:
            result = load_file(path)
            chunks = make_chunks(result.segments)
            note = ""
            if result.skipped_pages:
                note = f"{result.skipped_pages}/{result.total_pages} trang không có chữ (nghi là scan)"

            if not chunks:
                status = "needs_ocr" if result.skipped_pages else "empty"
                store.mark_doc(rel, digest, size, mtime, status, note)
                if status == "needs_ocr":
                    report.needs_ocr.append(rel)
            else:
                vectors = embedder.embed([c.text for c in chunks])
                store.replace_doc(rel, digest, size, mtime, chunks, vectors, "ok", note)

            if old:
                report.updated += 1
            else:
                report.added += 1
        except Exception as e:                      # một file lỗi không được làm hỏng cả lượt
            log.exception("Lỗi khi xử lý %s", rel)
            store.mark_doc(rel, digest, size, mtime, "error", str(e)[:300])
            report.errors.append(f"{rel}: {e}")

    # File đã bị xóa khỏi thư mục -> xóa khỏi index
    for row in store.list_docs():
        if row.path not in seen:
            store.delete_doc(row.path)
            report.removed += 1

    return report
