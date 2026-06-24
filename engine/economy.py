import sqlite3, logging
import config

DB = "rps_bot.db"

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def buy_item(user_id, item_type, item_id):
    """شراء أي عنصر من المتجر (بطاقة، لقب، ثيم، إطار، قدرة)"""
    conn = get_conn()
    u = conn.execute("SELECT points, gems, shop_items, theme, title FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not u:
        conn.close()
        return False, "المستخدم غير موجود"

    price = None
    # تحديد السعر حسب النوع
    if item_type == "booster":
        item = conn.execute("SELECT * FROM shop WHERE item_id=?", (item_id,)).fetchone()
        if not item:
            conn.close()
            return False, "العنصر غير موجود"
        price = item["price"]
    elif item_type == "title":
        row = conn.execute("SELECT * FROM titles_shop WHERE title_id=?", (item_id,)).fetchone()
        if not row:
            conn.close()
            return False, "اللقب غير موجود"
        price = row["price"]
    elif item_type == "theme":
        row = conn.execute("SELECT * FROM themes_shop WHERE theme_id=?", (item_id,)).fetchone()
        if not row:
            conn.close()
            return False, "الثيم غير موجود"
        price = row["price"]
    elif item_type == "frame":
        price = config.FRAME_PRICES.get(item_id)
        if not price:
            conn.close()
            return False, "الإطار غير موجود"
    elif item_type == "ability":
        cost = config.ABILITIES[item_id]["cost"]
        if not cost:
            conn.close()
            return False, "القدرة غير موجودة"
        price = cost
    else:
        conn.close()
        return False, "نوع غير معروف"

    # التحقق من النقاط الكافية
    if u["points"] < price:
        conn.close()
        return False, "نقاط غير كافية"

    # خصم النقاط
    new_points = u["points"] - price
    conn.execute("UPDATE users SET points = ? WHERE user_id = ?", (new_points, user_id))

    # إضافة العنصر للمستخدم حسب النوع
    if item_type == "booster":
        owned = (u["shop_items"] or "").split(",")
        owned.append(item_id)
        conn.execute("UPDATE users SET shop_items = ? WHERE user_id = ?", (",".join(owned), user_id))
    elif item_type == "title":
        conn.execute("UPDATE users SET title = ? WHERE user_id = ?", (item_id, user_id))
    elif item_type == "theme":
        conn.execute("UPDATE users SET theme = ? WHERE user_id = ?", (item_id, user_id))
    elif item_type == "frame":
        from engine.users import set_user_frame
        set_user_frame(user_id, item_id)
    elif item_type == "ability":
        conn.execute("INSERT OR IGNORE INTO user_abilities (user_id) VALUES (?)", (user_id,))
        conn.execute(f"UPDATE user_abilities SET {item_id} = {item_id} + 1 WHERE user_id = ?", (user_id,))

    conn.commit()
    conn.close()
    return True, "تم الشراء بنجاح"
