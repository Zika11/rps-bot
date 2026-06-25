# core/misc_manager.py
import json
import random
import db
import config

# ========== البطولات ==========
def create_tournament(name="بطولة الأبطال"):
    return db.create_tournament(name)

def get_tournament(tour_id):
    return db.get_tournament(tour_id)

def join_tournament(tour_id, user_id):
    return db.join_tournament(tour_id, user_id)

def update_tournament(tour_id, **kwargs):
    db.update_tournament(tour_id, **kwargs)

# ========== الزعيم العالمي ==========
def get_world_boss():
    return db.get_world_boss()

def attack_boss(user_id, damage=None):
    if damage is None:
        damage = random.randint(10, 40)
    db.add_boss_damage(user_id, damage)
    user_data = db.get_user(user_id)
    db.update_user(user_id, points=user_data["points"] + 5)
    return damage

def get_top_boss_damagers():
    return db.get_top_boss_damagers()

# ========== الموسم ==========
def get_active_season():
    return db.get_active_season()

def get_season_top_players(season_id, limit=5):
    conn = db.get_conn()
    top = conn.execute("""
        SELECT u.first_name, s.rating, s.wins 
        FROM season_rankings s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.season_id = ? 
        ORDER BY s.rating DESC 
        LIMIT ?
    """, (season_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in top]

# ========== غرفة المشاهدة ==========
def create_spectator_room(room_id, player1, chat_id):
    db.create_spectator_room(room_id, player1, None, chat_id)

def get_spectator_room(room_id):
    return db.get_spectator_room(room_id)

def join_spectator_room(room_id, player2):
    db.update_spectator_room(room_id, player2=player2, status="active")

def update_spectator_moves(room_id, moves):
    db.update_spectator_room(room_id, moves=json.dumps(moves))

def finish_spectator_room(room_id):
    db.update_spectator_room(room_id, status="finished")
