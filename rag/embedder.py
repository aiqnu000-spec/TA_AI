"""
1.2 (phần 2) - Embedding qua Ollama (mặc định bge-m3: đa ngôn ngữ, hỗ trợ tiếng Việt).

Dùng Ollama cho cả embedding lẫn LLM nên KHÔNG cần cài PyTorch/sentence-transformers
(nhẹ hơn nhiều, và tránh lỗi tương thích phiên bản Python).

Lưu ý: bge-m3 không cần tiền tố "query:"/"passage:". Nếu sau này đổi sang
multilingual-e5 thì phải thêm các tiền tố đó.
"""
import ollama

from .settings import EMBED_BATCH, EMBED_MODEL, LLM_MODEL, LLM_TIMEOUT, OLLAMA_HOST

_client: ollama.Client | None = None


def get_client() -> ollama.Client:
    global _client
    if _client is None:
        _client = ollama.Client(host=OLLAMA_HOST, timeout=LLM_TIMEOUT)
    return _client


def embed(texts: list[str]) -> list[list[float]]:
    """Trả về một vector cho mỗi đoạn văn bản, giữ nguyên thứ tự."""
    out: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        res = get_client().embed(model=EMBED_MODEL, input=texts[i:i + EMBED_BATCH])
        out.extend(res["embeddings"])
    return out


def check_ollama() -> list[str]:
    """Trả về danh sách lỗi (rỗng = mọi thứ sẵn sàng)."""
    problems: list[str] = []
    try:
        get_client().list()
    except Exception:
        return [f"Không kết nối được Ollama tại {OLLAMA_HOST}. Ollama đã chạy chưa?"]
    for model in (EMBED_MODEL, LLM_MODEL):
        try:
            get_client().show(model)
        except Exception:
            problems.append(f"Chưa có model '{model}'. Chạy:  ollama pull {model}")
    return problems
