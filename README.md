# Giai đoạn 1 - Lõi RAG (chạy bằng dòng lệnh)

Xem hướng dẫn đầy đủ trong tin nhắn trả lời. Tóm tắt lệnh:

    py -3.14 -m venv .venv && .venv\Scripts\activate
    pip install -r requirements.txt -r requirements-rag.txt
    ollama pull bge-m3 && ollama pull qwen2.5:7b
    python rag_cli.py check
    python rag_cli.py ingest
    python rag_cli.py ask "câu hỏi" --debug
    python rag_eval.py
    pytest -q
