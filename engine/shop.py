import sqlite3, json, logging
import config

DB = "rps_bot.db"

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def get_shop_items():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM shop").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def buy_item(user_id, item_id):
    conn = get_conn()
    u = conn.execute("SELECT points, shop_items FROM users WHERE user_id=?", (user_id,)).fetchone()
    item = conn.execute("SELECT * FROM shop WHERE item_id=?", (item_id,)).fetchone()
    if not u or not item:
        conn.close()
        return False, "المستخدم أو العنصر غير موجود"
    if u["points"] < item["price"]:
        conn.close()
        return False, "نقاط غير كافية"
    new_points = u["points"] - item["price"]
    owned = (u["shop_items"] or "").split(",")
    if item_id in owned:
        conn.close()
        return False, "تمتلك هذا العنصر بالفعل"
    owned.append(item_id)
    conn.execute("UPDATE users SET points=?, shop_items=? WHERE user_id=?", (new_points, ",".join(owned), user_id))
    conn.commit()
    conn.close()
    return True, "تم الشراء!"

def buy_ability(user_id, ability):
    cost = config.ABILITIES[ability]["cost"]
    conn = get_conn()
    u = conn.execute("SELECT points FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not u or u["points"] < cost:
        conn.close()
        return False
    conn.execute("UPDATE users SET points = points - ? WHERE user_id=?", (cost, user_id))
    conn.execute("INSERT OR IGNORE INTO user_abilities (user_id) VALUES (?)", (user_id,))
    conn.execute(f"UPDATE user_abilities SET {ability} = {ability} + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    return True

def get_ability_count(user_id, ability):
    conn = get_conn()
    row = conn.execute(f"SELECT {ability} FROM user_abilities WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row[0] if row else 0

def use_ability(user_id, ability):
    conn = get_conn()
    count = conn.execute(f"SELECT {ability} FROM user_abilities WHERE user_id=?", (user_id,)).fetchone()
    if not count or count[0] <= 0:
        conn.close()
        return False
    conn.execute(f"UPDATE user_abilities SET {ability} = {ability} - 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    return True
