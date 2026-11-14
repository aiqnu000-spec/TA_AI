"""
Kiểm tra + chạy lệnh CMD an toàn.

Nội dung: Lọc các lệnh, kí tự đặt biệt.

Nguyên tắc:
  1. Mặc định TỪ CHỐI: chỉ lệnh có trong danh sách 'safe' hoặc 'confirm' mới được xét.
  2. Cấm ký tự nối/chuyển hướng lệnh (& | < > ^ % `) để không "lách" bằng  `dir & del x`.
  3. Lệnh trong 'confirm' (xóa, di chuyển, tắt máy...) phải được Admin bấm xác nhận.
  4. Có timeout (diệt cả cây tiến trình) và ghi log kiểm toán mọi sự kiện.
Phần này không phụ thuộc Telegram nên test được độc lập.
"""
import json
import logging
import os
import re
import signal
import subprocess
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY_FILE = ROOT / "config" / "cmd_policy.json"
AUDIT_FILE = ROOT / "data" / "logs" / "cmd_audit.log"

METACHARS = set("&|<>^%`\n\r")
MAX_LEN = 500


@dataclass
class Decision:
    kind: str          # "run" | "confirm" | "deny"
    reason: str = ""


@dataclass
class Result:
    output: str
    returncode: int | None
    timed_out: bool


def load_policy(path: Path = POLICY_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))   # đọc lại mỗi lần -> sửa không cần restart


def check_command(command: str, policy: dict | None = None) -> Decision:
    policy = policy if policy is not None else load_policy()
    cmd = command.strip()
    if not cmd:
        return Decision("deny", "Chưa nhập lệnh. Ví dụ: /cmd dir")
    if len(cmd) > MAX_LEN:
        return Decision("deny", f"Lệnh quá dài (tối đa {MAX_LEN} ký tự).")
    if any(c in METACHARS for c in cmd):
        return Decision("deny", "Không cho phép các ký tự điều khiển shell: & | < > ^ % `")

    name = cmd.split(None, 1)[0].lower()
    if name.endswith(".exe"):
        name = name[:-4]
    if not re.fullmatch(r"[a-z0-9_-]+", name):
        return Decision("deny", "Chỉ dùng tên lệnh đơn giản, không dùng đường dẫn hay ký tự lạ.")

    for pat in policy.get("blocked_patterns", []):
        if re.search(pat, cmd, re.IGNORECASE):
            return Decision("deny", "Lệnh chứa nội dung bị chặn.")
    if name in policy.get("blocked", []):
        return Decision("deny", f"Lệnh '{name}' bị chặn vĩnh viễn.")
    if name in policy.get("confirm", []):
        return Decision("confirm")
    if name in policy.get("safe", []):
        return Decision("run")
    return Decision("deny", f"Lệnh '{name}' không nằm trong danh sách cho phép (config/cmd_policy.json).")


# ---- chạy lệnh -------------------------------------------------------------
def _oem_encoding() -> str:
    """Console Windows xuất chữ theo bảng mã OEM (vd cp850/cp1258), không phải UTF-8."""
    if os.name == "nt":
        try:
            import ctypes
            return f"cp{ctypes.windll.kernel32.GetOEMCP()}"
        except Exception:
            pass
    return "utf-8"


def _kill_tree(p: subprocess.Popen) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
        else:
            os.killpg(p.pid, signal.SIGKILL)
    except Exception:
        p.kill()


def run_command(command: str, timeout: float) -> Result:
    """CHỈ gọi sau khi check_command() cho phép (và đã được xác nhận nếu cần)."""
    kwargs: dict = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        kwargs["start_new_session"] = True
    p = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,           # lệnh hỏi Y/N sẽ không treo chờ bàn phím
        cwd=str(Path.home()), **kwargs,
    )
    timed_out = False
    try:
        raw, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_tree(p)
        raw, _ = p.communicate()
    text = raw.decode(_oem_encoding(), errors="replace").strip()
    return Result(text, None if timed_out else p.returncode, timed_out)


# ---- nhật ký kiểm toán -----------------------------------------------------
_audit_logger: logging.Logger | None = None


def audit(user_id: int, event: str, command: str, detail: str = "") -> None:
    """event: run | denied | ask_confirm | confirmed | cancelled | expired | done"""
    global _audit_logger
    if _audit_logger is None:
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        _audit_logger = logging.getLogger("cmd_audit")
        _audit_logger.setLevel(logging.INFO)
        _audit_logger.propagate = False
        h = RotatingFileHandler(AUDIT_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
        _audit_logger.addHandler(h)
    _audit_logger.info("user=%s | %s | %s | %s", user_id, event, command, detail)
