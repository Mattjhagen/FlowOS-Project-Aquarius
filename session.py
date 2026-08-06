import json
import os
from pathlib import Path
from datetime import datetime

SESSION_DIR = Path.home() / ".flowos" / "sessions"


def get_session_path(session_id: str) -> Path:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return SESSION_DIR / f"{session_id}.json"


def load_session(session_id: str) -> list:
    path = get_session_path(session_id)
    if path.exists():
        return json.loads(path.read_text())
    return []


def save_session(session_id: str, messages: list):
    path = get_session_path(session_id)
    path.write_text(json.dumps(messages, indent=2))


def list_sessions() -> list:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    sessions = []
    for f in sorted(SESSION_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            msgs = json.loads(f.read_text())
            first_user = next((m["content"] for m in msgs if m["role"] == "user"), "")
            if isinstance(first_user, list):
                first_user = next((b["text"] for b in first_user if b.get("type") == "text"), "")
            sessions.append({
                "id": f.stem,
                "preview": first_user[:60],
                "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            })
        except Exception:
            pass
    return sessions


def new_session_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")
