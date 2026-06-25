# core/shop_manager.py
import random
import db
import config

# ========== المتجر الأساسي ==========
def get_shop_items():
    return db.get_shop_items()

def get_titles_shop():
    conn = db.get_conn()
    rows = conn.execute("SELECT * FROM titles_shop").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_themes_shop():
    conn = db.get_conn()
    rows = conn.execute("SELECT * FROM themes_shop").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def buy_item(user_id, item_type, item_id):
    """شراء عنصر (موحد)"""
    return db.buy_item(user_id, item_type, item_id)

# ========== الإطارات ==========
def get_frame_price(frame_id):
    return config.FRAME_PRICES.get(frame_id)

def get_available_frames():
    """إرجاع قائمة الإطارات المتاحة (باستثناء default)"""
    frames = []
    for frame_id, icon in config.AVATAR_FRAMES.items():
        if frame_id != "default":
            frames.append({
                "id": frame_id,
                "icon": icon,
                "price": config.FRAME_PRICES.get(frame_id, 200)
            })
    return frames

def set_user_frame(user_id, frame_id):
    db.set_user_frame(user_id, frame_id)

# ========== القدرات ==========
def get_abilities():
    return config.ABILITIES

def buy_ability(user_id, ability_id):
    return db.buy_item(user_id, "ability", ability_id)

# ========== السوق (Marketplace) ==========
def get_active_listings():
    return db.get_active_listings()

def create_listing(seller_id, item_type, item_id, price_type, price):
    db.create_listing(seller_id, item_type, item_id, price_type, price)

def buy_listing(listing_id, buyer_id):
    return db.buy_listing(listing_id, buyer_id)

# ========== صندوق الكنز ==========
def open_treasure_box(user_id):
    u = db.get_user(user_id)
    if u["points"] < config.TREASURE_BOX_PRICE:
        return False, "نقاط غير كافية", None
    db.update_user(user_id, points=u["points"] - config.TREASURE_BOX_PRICE)
    reward = random.choice(config.TREASURE_REWARDS)
    typ, val = reward[0], reward[1]
    if typ == "points":
        db.update_user(user_id, points=u["points"] + val)
    elif typ == "gems":
        db.update_user(user_id, gems=int(u.get("gems", 0)) + val)
    elif typ == "title":
        db.update_user(user_id, title=val)
    elif typ == "theme":
        db.update_user(user_id, theme=val)
    elif typ == "booster":
        owned = u.get("shop_items", "") + f",{val}" if u.get("shop_items") else val
        db.update_user(user_id, shop_items=owned)
    return True, f"🎁 حصلت على {val}!", {"type": typ, "value": val}

# ========== عجلة الحظ ==========
def spin_wheel(user_id):
    u = db.get_user(user_id)
    if u["gems"] < config.WHEEL_COST:
        return False, "تحتاج 5 جواهر لتدوير العجلة!", None
    db.update_user(user_id, gems=u["gems"] - config.WHEEL_COST)
    reward_type, value = db.spin_wheel(user_id)
    # تطبيق المكافأة
    if reward_type == "points":
        db.update_user(user_id, points=u["points"] + value)
        msg = f"🎉 ربحت {value} نقطة!"
    elif reward_type == "gems":
        db.update_user(user_id, gems=u["gems"] + value)
        msg = f"🎉 ربحت {value} جوهرة!"
    elif reward_type == "title":
        db.update_user(user_id, title=value)
        msg = f"🎉 حصلت على لقب '{value}'!"
    elif reward_type == "theme":
        db.update_user(user_id, theme=value)
        msg = f"🎉 حصلت على ثيم جديد!"
    elif reward_type == "treasure_box":
        # فتح صندوق كنز مجاني
        success, box_msg, _ = open_treasure_box(user_id)
        msg = f"🎁 صندوق كنز: {box_msg}"
    else:
        msg = "🎡 حظ سعيد!"
    db.add_battle_pass_xp(user_id, 5)
    return True, msg, {"type": reward_type, "value": value}

# ========== Battle Pass ==========
def get_battle_pass(user_id):
    return db.get_battle_pass(user_id)

def get_battle_pass_rewards():
    return config.BATTLE_PASS_REWARDS

def get_battle_pass_levels():
    return config.MAX_BATTLE_PASS_LEVEL
