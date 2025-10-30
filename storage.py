import uuid
from datetime import datetime
from typing import List, Dict, Any
from tinydb import TinyDB, Query

_DB = TinyDB("chat_threads_db.json")

def _now_iso():
    return datetime.utcnow().isoformat()

def upsert_user(user_id: str, display_name: str = ""):
    users = _DB.table("users")
    q = Query()
    existing = users.get(q.user_id == user_id)
    if existing:
        return existing
    doc = {"user_id": user_id, "display_name": display_name, "created_at": _now_iso()}
    users.insert(doc)
    return doc

def create_thread(user_id: str, title: str = "New Thread") -> str:
    threads = _DB.table("threads")
    thread_id = str(uuid.uuid4())
    doc = {
        "thread_id": thread_id,
        "user_id": user_id,
        "title": title,
        "created_at": _now_iso(),
        "updated_at": _now_iso()
    }
    threads.insert(doc)
    return thread_id

def list_threads(user_id: str) -> List[Dict[str, Any]]:
    threads = _DB.table("threads")
    q = Query()
    items = threads.search(q.user_id == user_id)
    # newest first
    return sorted(items, key=lambda d: d.get("updated_at", ""), reverse=True)

def rename_thread(thread_id: str, title: str):
    threads = _DB.table("threads")
    q = Query()
    threads.update({"title": title, "updated_at": _now_iso()}, q.thread_id == thread_id)

def save_messages(thread_id: str, messages: List[Dict[str, str]]):
    """
    messages = [{ "role": "user"|"assistant", "content": "..." , "ts": ISO }, ...]
    """
    msgs = _DB.table("messages")
    # store with incremental order index
    order = len(msgs.search(Query().thread_id == thread_id))
    for m in messages:
        msgs.insert({
            "thread_id": thread_id,
            "role": m["role"],
            "content": m["content"],
            "ts": m.get("ts", _now_iso()),
            "order": order
        })
        order += 1
    # bump thread updated time
    threads = _DB.table("threads")
    threads.update({"updated_at": _now_iso()}, Query().thread_id == thread_id)

def load_messages(thread_id: str) -> List[Dict[str, str]]:
    msgs = _DB.table("messages")
    q = Query()
    items = msgs.search(q.thread_id == thread_id)
    items = sorted(items, key=lambda d: d.get("order", 0))
    return [{"role": it["role"], "content": it["content"], "ts": it.get("ts", "")} for it in items]
