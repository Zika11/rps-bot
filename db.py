import sqlite3, json, logging, random
from datetime import datetime, date, timedelta
import config

DB = config.DB_NAME

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- دوال المستخدمين الأساسية (من engine/users.py) ----------
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

# ---------- دوال العشائر ----------
def get_clan(clan_name):
    conn = get_conn()
    row = conn.execute("SELECT * FROM clans WHERE name=?", (clan_name,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_clan(name, leader_id):
    conn = get_conn()
    try:
        conn.execute("INSERT INTO clans (name, leader_id, created_at) VALUES (?,?,?)",
                     (name, leader_id, datetime.now().isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_clan(name, **kwargs):
    conn = get_conn()
    fields = ', '.join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [name]
    conn.execute(f"UPDATE clans SET {fields} WHERE name=?", values)
    conn.commit()
    conn.close()

def get_all_clans():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM clans ORDER BY points DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_tasks():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_shop_items():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM shop").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_rating(user_id):
    conn = get_conn()
    row = conn.execute("SELECT rating FROM ratings WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row[0] if row else None

def update_rating(user_id, new_rating):
    conn = get_conn()
    conn.execute("UPDATE ratings SET rating=? WHERE user_id=?", (new_rating, user_id))
    conn.commit()
    conn.close()

def get_top_ratings(limit=10):
    conn = get_conn()
    rows = conn.execute("""
        SELECT u.user_id, u.first_name, r.rating
        FROM ratings r JOIN users u ON r.user_id = u.user_id
        ORDER BY r.rating DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ---------- الأصدقاء ----------
def send_friend_request(sender, receiver):
    conn = get_conn()
    try:
        conn.execute("INSERT OR IGNORE INTO friend_requests VALUES (?,?, 'pending')", (sender, receiver))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_pending_requests(user_id):
    conn = get_conn()
    rows = conn.execute("SELECT sender_id FROM friend_requests WHERE receiver_id=? AND status='pending'", (user_id,)).fetchall()
    conn.close()
    return [r[0] for r in rows]

def accept_friend_request(sender, receiver):
    conn = get_conn()
    conn.execute("UPDATE friend_requests SET status='accepted' WHERE sender_id=? AND receiver_id=?", (sender, receiver))
    conn.execute("INSERT OR IGNORE INTO friends VALUES (?,?)", (sender, receiver))
    conn.execute("INSERT OR IGNORE INTO friends VALUES (?,?)", (receiver, sender))
    conn.commit()
    conn.close()

def reject_friend_request(sender, receiver):
    conn = get_conn()
    conn.execute("DELETE FROM friend_requests WHERE sender_id=? AND receiver_id=?", (sender, receiver))
    conn.commit()
    conn.close()

def get_friends(user_id):
    conn = get_conn()
    rows = conn.execute("SELECT friend_id FROM friends WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return [r[0] for r in rows]

# ---------- البطولات ----------
def create_tournament(name):
    conn = get_conn()
    cur = conn.execute("INSERT INTO tournaments (name, status) VALUES (?, 'open')", (name,))
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

def get_achievements():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM achievements").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_achievement(user_id, ach_id):
    conn = get_conn()
    u = conn.execute("SELECT achievements FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not u: return False
    achieved = u[0].split(",") if u[0] else []
    if ach_id in achieved: return False
    achieved.append(ach_id)
    conn.execute("UPDATE users SET achievements=? WHERE user_id=?", (",".join(achieved), user_id))
    conn.commit()
    conn.close()
    return True

def get_active_clan_war():
    conn = get_conn()
    row = conn.execute("SELECT * FROM clan_wars WHERE active=1").fetchone()
    conn.close()
    return dict(row) if row else None

def add_clan_war_points(clan, amount):
    conn = get_conn()
    conn.execute("UPDATE clan_wars SET points1 = points1 + ? WHERE clan1=? AND active=1", (amount, clan))
    conn.execute("UPDATE clan_wars SET points2 = points2 + ? WHERE clan2=? AND active=1", (amount, clan))
    conn.commit()
    conn.close()

def apply_game_result(user_id, result, move, opponent_id=None):
    conn = get_conn()
    u = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not u:
        conn.close()
        return None

    wins = u["wins"] + (1 if result == "win" else 0)
    losses = u["losses"] + (1 if result == "loss" else 0)
    draws = u["draws"] + (1 if result == "draw" else 0)
    points = u["points"] + (10 if result == "win" else (5 if result == "draw" else 0))
    gems = u["gems"] + 1
    rock_used = u["rock_used"] + (1 if move == "rock" else 0)
    win_streak = u["win_streak"] + 1 if result == "win" else 0
    streak_count = u["streak_count"] + 1 if result == "win" else max(0, u["streak_count"] - 1)

    conn.execute("""
        UPDATE users SET
            wins = ?, losses = ?, draws = ?, points = ?, gems = ?,
            rock_used = ?, win_streak = ?, streak_count = ?
        WHERE user_id = ?
    """, (wins, losses, draws, points, gems, rock_used, win_streak, streak_count, user_id))

    rating = conn.execute("SELECT rating FROM ratings WHERE user_id=?", (user_id,)).fetchone()
    rating = rating[0] if rating else config.DEFAULT_RATING
    opp_rating = config.DEFAULT_RATING
    if opponent_id:
        opp = conn.execute("SELECT rating FROM ratings WHERE user_id=?", (opponent_id,)).fetchone()
        if opp:
            opp_rating = opp[0]
    expected = 1 / (1 + 10 ** ((opp_rating - rating) / 400))
    score = 1 if result == "win" else 0.5 if result == "draw" else 0
    new_rating = int(rating + config.RATING_K * (score - expected))
    conn.execute("UPDATE ratings SET rating = ? WHERE user_id = ?", (new_rating, user_id))

    add_battle_pass_xp(user_id, 15, conn)

    clan = u["clan"]
    if clan:
        add_clan_treasury_points(clan, 1, conn)
        update_clan_war_score(clan, 1, conn)

    if result == "win":
        damage = random.randint(20, 50)
        add_boss_damage(user_id, damage, conn)

    conn.commit()
    conn.close()
    return {
        "user_id": user_id,
        "wins": wins, "losses": losses, "draws": draws,
        "points": points, "gems": gems, "win_streak": win_streak,
        "rock_used": rock_used, "streak_count": streak_count,
        "rating": new_rating
    }

# --- دوال الميزات السابقة ---
def claim_daily(user_id):
    conn = get_conn()
    today = date.today().isoformat()
    row = conn.execute("SELECT * FROM daily_claims WHERE user_id=?", (user_id,)).fetchone()
    if row and row["last_claimed_date"] == today:
        conn.close()
        return None
    if row:
        last_date = row["last_claimed_date"]
        streak = row["streak"]
        if last_date:
            last = date.fromisoformat(last_date)
            diff = (date.today() - last).days
            if diff == 1:
                streak += 1
            else:
                streak = 1
        else:
            streak = 1
    else:
        streak = 1
    if streak > 7:
        streak = 1
    reward = config.DAILY_REWARDS.get(streak, (0,0))
    points, gems = reward
    u = conn.execute("SELECT points, gems FROM users WHERE user_id=?", (user_id,)).fetchone()
    if u:
        conn.execute("UPDATE users SET points=?, gems=? WHERE user_id=?", 
                     (u["points"] + points, u["gems"] + gems, user_id))
    conn.execute("INSERT OR REPLACE INTO daily_claims (user_id, last_claimed_date, streak) VALUES (?,?,?)",
                 (user_id, today, streak))
    add_battle_pass_xp(user_id, 10, conn)
    conn.commit()
    conn.close()
    return {"day": streak, "points": points, "gems": gems}

def get_battle_pass(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM battle_pass WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        conn.execute("INSERT OR IGNORE INTO battle_pass (user_id) VALUES (?)", (user_id,))
        conn.commit()
        row = conn.execute("SELECT * FROM battle_pass WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else {"user_id": user_id, "season": 1, "xp": 0, "level": 1, "premium": 0}

def add_battle_pass_xp(user_id, xp_amount, existing_conn=None):
    conn = existing_conn if existing_conn else get_conn()
    bp = conn.execute("SELECT * FROM battle_pass WHERE user_id=?", (user_id,)).fetchone()
    if not bp:
        conn.execute("INSERT INTO battle_pass (user_id, xp, level) VALUES (?,?,?)", (user_id, xp_amount, 1))
        if not existing_conn:
            conn.commit()
            conn.close()
        return 1
    new_xp = bp["xp"] + xp_amount
    new_level = bp["level"]
    while new_level < config.MAX_BATTLE_PASS_LEVEL and new_xp >= new_level * config.BATTLE_PASS_XP_PER_LEVEL:
        new_xp -= new_level * config.BATTLE_PASS_XP_PER_LEVEL
        new_level += 1
    conn.execute("UPDATE battle_pass SET xp=?, level=? WHERE user_id=?", (new_xp, new_level, user_id))
    if not existing_conn:
        conn.commit()
        conn.close()
    return new_level

def spin_wheel(user_id):
    r = random.random()
    cumulative = 0
    for reward_type, value, prob in config.WHEEL_REWARDS:
        cumulative += prob
        if r <= cumulative:
            return (reward_type, value)
    return ("points", 50)

def get_user_frame(user_id):
    conn = get_conn()
    row = conn.execute("SELECT active_frame FROM user_frames WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row[0] if row else "default"

def set_user_frame(user_id, frame):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO user_frames (user_id, owned_frames, active_frame) VALUES (?, 'default', 'default')", (user_id,))
    current = conn.execute("SELECT owned_frames FROM user_frames WHERE user_id=?", (user_id,)).fetchone()
    if current:
        owned = current[0].split(",")
        if frame not in owned:
            owned.append(frame)
        conn.execute("UPDATE user_frames SET owned_frames=?, active_frame=? WHERE user_id=?", (",".join(owned), frame, user_id))
    conn.commit()
    conn.close()

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
    if listing["price_type"] == "points":
        conn.execute("UPDATE users SET points = points - ? WHERE user_id=?", (price, buyer_id))
        conn.execute("UPDATE users SET points = points + ? WHERE user_id=?", (price, seller_id))
    else:
        conn.execute("UPDATE users SET gems = gems - ? WHERE user_id=?", (price, buyer_id))
        conn.execute("UPDATE users SET gems = gems + ? WHERE user_id=?", (price, seller_id))
    item_type = listing["item_type"]
    item_id = listing["item_id"]
    if item_type == "frame":
        set_user_frame(buyer_id, item_id)
    elif item_type == "theme":
        conn.execute("UPDATE users SET theme=? WHERE user_id=?", (item_id, buyer_id))
    elif item_type == "title":
        conn.execute("UPDATE users SET title=? WHERE user_id=?", (item_id, buyer_id))
    elif item_type == "booster":
        user = conn.execute("SELECT shop_items FROM users WHERE user_id=?", (buyer_id,)).fetchone()
        items = user[0].split(",") if user[0] else []
        items.append(item_id)
        conn.execute("UPDATE users SET shop_items=? WHERE user_id=?", (",".join(items), buyer_id))
    conn.execute("UPDATE market_listings SET status='sold' WHERE listing_id=?", (listing_id,))
    conn.commit()
    conn.close()
    return True

# --- Clan Treasury ---
def get_clan_treasury(clan_name):
    conn = get_conn()
    row = conn.execute("SELECT * FROM clan_treasury WHERE clan_name=?", (clan_name,)).fetchone()
    if not row:
        conn.execute("INSERT OR IGNORE INTO clan_treasury (clan_name) VALUES (?)", (clan_name,))
        conn.commit()
        row = conn.execute("SELECT * FROM clan_treasury WHERE clan_name=?", (clan_name,)).fetchone()
    conn.close()
    return dict(row) if row else None

def add_clan_treasury_points(clan_name, amount, existing_conn=None):
    conn = existing_conn if existing_conn else get_conn()
    conn.execute("INSERT OR IGNORE INTO clan_treasury (clan_name) VALUES (?)", (clan_name,))
    conn.execute("UPDATE clan_treasury SET points = points + ? WHERE clan_name=?", (amount, clan_name))
    if not existing_conn:
        conn.commit()
        conn.close()

def add_clan_treasury_gems(clan_name, amount, existing_conn=None):
    conn = existing_conn if existing_conn else get_conn()
    conn.execute("INSERT OR IGNORE INTO clan_treasury (clan_name) VALUES (?)", (clan_name,))
    conn.execute("UPDATE clan_treasury SET gems = gems + ? WHERE clan_name=?", (amount, clan_name))
    if not existing_conn:
        conn.commit()
        conn.close()

def upgrade_clan(clan_name, upgrade_id, conn=None):
    if conn is None:
        conn = get_conn()
    treasury = conn.execute("SELECT * FROM clan_treasury WHERE clan_name=?", (clan_name,)).fetchone()
    if not treasury: return False
    upgrades = json.loads(treasury["upgrades"] or "{}")
    current_level = int(upgrades.get(upgrade_id, 0))
    max_level = config.CLAN_UPGRADES[upgrade_id]["levels"]
    if current_level >= max_level: return False
    cost = config.CLAN_UPGRADES[upgrade_id]["cost_per_level"] * (current_level + 1)
    if treasury["points"] < cost: return False
    conn.execute("UPDATE clan_treasury SET points = points - ? WHERE clan_name=?", (cost, clan_name))
    upgrades[upgrade_id] = current_level + 1
    conn.execute("UPDATE clan_treasury SET upgrades = ? WHERE clan_name=?", (json.dumps(upgrades), clan_name))
    return True

# --- Clan Wars ---
def get_active_war_season():
    conn = get_conn()
    row = conn.execute("SELECT * FROM clan_war_season WHERE active=1 ORDER BY season_id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None

def start_new_war_season():
    conn = get_conn()
    now = datetime.now().isoformat()
    end = (datetime.now() + timedelta(days=config.WAR_SEASON_DURATION_DAYS)).isoformat()
    conn.execute("INSERT INTO clan_war_season (start_date, end_date, active) VALUES (?,?,1)", (now, end))
    conn.commit()
    conn.close()

def update_clan_war_score(clan_name, points, existing_conn=None):
    conn = existing_conn if existing_conn else get_conn()
    season = conn.execute("SELECT season_id FROM clan_war_season WHERE active=1 ORDER BY season_id DESC LIMIT 1").fetchone()
    if not season: return
    region = random.choice(config.WAR_REGIONS)
    conn.execute("INSERT OR IGNORE INTO clan_war_scores (clan_name, season_id, region, score) VALUES (?,?,?,0)",
                 (clan_name, season[0], region))
    conn.execute("UPDATE clan_war_scores SET score = score + ? WHERE clan_name=? AND season_id=? AND region=?",
                 (points, clan_name, season[0], region))
    if not existing_conn:
        conn.commit()
        conn.close()

# --- Spectator Mode ---
def create_spectator_room(room_id, player1, player2, chat_id):
    conn = get_conn()
    conn.execute("INSERT INTO spectator_rooms (room_id, player1, player2, chat_id, status) VALUES (?,?,?,?,'waiting')",
                 (room_id, player1, player2, chat_id))
    conn.commit()
    conn.close()

def get_spectator_room(room_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM spectator_rooms WHERE room_id=?", (room_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_spectator_room(room_id, **kwargs):
    conn = get_conn()
    fields = ', '.join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [room_id]
    conn.execute(f"UPDATE spectator_rooms SET {fields} WHERE room_id=?", values)
    conn.commit()
    conn.close()

# --- Seasons ---
def get_active_season():
    conn = get_conn()
    row = conn.execute("SELECT * FROM season_info WHERE active=1 ORDER BY season_id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None

def reset_season_rankings():
    conn = get_conn()
    conn.execute("UPDATE ratings SET rating = ?", (config.SEASON_RESET_RATING,))
    conn.commit()
    conn.close()

# --- World Boss ---
def get_world_boss():
    conn = get_conn()
    row = conn.execute("SELECT * FROM world_boss WHERE status='active'").fetchone()
    if not row:
        conn.execute("INSERT OR IGNORE INTO world_boss (boss_id, current_hp, max_hp, spawned_at) VALUES (1, ?, ?, ?)",
                     (config.BOSS_HP, config.BOSS_HP, datetime.now().isoformat()))
        conn.commit()
        row = conn.execute("SELECT * FROM world_boss WHERE boss_id=1").fetchone()
    conn.close()
    return dict(row) if row else None

def add_boss_damage(user_id, damage, existing_conn=None):
    conn = existing_conn if existing_conn else get_conn()
    boss = conn.execute("SELECT * FROM world_boss WHERE status='active'").fetchone()
    if not boss: return
    conn.execute("INSERT OR IGNORE INTO boss_damage (user_id, boss_id) VALUES (?,?)", (user_id, boss["boss_id"]))
    conn.execute("UPDATE boss_damage SET damage = damage + ?, attacks = attacks + 1 WHERE user_id=? AND boss_id=?",
                 (damage, user_id, boss["boss_id"]))
    conn.execute("UPDATE world_boss SET current_hp = MAX(0, current_hp - ?) WHERE boss_id=?", (damage, boss["boss_id"]))
    updated = conn.execute("SELECT current_hp FROM world_boss WHERE boss_id=?", (boss["boss_id"],)).fetchone()
    if updated and updated[0] <= 0:
        conn.execute("UPDATE world_boss SET status='defeated' WHERE boss_id=?", (boss["boss_id"],))
    if not existing_conn:
        conn.commit()
        conn.close()

def get_top_boss_damagers():
    conn = get_conn()
    rows = conn.execute("""
        SELECT u.first_name, b.damage
        FROM boss_damage b JOIN users u ON b.user_id = u.user_id
        ORDER BY b.damage DESC LIMIT 5
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- قدرات ---
def get_ability_count(user_id, ability):
    conn = get_conn()
    row = conn.execute(f"SELECT {ability} FROM user_abilities WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        conn.execute("INSERT OR IGNORE INTO user_abilities (user_id) VALUES (?)", (user_id,))
        conn.commit()
        row = conn.execute(f"SELECT {ability} FROM user_abilities WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row[0] if row else 0

def use_ability(user_id, ability):
    conn = get_conn()
    count = conn.execute(f"SELECT {ability} FROM user_abilities WHERE user_id=?", (user_id,)).fetchone()
    if not count or count[0] <= 0: return False
    conn.execute(f"UPDATE user_abilities SET {ability} = {ability} - 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    return True

def buy_ability(user_id, ability):
    cost = config.ABILITIES[ability]["cost"]
    conn = get_conn()
    u = conn.execute("SELECT points FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not u or u["points"] < cost: return False
    conn.execute("UPDATE users SET points = points - ? WHERE user_id=?", (cost, user_id))
    conn.execute("INSERT OR IGNORE INTO user_abilities (user_id) VALUES (?)", (user_id,))
    conn.execute(f"UPDATE user_abilities SET {ability} = {ability} + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    return True

# --- Mass Battle ---
def start_mass_battle(chat_id):
    conn = get_conn()
    cur = conn.execute("INSERT INTO mass_battle (chat_id, start_time) VALUES (?, datetime('now'))", (chat_id,))
    battle_id = cur.lastrowid
    conn.commit()
    conn.close()
    return battle_id

def add_mass_pick(battle_id, user_id, move):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO mass_battle_picks (battle_id, user_id, move) VALUES (?,?,?)",
                 (battle_id, user_id, move))
    conn.commit()
    conn.close()

def get_mass_battle_results(battle_id):
    conn = get_conn()
    picks = conn.execute("SELECT move, COUNT(*) as cnt FROM mass_battle_picks WHERE battle_id=? GROUP BY move", (battle_id,)).fetchall()
    winners = []
    if picks:
        sorted_picks = sorted(picks, key=lambda x: x["cnt"], reverse=True)
        winning_move = sorted_picks[0]["move"]
        winner_rows = conn.execute("SELECT user_id FROM mass_battle_picks WHERE battle_id=? AND move=?", (battle_id, winning_move)).fetchall()
        winners = [r["user_id"] for r in winner_rows]
    conn.execute("UPDATE mass_battle SET status='finished' WHERE battle_id=?", (battle_id,))
    conn.commit()
    conn.close()
    return winners

# --- Team Battles ---
def create_team_battle(chat_id, team1_name, team2_name):
    conn = get_conn()
    cur = conn.execute("INSERT INTO team_battles (chat_id, team1_name, team2_name) VALUES (?,?,?)",
                      (chat_id, team1_name, team2_name))
    battle_id = cur.lastrowid
    conn.commit()
    conn.close()
    return battle_id

def add_team_player(battle_id, user_id, team):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO team_battle_players (battle_id, user_id, team) VALUES (?,?,?)",
                 (battle_id, user_id, team))
    conn.commit()
    conn.close()

def get_team_players(battle_id, team):
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM team_battle_players WHERE battle_id=? AND team=?", (battle_id, team)).fetchall()
    conn.close()
    return [r["user_id"] for r in rows]

# --- دوال التصنيف للقناة ---
def get_channel_leaderboard(chat_id, limit=10):
    conn = get_conn()
    rows = conn.execute("""
        SELECT u.first_name, c.points 
        FROM channel_user_points c JOIN users u ON c.user_id = u.user_id
        WHERE c.chat_id = ? ORDER BY c.points DESC LIMIT ?
    """, (chat_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_weekly_channel_leaderboard(chat_id, limit=10):
    conn = get_conn()
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    rows = conn.execute("""
        SELECT u.first_name, SUM(c.points) as total_points
        FROM channel_user_points c JOIN users u ON c.user_id = u.user_id
        WHERE c.chat_id = ? AND c.last_updated >= ?
        GROUP BY c.user_id
        ORDER BY total_points DESC LIMIT ?
    """, (chat_id, week_ago, limit)).fetchall()
    conn.close()
    return [{"name": r["first_name"], "points": r["total_points"]} for r in rows]

# ---------- دوال المتجر والاقتصاد (من engine/economy.py) ----------
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
        cost = config.ABILITIES.get(item_id, {}).get("cost")
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
        set_user_frame(user_id, item_id)
    elif item_type == "ability":
        conn.execute("INSERT OR IGNORE INTO user_abilities (user_id) VALUES (?)", (user_id,))
        conn.execute(f"UPDATE user_abilities SET {item_id} = {item_id} + 1 WHERE user_id = ?", (user_id,))

    conn.commit()
    conn.close()
    return True, "تم الشراء بنجاح"
