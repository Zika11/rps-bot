import sqlite3, json, asyncio
from datetime import datetime

DB = "rps_bot.db"

# أقفال للحفاظ على التزامن
pending_lock = asyncio.Lock()
active_lock = asyncio.Lock()

# ---------- إدارة المباريات العشوائية (Random) ----------
async def add_pending(user_id):
    async with pending_lock:
        conn = sqlite3.connect(DB)
        cur = conn.execute("SELECT user_id FROM pending_matches WHERE user_id=?", (user_id,))
        if cur.fetchone():
            conn.close()
            return None  # موجود بالفعل
        # البحث عن لاعب آخر منتظر
        cur = conn.execute("SELECT user_id FROM pending_matches LIMIT 1")
        other = cur.fetchone()
        if other:
            opp_id = other[0]
            # إزالته من قائمة الانتظار
            conn.execute("DELETE FROM pending_matches WHERE user_id=?", (opp_id,))
            # إنشاء لعبة نشطة
            game_id = f"{user_id}_{opp_id}_{int(datetime.now().timestamp())}"
            conn.execute("INSERT INTO active_games (game_id, player1, player2, type, status, data) VALUES (?,?,?,?,?,?)",
                        (game_id, user_id, opp_id, "random", "waiting", json.dumps({})))
            conn.commit()
            conn.close()
            return opp_id  # تم العثور على خصم
        else:
            # إضافة اللاعب الحالي للانتظار
            conn.execute("INSERT INTO pending_matches (user_id) VALUES (?)", (user_id,))
            conn.commit()
            conn.close()
            return True  # في الانتظار

async def remove_game(game_id):
    async with active_lock:
        conn = sqlite3.connect(DB)
        conn.execute("DELETE FROM active_games WHERE game_id=?", (game_id,))
        conn.commit()
        conn.close()

# ---------- ألعاب فردية (Solo) – نستخدم active_games أيضاً ----------
def start_solo_game(user_id):
    game_id = f"solo_{user_id}_{int(datetime.now().timestamp())}"
    conn = sqlite3.connect(DB)
    conn.execute("INSERT INTO active_games (game_id, player1, type, status, data) VALUES (?,?,?,?,?)",
                (game_id, user_id, "solo", "active", json.dumps({})))
    conn.commit()
    conn.close()
    return game_id

def finish_solo_game(game_id):
    conn = sqlite3.connect(DB)
    conn.execute("DELETE FROM active_games WHERE game_id=?", (game_id,))
    conn.commit()
    conn.close()

# ---------- دوال مساعدة ----------
def get_game(game_id):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    game = conn.execute("SELECT * FROM active_games WHERE game_id=?", (game_id,)).fetchone()
    conn.close()
    return dict(game) if game else None

def set_game_move(game_id, player_id, move):
    conn = sqlite3.connect(DB)
    game = conn.execute("SELECT data FROM active_games WHERE game_id=?", (game_id,)).fetchone()
    if not game: return False
    data = json.loads(game[0])
    data[str(player_id)] = move
    conn.execute("UPDATE active_games SET data=? WHERE game_id=?", (json.dumps(data), game_id))
    conn.commit()
    conn.close()
    return True

def get_game_moves(game_id):
    conn = sqlite3.connect(DB)
    game = conn.execute("SELECT data FROM active_games WHERE game_id=?", (game_id,)).fetchone()
    conn.close()
    if not game: return {}
    return json.loads(game[0])
