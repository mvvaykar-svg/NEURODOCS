import sqlite3

DB_NAME = "chat.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("CREATE TABLE IF NOT EXISTS chat (role TEXT, content TEXT)")
    conn.commit()
    conn.close()

def load_chat():
    init_db()
    conn = sqlite3.connect(DB_NAME)
    rows = conn.execute("SELECT role, content FROM chat").fetchall()
    conn.close()
    return [{"role": r, "content": c} for r, c in rows]

def save_chat(role, content):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT INTO chat VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()

def clear_memory():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("DELETE FROM chat")
    conn.commit()
    conn.close()
