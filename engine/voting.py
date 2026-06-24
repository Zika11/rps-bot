import sqlite3, json, logging
from datetime import datetime, timedelta
from collections import Counter
import config

DB = "rps_bot.db"
logger = logging.getLogger(__name__)

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def start_channel_loop(chat_id, interval=60, ttl=30):
    now = datetime.now()
    end = now + timedelta(seconds=interval)
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO channel_loop_state
        (chat_id, active, status, interval_sec, ttl_sec, round_id, players_choice, predictions, round_start_time, end_time)
        VALUES (?,1,'ACTIVE',?,?,0,'{}','{}',?,?)
    """, (chat_id, interval, ttl, now.isoformat(), end.isoformat()))
    conn.commit()
    conn.close()
    return end.isoformat()

def stop_channel_loop(chat_id):
    conn = get_conn()
    conn.execute("DELETE FROM channel_loop_state WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()

def get_channel_loop(chat_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM channel_loop_state WHERE chat_id=? AND active=1", (chat_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def is_user_registered(user_id):
    conn = get_conn()
    row = conn.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row is not None

def record_channel_vote(chat_id, user_id, move):
    if not is_user_registered(user_id):
        return False

    conn = get_conn()
    state = conn.execute("SELECT * FROM channel_loop_state WHERE chat_id=? AND active=1 AND status='ACTIVE'", (chat_id,)).fetchone()
    if not state:
        conn.close()
        return False

    end_time_str = state["end_time"]
    if end_time_str:
        end_dt = datetime.fromisoformat(end_time_str)
        freeze_start = end_dt - timedelta(seconds=config.VOTE_FREEZE_SECONDS)
        if datetime.now() >= freeze_start:
            conn.close()
            return False

    choices = json.loads(state["players_choice"])
    choices[str(user_id)] = {
        "move": move,
        "round": state["round_id"]
    }
    conn.execute("UPDATE channel_loop_state SET players_choice=? WHERE chat_id=?", (json.dumps(choices), chat_id))
    conn.commit()
    conn.close()
    return True

def record_prediction(chat_id, user_id, predicted_move):
    if not is_user_registered(user_id):
        return False

    conn = get_conn()
    state = conn.execute("SELECT * FROM channel_loop_state WHERE chat_id=? AND active=1 AND status='ACTIVE'", (chat_id,)).fetchone()
    if not state:
        return False

    end_time_str = state["end_time"]
    if end_time_str:
        end_dt = datetime.fromisoformat(end_time_str)
        freeze_start = end_dt - timedelta(seconds=config.VOTE_FREEZE_SECONDS)
        if datetime.now() >= freeze_start:
            conn.close()
            return False

    predictions = json.loads(state["predictions"] or "{}")
    predictions[str(user_id)] = predicted_move
    conn.execute("UPDATE channel_loop_state SET predictions=? WHERE chat_id=?", (json.dumps(predictions), chat_id))
    conn.commit()
    conn.close()
    return True

def get_predictions(chat_id):
    conn = get_conn()
    row = conn.execute("SELECT predictions FROM channel_loop_state WHERE chat_id=?", (chat_id,)).fetchone()
    conn.close()
    if not row: return {}
    return json.loads(row[0] or "{}")

def get_voter_count(chat_id):
    conn = get_conn()
    state = conn.execute("SELECT players_choice FROM channel_loop_state WHERE chat_id=? AND active=1 AND status='ACTIVE'", (chat_id,)).fetchone()
    conn.close()
    if not state:
        return 0
    choices = json.loads(state[0] or "{}")
    return len(choices)

def finish_channel_round(chat_id):
    conn = get_conn()
    state = conn.execute("SELECT * FROM channel_loop_state WHERE chat_id=? AND active=1 AND status='ACTIVE'", (chat_id,)).fetchone()
    if not state:
        conn.close()
        return None

    current_round = state["round_id"]
    choices_raw = json.loads(state["players_choice"])

    valid_choices = {}
    for uid, data in choices_raw.items():
        if isinstance(data, dict) and data.get("round") == current_round:
            valid_choices[uid] = data["move"]

    if not valid_choices:
        conn.execute("UPDATE channel_loop_state SET status='WAITING' WHERE chat_id=?", (chat_id,))
        conn.commit()
        conn.close()
        return {"players": {}, "counts": {}, "winners": [], "draw": False, "winning_moves": []}

    # حساب الهيمنة (Dominance Scoring)
    moves = list(valid_choices.values())
    counts = dict(Counter(moves))
    dominance = {"rock": 0, "paper": 0, "scissors": 0}

    rock_count = counts.get("rock", 0)
    paper_count = counts.get("paper", 0)
    scissors_count = counts.get("scissors", 0)

    # Rock vs Scissors
    if rock_count > scissors_count:
        diff = rock_count - scissors_count
        dominance["rock"] += diff
        dominance["scissors"] -= diff
    else:
        diff = scissors_count - rock_count
        dominance["scissors"] += diff
        dominance["rock"] -= diff

    # Paper vs Rock
    if paper_count > rock_count:
        diff = paper_count - rock_count
        dominance["paper"] += diff
        dominance["rock"] -= diff
    else:
        diff = rock_count - paper_count
        dominance["rock"] += diff
        dominance["paper"] -= diff

    # Scissors vs Paper
    if scissors_count > paper_count:
        diff = scissors_count - paper_count
        dominance["scissors"] += diff
        dominance["paper"] -= diff
    else:
        diff = paper_count - scissors_count
        dominance["paper"] += diff
        dominance["scissors"] -= diff

    # تحديد الحركة الفائزة (أعلى هيمنة موجبة)
    if dominance["rock"] > dominance["paper"] and dominance["rock"] > dominance["scissors"]:
        winning_moves = ["rock"]
    elif dominance["paper"] > dominance["rock"] and dominance["paper"] > dominance["scissors"]:
        winning_moves = ["paper"]
    elif dominance["scissors"] > dominance["rock"] and dominance["scissors"] > dominance["paper"]:
        winning_moves = ["scissors"]
    else:
        # تعادل في الهيمنة: نأخذ الأعلى في العدد البسيط كمعيار ثانوي
        max_count = max(counts.values())
        winning_moves = [move for move, cnt in counts.items() if cnt == max_count]

    draw = len(winning_moves) > 1
    winners = [uid for uid, mv in valid_choices.items() if mv in winning_moves]

    new_round = current_round + 1
    conn.execute("UPDATE channel_loop_state SET round_id=?, players_choice='{}', predictions='{}', status='WAITING', round_start_time=datetime('now') WHERE chat_id=?",
                 (new_round, chat_id))
    conn.commit()
    conn.close()

    return {
        "players": valid_choices,
        "counts": counts,
        "winners": winners,
        "winning_moves": winning_moves,
        "draw": draw
    }
