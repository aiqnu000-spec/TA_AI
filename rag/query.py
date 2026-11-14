"""
1.3 + 1.4 - Truy vấn: câu hỏi -> embedding -> tìm K đoạn -> ghép prompt -> LLM -> trả lời + nguồn.
"""
import re
from dataclasses import dataclass, field
from typing import Callable

from . import embedder
from .settings import LLM_MODEL, LLM_NUM_CTX, MIN_SCORE, TOP_K
from .store import Hit, Store

NOT_FOUND = "Không tìm thấy thông tin này trong tài liệu."

SYSTEM_PROMPT = f"""Bạn là trợ lý hỏi đáp dựa trên tài liệu cá nhân của người dùng.

QUY TẮC BẮT BUỘC:
1. CHỈ dùng thông tin trong phần NGỮ CẢNH được cung cấp. Tuyệt đối không dùng kiến thức bên ngoài và không suy đoán.
2. Nếu ngữ cảnh không đủ để trả lời, chỉ trả lời đúng một câu: "{NOT_FOUND}"
3. Trả lời bằng tiếng Việt, ngắn gọn, rõ ràng, đi thẳng vào câu hỏi.
4. Sau mỗi ý lấy từ ngữ cảnh, ghi số đoạn nguồn trong ngoặc vuông, ví dụ [1] hoặc [2][3]."""


@dataclass
class Answer:
    text: str
    hits: list[Hit] = field(default_factory=list)   # các đoạn đã đưa cho LLM
    found: bool = True                              # False = không có đoạn nào đủ liên quan

    @property
    def cited(self) -> list[tuple[int, Hit]]:
        """Các nguồn mà LLM thực sự trích dẫn [n]; nếu LLM không trích thì trả toàn bộ."""
        nums = sorted({int(n) for n in re.findall(r"\[(\d+)\]", self.text)})
        picked = [(n, self.hits[n - 1]) for n in nums if 1 <= n <= len(self.hits)]
        return picked or list(enumerate(self.hits, start=1))


def retrieve(store: Store, question: str, k: int = TOP_K) -> list[Hit]:
    """Trả về k đoạn gần nhất (CHƯA lọc ngưỡng) - dùng cho debug và đánh giá."""
    vec = embedder.embed([question])[0]
    return store.query(vec, k)


def build_context(hits: list[Hit]) -> str:
    return "\n\n".join(f"[{i}] (Nguồn: {h.label})\n{h.text}" for i, h in enumerate(hits, start=1))


def _call_llm(messages: list[dict], on_token: Callable[[str], None] | None) -> str:
    opts = {"temperature": 0.1, "num_ctx": LLM_NUM_CTX}
    client = embedder.get_client()
    if on_token is None:
        res = client.chat(model=LLM_MODEL, messages=messages, options=opts)
        return res["message"]["content"].strip()
    parts: list[str] = []
    for chunk in client.chat(model=LLM_MODEL, messages=messages, options=opts, stream=True):
        piece = chunk["message"]["content"]
        parts.append(piece)
        on_token(piece)
    return "".join(parts).strip()


def ask(store: Store, question: str,
        on_token: Callable[[str], None] | None = None) -> Answer:
    hits = [h for h in retrieve(store, question) if h.score >= MIN_SCORE]

    # Không đoạn nào đủ liên quan -> trả lời luôn, KHÔNG gọi LLM:
    # vừa nhanh, vừa chặn được việc LLM "bịa" khi không có dữ liệu.
    if not hits:
        if on_token:
            on_token(NOT_FOUND)
        return Answer(NOT_FOUND, [], found=False)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"NGỮ CẢNH:\n{build_context(hits)}\n\nCÂU HỎI: {question}"},
    ]
    text = _call_llm(messages, on_token)
    return Answer(text, hits, found=True)
