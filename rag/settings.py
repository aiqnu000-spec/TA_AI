"""
Cấu hình riêng cho phần RAG.

Cố ý KHÔNG dùng config.py của bot: config.py bắt buộc phải có TELEGRAM_TOKEN,
trong khi chạy RAG bằng dòng lệnh thì không cần token.
Mọi giá trị đều đổi được qua file .env (xem .env.example).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent

# --- Đường dẫn -------------------------------------------------------------
DOCS_DIR = Path(os.getenv("RAG_DOCS_DIR", ROOT / "data" / "documents"))
INDEX_DIR = Path(os.getenv("RAG_INDEX_DIR", ROOT / "data" / "index"))

# --- Ollama ----------------------------------------------------------------
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = os.getenv("RAG_EMBED_MODEL", "bge-m3")
LLM_MODEL = os.getenv("RAG_LLM_MODEL", "qwen2.5:3b")
LLM_NUM_CTX = int(os.getenv("RAG_LLM_NUM_CTX", "4096"))
LLM_TIMEOUT = float(os.getenv("RAG_LLM_TIMEOUT", "300"))  # giây; CPU chạy chậm nên để dài

# --- Chia đoạn (chunk) -----------------------------------------------------
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "800"))      # ký tự
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "100"))
EMBED_BATCH = int(os.getenv("RAG_EMBED_BATCH", "16"))

# --- Truy vấn --------------------------------------------------------------
TOP_K = int(os.getenv("RAG_TOP_K", "5"))
# Độ tương đồng cosine tối thiểu (0..1). Thấp hơn => coi như "không tìm thấy".
# Đây là con số phải tinh chỉnh bằng rag_eval.py ở bước 1.5.
MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.40"))

SUPPORTED_EXT = {".pdf", ".txt", ".md", ".docx"}
