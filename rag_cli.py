"""
Chạy lõi RAG bằng dòng lệnh (Giai đoạn 1 - chưa cần Telegram).

  python rag_cli.py check                 kiểm tra Ollama + model
  python rag_cli.py ingest [--force]      nạp / cập nhật tài liệu trong data/documents
  python rag_cli.py docs                  liệt kê tài liệu đã index
  python rag_cli.py stats                 thống kê
  python rag_cli.py ask "câu hỏi" [--debug]
  python rag_cli.py chat                  hỏi liên tục (gõ 'exit' để thoát)
"""
import argparse
import logging
import sys

from rag import settings
from rag.ingest import ingest
from rag.query import ask, retrieve
from rag.store import Store
from rag import embedder

# Chức năng chuyển đầu ra console của Windows sang UTF-8 để hiển thị tiếng Việt có dấu chính xác
# A function to switch Windows console output to UTF-8
def _fix_console() -> None:
    # Console Windows có thể không in được tiếng Việt nếu bảng mã không phải UTF-8
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


# Kiểm tra Ollama có hoạt động và đáp ứng yêu cầu hay không?
# Check if Ollama is running and meets the requirements
def _require_ollama() -> bool:
    problems = embedder.check_ollama()
    for p in problems:
        print("✗", p)
    return not problems


# Thông tin cấu hình
# Configuration information
def cmd_check(_args) -> int:
    print(f"Ollama      : {settings.OLLAMA_HOST}")
    print(f"Embedding   : {settings.EMBED_MODEL}")
    print(f"LLM         : {settings.LLM_MODEL}")
    print(f"Kho tài liệu: {settings.DOCS_DIR}")
    print(f"Index       : {settings.INDEX_DIR}")
    if _require_ollama():
        print("✓ Mọi thứ sẵn sàng.")
        return 0
    return 1


def cmd_ingest(args) -> int:
    if not _require_ollama():
        return 1
    store = Store()
    rep = ingest(store, force=args.force, progress=print)
    print(f"\nThêm mới: {rep.added} | Cập nhật: {rep.updated} | Không đổi: {rep.unchanged} "
          f"| Xóa: {rep.removed} | Lỗi: {len(rep.errors)}")
    if rep.needs_ocr:
        print(f"⚠ {len(rep.needs_ocr)} file nghi là PDF scan (chưa có OCR), đã bỏ qua:")
        for p in rep.needs_ocr[:10]:
            print("   -", p)
    for e in rep.errors[:10]:
        print("✗", e)
    print("Thống kê:", store.stats())
    return 0 if not rep.errors else 2


def cmd_docs(_args) -> int:
    for d in Store().list_docs():
        extra = f"  ({d.note})" if d.note else ""
        print(f"{d.status:9} {d.n_chunks:5} chunk  {d.size / 1024:8.1f} KB  {d.path}{extra}")
    return 0


def cmd_stats(_args) -> int:
    print(Store().stats())
    return 0


def _answer(store: Store, question: str, debug: bool) -> None:
    if debug:
        print("--- Top đoạn tìm được (chưa lọc ngưỡng) ---")
        for h in retrieve(store, question):
            mark = "✓" if h.score >= settings.MIN_SCORE else "✗"
            preview = h.text[:90].replace("\n", " ")
            print(f" {mark} {h.score:.3f}  {h.label}\n        {preview}...")
        print(f"(ngưỡng MIN_SCORE = {settings.MIN_SCORE})\n--- Trả lời ---")
    ans = ask(store, question, on_token=lambda t: print(t, end="", flush=True))
    print()
    if ans.found:
        print("\nNguồn:")
        for n, h in ans.cited:
            print(f"  [{n}] {h.label}  (độ giống {h.score:.2f})")


def cmd_ask(args) -> int:
    if not _require_ollama():
        return 1
    _answer(Store(), args.question, args.debug)
    return 0


def cmd_chat(args) -> int:
    if not _require_ollama():
        return 1
    store = Store()
    print("Hỏi đáp trên tài liệu. Gõ 'exit' để thoát.")
    while True:
        try:
            q = input("\nBạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in {"exit", "quit", "thoat", "thoát"}:
            break
        if q:
            print("Bot: ", end="")
            _answer(store, q, args.debug)
    return 0


def main() -> int:
    _fix_console()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="RAG - giai đoạn 1 (dòng lệnh)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check").set_defaults(func=cmd_check)
    p = sub.add_parser("ingest"); p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_ingest)
    sub.add_parser("docs").set_defaults(func=cmd_docs)
    sub.add_parser("stats").set_defaults(func=cmd_stats)
    p = sub.add_parser("ask"); p.add_argument("question"); p.add_argument("--debug", action="store_true")
    p.set_defaults(func=cmd_ask)
    p = sub.add_parser("chat"); p.add_argument("--debug", action="store_true")
    p.set_defaults(func=cmd_chat)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
