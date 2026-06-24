import sqlite3, json, logging, random
from datetime import datetime, date
import config

DB = "rps_bot.db"

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# --- جميع الدوال السابقة (get_user, create_user, update_user, apply_game_result, claim_daily, ...) ---
# تبقى كما هي. أضف الدوال التالية:

# ---------- Avatar Frames ----------
def get_user_frame(user_id):
    conn = get_conn()
    row = conn.execute("SELECT active_frame FROM user_frames WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row[0] if row else "default"

def set_user_frame(user_id, frame):
    conn = get_conn()
    # Ensure default is always owned
    conn.execute("INSERT OR IGNORE INTO user_frames (user_id, owned_frames, active_frame) VALUES (?, 'default', 'default')", (user_id,))
    # Add frame to owned list
    current = conn.execute("SELECT owned_frames FROM user_frames WHERE user_id=?", (user_id,)).fetchone()
    if current:
        owned = current[0].split(",")
        if frame not in owned:
            owned.append(frame)
        conn.execute("UPDATE user_frames SET owned_frames=?, active_frame=? WHERE user_id=?", (",".join(owned), frame, user_id))
    conn.commit()
    conn.close()

# ---------- Marketplace ----------
def create_listing(seller_id, item_type, item_id, price_type, price):
    conn = get_conn()
    conn.execute("INSERT INTO market_listings (seller_id, item_type, item_id, price_type, price) VALUES (?,?,?,?,?)",
                 (seller_id, item_type, item_id, price_type, price))
    conn.commit()
    conn.close()

def get_active_listings():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM market_listings WHERE status='active' ORDER BY listing_id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def buy_listing(listing_id, buyer_id):
    conn = get_conn()
    listing = conn.execute("SELECT * FROM market_listings WHERE listing_id=? AND status='active'", (listing_id,)).fetchone()
    if not listing: return False
    seller_id = listing["seller_id"]
    buyer = conn.execute("SELECT points, gems FROM users WHERE user_id=?", (buyer_id,)).fetchone()
    if not buyer: return False
    price = listing["price"]
    if listing["price_type"] == "points" and buyer["points"] < price: return False
    if listing["price_type"] == "gems" and buyer["gems"] < price: return False
    # خصم ودفع
    if listing["price_type"] == "points":
        conn.execute("UPDATE users SET points = points - ? WHERE user_id=?", (price, buyer_id))
        conn.execute("UPDATE users SET points = points + ? WHERE user_id=?", (price, seller_id))
    else:
        conn.execute("UPDATE users SET gems = gems - ? WHERE user_id=?", (price, buyer_id))
        conn.execute("UPDATE users SET gems = gems + ? WHERE user_id=?", (price, seller_id))
    # نقل الملكية حسب النوع
    item_type = listing["item_type"]
    item_id = listing["item_id"]
    if item_type == "frame":
        set_user_frame(buyer_id, item_id)
    elif item_type == "theme":
        conn.execute("UPDATE users SET theme=? WHERE user_id=?", (item_id, buyer_id))
    elif item_type == "title":
        conn.execute("UPDATE users SET title=? WHERE user_id=?", (item_id, buyer_id))
    elif item_type == "booster":
        # إضافة booster للمشتري
        user = conn.execute("SELECT shop_items FROM users WHERE user_id=?", (buyer_id,)).fetchone()
        items = user[0].split(",") if user[0] else []
        items.append(item_id)
        conn.execute("UPDATE users SET shop_items=? WHERE user_id=?", (",".join(items), buyer_id))
    conn.execute("UPDATE market_listings SET status='sold' WHERE listing_id=?", (listing_id,))
    conn.commit()
    conn.close()
    return True

# ---------- Tournament Helpers ----------
def get_tournament(tour_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM tournaments WHERE tour_id=?", (tour_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_tournament(tour_id, **kwargs):
    conn = get_conn()
    fields = ', '.join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [tour_id]
    conn.execute(f"UPDATE tournaments SET {fields} WHERE tour_id=?", values)
    conn.commit()
    conn.close()

def create_tournament(name):
    conn = get_conn()
    cur = conn.execute("INSERT INTO tournaments (name, status, current_round) VALUES (?, 'open', 0)", (name,))
    conn.commit()
    tour_id = cur.lastrowid
    conn.close()
    return tour_id

def join_tournament(tour_id, user_id):
    conn = get_conn()
    row = conn.execute("SELECT players FROM tournaments WHERE tour_id=?", (tour_id,)).fetchone()
    if not row: return False
    players = json.loads(row[0] or "[]")
    if len(players) >= 8: return False
    if user_id in players: return True
    players.append(user_id)
    conn.execute("UPDATE tournaments SET players=? WHERE tour_id=?", (json.dumps(players), tour_id))
    conn.commit()
    conn.close()
    return True
