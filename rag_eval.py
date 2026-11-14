"""
1.5 - Đánh giá chất lượng bằng bộ câu hỏi mẫu (eval/questions.json).

Mặc định chỉ đo bước TÌM KIẾM (nhanh, không gọi LLM):
  - câu có đáp án: có tìm ra đúng tài liệu trong top-K không (hit@K) và xếp hạng mấy
  - câu "ngoài tài liệu": có bị lọc hết bởi ngưỡng MIN_SCORE không

  python rag_eval.py            # chỉ đo tìm kiếm
  python rag_eval.py --llm      # chạy cả LLM, kiểm tra từ khóa trong câu trả lời + việc từ chối
"""
import argparse
import json
import sys
from pathlib import Path

from rag import settings
from rag.query import NOT_FOUND, ask, retrieve
from rag.store import Store
from rag import embedder

QUESTIONS = Path(__file__).parent / "eval" / "questions.json"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="chạy cả LLM (chậm)")
    args = ap.parse_args()

    problems = embedder.check_ollama()
    if problems:
        print("\n".join("✗ " + p for p in problems))
        return 1

    items = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    store = Store()
    ok = 0

    for i, it in enumerate(items, start=1):
        q = it["q"]
        hits = retrieve(store, q)
        kept = [h for h in hits if h.score >= settings.MIN_SCORE]
        top = f"{hits[0].score:.2f}" if hits else "-"

        if it.get("should_refuse"):
            passed = not kept
            detail = f"điểm cao nhất {top} (ngưỡng {settings.MIN_SCORE}) -> " + \
                     ("bị lọc, ĐÚNG" if passed else "VẪN lọt qua ngưỡng, SAI")
        else:
            want = it["expect_source"].lower()
            rank = next((r for r, h in enumerate(hits, 1) if want in h.source.lower()), None)
            passed = rank is not None and hits[rank - 1].score >= settings.MIN_SCORE
            detail = f"đúng tài liệu ở hạng {rank}, điểm {top}" if rank else f"KHÔNG thấy '{it['expect_source']}' trong top {len(hits)}"

        if args.llm and passed:
            ans = ask(store, q).text
            if it.get("should_refuse"):
                passed = NOT_FOUND.lower() in ans.lower()
                detail += " | LLM " + ("từ chối đúng" if passed else "KHÔNG từ chối")
            elif it.get("expect_text"):
                missing = [t for t in it["expect_text"] if t.lower() not in ans.lower()]
                passed = not missing
                detail += " | thiếu từ khóa: " + ", ".join(missing) if missing else " | đủ từ khóa"

        ok += passed
        print(f"{'✓' if passed else '✗'} {i:2}. {q}\n      {detail}")

    print(f"\nKết quả: {ok}/{len(items)} đạt ({ok / len(items):.0%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
