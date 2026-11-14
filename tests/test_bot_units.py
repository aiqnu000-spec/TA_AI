"""
Test cho giai đoạn 2 - KHÔNG cần token Telegram, Ollama hay mạng (dùng đối tượng giả).
Chạy:  pytest -q
"""
import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from bot_rag import auth, h_ask, h_cmd

_tmp = tempfile.mkdtemp()
os.environ.update({
    "RAG_BOT_TOKEN": "123456:TEST-TOKEN", "RAG_ADMIN_IDS": "1", "RAG_ALLOWED_IDS": "2",
    "RAG_DOCS_DIR": str(Path(_tmp) / "docs"), "RAG_INDEX_DIR": str(Path(_tmp) / "index"),
})

import pytest  # noqa: E402
from telegram.ext import ApplicationHandlerStop  # noqa: E402

from bot_rag import h_docs  # noqa: E402
from bot_rag.app import build_application  # noqa: E402
from bot_rag.utils import split_message  # noqa: E402
from backEnd.cmd_module import policy  # noqa: E402
from rag.query import NOT_FOUND, Answer  # noqa: E402
from rag.store import DocRow, Hit  # noqa: E402

POLICY = {
    "safe": ["dir", "echo", "sleep", "ping"], "confirm": ["del", "shutdown"],
    "blocked": ["format", "powershell"], "blocked_patterns": [r"\.env\b"],
}


def run(coro):
    return asyncio.run(coro)


def make_update(user_id, text="", callback_data=None):
    msg = SimpleNamespace(text=text, reply_text=AsyncMock(), document=None)
    sent = SimpleNamespace(edit_text=AsyncMock())
    msg.reply_text.return_value = sent
    q = None
    if callback_data is not None:
        q = SimpleNamespace(data=callback_data, answer=AsyncMock(), edit_message_text=AsyncMock(),
                            message=SimpleNamespace(chat_id=99))
    upd = SimpleNamespace(effective_user=SimpleNamespace(id=user_id, username="u"),
                          effective_message=msg, message=msg, callback_query=q,
                          effective_chat=SimpleNamespace(id=99, send_action=AsyncMock()))
    return upd, sent


# ---- A1/A2: xác thực & phân quyền -------------------------------------------
def test_gatekeeper_blocks_stranger_and_allows_known():
    upd, _ = make_update(999)
    with pytest.raises(ApplicationHandlerStop):
        run(auth.gatekeeper(upd, None))
    for uid in (1, 2):
        run(auth.gatekeeper(make_update(uid)[0], None))      # không ném lỗi


def test_admin_only_denies_normal_user():
    inner = AsyncMock()
    upd, _ = make_update(2)
    run(auth.admin_only(inner)(upd, None))
    inner.assert_not_awaited()
    upd.message.reply_text.assert_awaited()

    upd, _ = make_update(1)
    run(auth.admin_only(inner)(upd, None))
    inner.assert_awaited_once()


def test_admin_only_on_callback_alerts():
    inner = AsyncMock()
    upd, _ = make_update(2, callback_data="cmd:ok:abc")
    run(auth.admin_only(inner)(upd, None))
    inner.assert_not_awaited()
    upd.callback_query.answer.assert_awaited()


# ---- A3/E1: chính sách lệnh CMD ----------------------------------------------
@pytest.mark.parametrize("cmd,kind", [
    ("dir", "run"), ("DIR /w", "run"), ("echo xin chào", "run"),
    ("del a.txt", "confirm"), ("shutdown /s", "confirm"),
    ("format c:", "deny"), ("powershell -c x", "deny"), ("unknowncmd", "deny"),
    ("dir & del x", "deny"), ("dir | more", "deny"), ("echo hi > a.txt", "deny"),
    ("echo %USERPROFILE%", "deny"), ("C:\\Windows\\System32\\whoami.exe", "deny"),
    ("type .env", "deny"), ("dir/w", "deny"), ("", "deny"), ("a" * 600, "deny"),
])
def test_check_command(cmd, kind):
    assert policy.check_command(cmd, POLICY).kind == kind


def test_policy_file_default_loads_and_is_sane():
    pol = policy.load_policy()
    assert policy.check_command("dir", pol).kind == "run"
    assert policy.check_command("del x", pol).kind == "confirm"
    assert policy.check_command("powershell", pol).kind == "deny"
    assert not set(pol["safe"]) & set(pol["blocked"])


def test_run_command_output_and_timeout():
    res = policy.run_command("echo xin chao", timeout=10)
    assert "xin chao" in res.output and res.returncode == 0 and not res.timed_out
    slow = "ping -n 6 127.0.0.1" if os.name == "nt" else "sleep 5"
    t0 = time.time()
    res = policy.run_command(slow, timeout=1)
    assert res.timed_out and time.time() - t0 < 4


