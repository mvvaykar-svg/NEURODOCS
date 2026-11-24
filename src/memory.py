import sqlite3
import os
import shutil

DB = "memory.db"

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT)")
    conn.commit()
    conn.close()

def save_chat(role, content):
    try:
        init_db()
        conn = sqlite3.connect(DB)
        conn.execute("INSERT INTO chats (role, content) VALUES (?, ?)", (role, content))
        conn.commit()
        conn.close()
    except Exception:
        pass

def load_chat():
    try:
        init_db()
        conn = sqlite3.connect(DB)
        rows = conn.execute("SELECT role, content FROM chats ORDER BY id DESC LIMIT 50").fetchall()
        conn.close()
        return [{"role": r, "content": c} for r, c in reversed(rows)]
    except Exception:
        return []

def clear_memory():
    try:
        if os.path.exists(DB):
            os.remove(DB)
    except Exception:
        pass
    try:
        if os.path.exists("faiss_index"):
            shutil.rmtree("faiss_index", ignore_errors=True)
    except Exception:
        pass
