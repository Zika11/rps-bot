# core/social_manager.py
import json
import db

# ========== الأصدقاء ==========
def send_friend_request(sender_id, receiver_id):
    return db.send_friend_request(sender_id, receiver_id)

def get_pending_requests(user_id):
    return db.get_pending_requests(user_id)

def accept_friend_request(sender_id, receiver_id):
    db.accept_friend_request(sender_id, receiver_id)

def reject_friend_request(sender_id, receiver_id):
    db.reject_friend_request(sender_id, receiver_id)

def get_friends(user_id):
    return db.get_friends(user_id)

def get_user(user_id):
    return db.get_user(user_id)

def get_user_by_username(username):
    return db.get_user_by_username(username)

# ========== العشائر ==========
def get_clan(clan_name):
    return db.get_clan(clan_name)

def create_clan(name, leader_id):
    return db.create_clan(name, leader_id)

def join_clan(user_id, clan_name):
    db.update_user(user_id, clan=clan_name)

def get_all_clans():
    return db.get_all_clans()

def get_clan_treasury(clan_name):
    return db.get_clan_treasury(clan_name)

def donate_points_to_clan(user_id, clan_name, amount=50):
    u = db.get_user(user_id)
    if u["points"] < amount:
        return False, "نقاط غير كافية"
    db.update_user(user_id, points=u["points"] - amount)
    db.add_clan_treasury_points(clan_name, amount)
    return True, f"تم التبرع بـ {amount} نقطة"

def donate_gems_to_clan(user_id, clan_name, amount=5):
    u = db.get_user(user_id)
    if u["gems"] < amount:
        return False, "جواهر غير كافية"
    db.update_user(user_id, gems=u["gems"] - amount)
    db.add_clan_treasury_gems(clan_name, amount)
    return True, f"تم التبرع بـ {amount} جوهرة"

def upgrade_clan(clan_name, upgrade_id):
    return db.upgrade_clan(clan_name, upgrade_id)

def get_active_war_season():
    return db.get_active_war_season()

def get_clan_war_scores(season_id):
    conn = db.get_conn()
    scores = conn.execute(
        "SELECT clan_name, region, score FROM clan_war_scores WHERE season_id=? ORDER BY score DESC",
        (season_id,)
    ).fetchall()
    conn.close()
    return [dict(s) for s in scores]