def test_cmd_confirm_flow(monkeypatch):
    monkeypatch.setattr(h_cmd, "check_command", lambda c: policy.check_command(c, POLICY))
    monkeypatch.setattr(h_cmd, "audit", lambda *a, **k: None)
    executed = []
    monkeypatch.setattr(h_cmd, "run_command", lambda c, t: (executed.append(c), policy.Result("ok", 0, False))[1])
    ctx = SimpleNamespace(user_data={}, bot=SimpleNamespace(send_message=AsyncMock()))

    upd, _ = make_update(1, "/cmd del abc.txt")
    run(h_cmd.cmd_command(upd, ctx))
    assert not executed and "pending_cmd" in ctx.user_data          # chưa chạy, chờ xác nhận
    token = ctx.user_data["pending_cmd"]["token"]

    upd2, _ = make_update(1, callback_data=f"cmd:ok:{token}")
    run(h_cmd.cmd_confirm_callback(upd2, ctx))
    assert executed == ["del abc.txt"]

    # token cũ không dùng lại được
    upd3, _ = make_update(1, callback_data=f"cmd:ok:{token}")
    run(h_cmd.cmd_confirm_callback(upd3, ctx))
    assert executed == ["del abc.txt"]


def test_cmd_confirm_expired(monkeypatch):
    monkeypatch.setattr(h_cmd, "check_command", lambda c: policy.check_command(c, POLICY))
    monkeypatch.setattr(h_cmd, "audit", lambda *a, **k: None)
    monkeypatch.setattr(h_cmd, "run_command", lambda *a: pytest.fail("không được chạy"))
    ctx = SimpleNamespace(user_data={"pending_cmd": {"token": "t", "command": "del x", "ts": time.time() - 999}},
                          bot=SimpleNamespace(send_message=AsyncMock()))
    upd, _ = make_update(1, callback_data="cmd:ok:t")
    run(h_cmd.cmd_confirm_callback(upd, ctx))


def test_cmd_user_cannot_run():
    upd, _ = make_update(2, "/cmd dir")
    run(h_cmd.cmd_command(upd, SimpleNamespace(user_data={})))
    assert "Admin" in upd.message.reply_text.await_args.args[0]


# ---- C1/C2/C6: hỏi đáp ------------------------------------------------------
def test_split_message():
    text = "\n\n".join(["đoạn " * 300] * 6)
    parts = split_message(text, 4000)
    assert len(parts) > 1 and all(len(p) <= 4000 for p in parts)
    assert split_message("ngắn") == ["ngắn"] and split_message("   ") == []
    assert all(len(p) <= 100 for p in split_message("x" * 1000, 100))     # không có khoảng trắng


def test_text_handler_answers_with_sources(monkeypatch):
    hit = Hit("nội dung", "a.pdf", 3, 7, 0.8)
    monkeypatch.setattr(h_ask, "ask", lambda store, q: Answer("Đáp án [1]", [hit]))
    ctx = SimpleNamespace(application=SimpleNamespace(bot_data={"store": object()}))
    upd, sent = make_update(1, "câu hỏi?")
    run(h_ask.text_handler(upd, ctx))
    final = sent.edit_text.await_args.args[0]
    assert "Đáp án" in final and "a.pdf - trang 3" in final


def test_text_handler_not_found_has_no_sources(monkeypatch):
    monkeypatch.setattr(h_ask, "ask", lambda store, q: Answer(NOT_FOUND, [], found=False))
    ctx = SimpleNamespace(application=SimpleNamespace(bot_data={"store": object()}))
    upd, sent = make_update(1, "gì đó")
    run(h_ask.text_handler(upd, ctx))
    assert sent.edit_text.await_args.args[0] == NOT_FOUND


def test_text_handler_ollama_down(monkeypatch):
    def boom(store, q):
        raise ConnectionError("x")
    monkeypatch.setattr(h_ask, "ask", boom)
    ctx = SimpleNamespace(application=SimpleNamespace(bot_data={"store": object()}))
    upd, sent = make_update(1, "gì đó")
    run(h_ask.text_handler(upd, ctx))
    assert "Ollama" in sent.edit_text.await_args.args[0]


# ---- B1/B2: danh sách & chi tiết tài liệu -----------------------------------
def _docs(n):
    return [DocRow(f"f{i:02}.pdf", "h", 2048, 0, 5, "ok", "", "2026-10-28T10:00:00") for i in range(n)]


def test_docs_pagination_buttons():
    docs = _docs(20)
    text, kb = h_docs.render_docs_page(docs, 0, 100)
    assert "Trang 1/3" in text and [b.text for b in kb.inline_keyboard[0]] == ["Sau ▶"]
    _, kb = h_docs.render_docs_page(docs, 1, 100)
    assert len(kb.inline_keyboard[0]) == 2
    text, kb = h_docs.render_docs_page(docs, 99, 100)           # trang vượt quá -> kẹp về trang cuối
    assert "Trang 3/3" in text and [b.text for b in kb.inline_keyboard[0]] == ["◀ Trước"]
    _, kb = h_docs.render_docs_page(_docs(3), 0, 10)
    assert kb is None


