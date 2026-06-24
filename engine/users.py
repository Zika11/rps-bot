import sqlite3, json, logging
from datetime import datetime, date
import config

DB = "rps_bot.db"

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def get_user(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_username(username):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(user_id, username, first_name, language='ar'):
    conn = get_conn()
    now = datetime.now().isoformat()
    try:
        conn.execute("INSERT INTO users (user_id, username, first_name, language, registered_date, last_login) VALUES (?,?,?,?,?,?)",
                     (user_id, username, first_name, language, now, now))
        conn.execute("INSERT OR IGNORE INTO ratings (user_id) VALUES (?)", (user_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

def update_user(user_id, **kwargs):
    if not kwargs: return
    conn = get_conn()
    fields = ', '.join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values())
    values.append(user_id)
    conn.execute(f"UPDATE users SET {fields} WHERE user_id=?", values)
    conn.commit()
    conn.close()

def get_all_user_ids():
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    return [r[0] for r in rows]
