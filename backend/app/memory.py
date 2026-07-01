import time
from typing import List
from app.storage import read_json, write_json
from app.security import redact_pii, has_prompt_injection, has_secret_request

MAX_MEMORY_PER_USER = 20


def _safe(text: str) -> str:
    text = (text or "").strip()[:700]
    if has_prompt_injection(text) or has_secret_request(text):
        return ""
    return redact_pii(text)


def get_user_memory(current_user: dict, limit: int = 6) -> dict:
    user_id = current_user["id"]
    rows = read_json("memory.json", [])
    items = [m for m in rows if m.get("user_id") == user_id]
    items = sorted(items, key=lambda x: x.get("created_at", 0), reverse=True)[:limit]
    return {"allowed": True, "items": items}


def save_conversation_memory(summary: str, current_user: dict, kind: str = "support_context") -> dict:
    clean = _safe(summary)
    if not clean:
        return {"allowed": False, "reason": "Memory contained unsafe or sensitive content and was not saved."}
    rows = read_json("memory.json", [])
    user_id = current_user["id"]
    rows.append({
        "memory_id": f"MEM-{int(time.time())}",
        "user_id": user_id,
        "customer_id": current_user.get("customer_id"),
        "kind": kind,
        "summary": clean,
        "created_at": int(time.time()),
    })
    user_rows = [r for r in rows if r.get("user_id") == user_id]
    other_rows = [r for r in rows if r.get("user_id") != user_id]
    user_rows = sorted(user_rows, key=lambda x: x.get("created_at", 0), reverse=True)[:MAX_MEMORY_PER_USER]
    write_json("memory.json", other_rows + user_rows)
    return {"allowed": True, "saved": True}


def auto_memory_note(message: str, answer: str, current_user: dict) -> None:
    text = f"User asked: {message[:240]} | Assistant answered: {answer[:360]}"
    if any(k in message.lower() for k in ["payment", "emi", "noc", "ticket", "foreclosure", "portal", "loan"]):
        save_conversation_memory(text, current_user, kind="recent_support_interaction")