def test_docs_escapes_html():
    d = [DocRow("<b>x</b>&.pdf", "h", 1, 0, 1, "ok", "", "2026-10-28T10:00:00")]
    text, _ = h_docs.render_docs_page(d, 0, 1)
    assert "<b>x</b>" not in text and "&lt;b&gt;" in text


def test_resolve_doc():
    docs = _docs(12)
    assert h_docs.resolve_doc(docs, "3")[0].path == "f02.pdf"
    assert h_docs.resolve_doc(docs, "f05")[0].path == "f05.pdf"
    assert h_docs.resolve_doc(docs, "99")[0] is None
    d, err = h_docs.resolve_doc(docs, "f1")                      # khớp f10, f11
    assert d is None and "f10.pdf" in err
    assert h_docs.resolve_doc(docs, "zzz")[0] is None


def test_safe_filename_blocks_traversal():
    assert h_docs.safe_filename("../../Windows/evil.pdf") == "evil.pdf"
    assert h_docs.safe_filename('a:b*c?.pdf') == "a_b_c_.pdf"


# ---- lắp ráp ứng dụng -------------------------------------------------------
def test_build_application_registers_gatekeeper_first():
    app = build_application("123456:TEST-TOKEN")
    assert min(app.handlers) == -1                                  # nhóm -1 chạy trước
    assert app.handlers[-1][0].callback is auth.gatekeeper
    cmds = {c for h in app.handlers[0] if hasattr(h, "commands") for c in h.commands}
    assert {"start", "help", "ask", "docs", "doc", "reindex", "cmd"} <= cmds


# ---- B3: nhận file từ Telegram + dùng Store từ nhiều luồng ----------------------
def test_upload_flow_indexes_file_from_worker_thread(monkeypatch):
    import hashlib
    import math
    import re

    from vesion_new.rag import embedder
    from vesion_new.rag.settings import DOCS_DIR
    from vesion_new.rag.store import Store

    def fake_embed(texts):
        out = []
        for t in texts:
            v = [0.0] * 256
            for w in re.findall(r"\w+", t.lower()):
                v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 256] += 1
            n = math.sqrt(sum(x * x for x in v)) or 1
            out.append([x / n for x in v])
        return out
    monkeypatch.setattr(embedder, "embed", fake_embed)

    async def scenario():
        store = Store()                                   # tạo ở luồng chính...
        ctx = SimpleNamespace(application=SimpleNamespace(
            bot_data={"store": store, "ingest_lock": asyncio.Lock()}))

        async def download_to_drive(custom_path):
            Path(custom_path).write_text("Điều khoản bảo mật: mật khẩu phải dài 12 ký tự.", encoding="utf-8")
        doc = SimpleNamespace(file_name="../bao_mat.txt", file_size=100,
                              get_file=AsyncMock(return_value=SimpleNamespace(download_to_drive=download_to_drive)))
        upd, sent = make_update(1)
        upd.message.document = doc
        await h_docs.upload_handler(upd, ctx)             # ...dùng ở luồng phụ (to_thread)
        return store, sent

    store, sent = run(scenario())
    try:
        assert "Đã thêm" in sent.edit_text.await_args.args[0]
        assert (DOCS_DIR / "telegram" / "bao_mat.txt").exists()      # '../' đã bị loại bỏ
        assert not list((DOCS_DIR / "telegram").glob("*.part"))
        assert store.get_doc("telegram/bao_mat.txt").n_chunks >= 1
    finally:                                   # dọn để không ảnh hưởng test khác dùng chung kho
        (DOCS_DIR / "telegram" / "bao_mat.txt").unlink(missing_ok=True)
        store.delete_doc("telegram/bao_mat.txt")


def test_upload_rejects_bad_type_and_big_file():
    ctx = SimpleNamespace(application=SimpleNamespace(bot_data={}))
    for name, size, expect in [("virus.exe", 10, "hỗ trợ"), ("lon.pdf", 25 * 1024 * 1024, "20 MB")]:
        upd, _ = make_update(1)
        upd.message.document = SimpleNamespace(file_name=name, file_size=size)
        run(h_docs.upload_handler(upd, ctx))
        assert expect in upd.message.reply_text.await_args.args[0]


def test_upload_denied_for_normal_user():
    upd, _ = make_update(2)
    upd.message.document = SimpleNamespace(file_name="a.pdf", file_size=1)
    run(h_docs.upload_handler(upd, SimpleNamespace()))
    assert "Admin" in upd.message.reply_text.await_args.args[0]
