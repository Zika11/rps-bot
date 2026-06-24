import sqlite3, json, logging
from datetime import datetime
from collections import Counter

DB = "rps_bot.db"

logger = logging.getLogger(__name__)

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def start_channel_loop(chat_id, interval=60, ttl=30):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO channel_loop_state
        (chat_id, active, interval_sec, ttl_sec, round_id, players_choice, predictions, round_start_time)
        VALUES (?,1,?,?,0,'{}','{}',datetime('now'))
    """, (chat_id, interval, ttl))
    conn.commit()
    conn.close()

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

def record_channel_vote(chat_id, user_id, move):
    conn = get_conn()
    state = conn.execute("SELECT * FROM channel_loop_state WHERE chat_id=?", (chat_id,)).fetchone()
    if not state or not state["active"]:
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
    conn = get_conn()
    state = conn.execute("SELECT * FROM channel_loop_state WHERE chat_id=?", (chat_id,)).fetchone()
    if not state: return False
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

def finish_channel_round(chat_id):
    conn = get_conn()
    state = conn.execute("SELECT * FROM channel_loop_state WHERE chat_id=?", (chat_id,)).fetchone()
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
        conn.close()
        return {"players": {}, "counts": {}, "winners": [], "draw": False, "winning_moves": []}

    moves = list(valid_choices.values())
    counts = dict(Counter(moves))
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)

    draw = False
    winning_moves = []
    if len(sorted_counts) >= 2 and sorted_counts[0][1] == sorted_counts[1][1]:
        draw = True
        top_count = sorted_counts[0][1]
        winning_moves = [move for move, cnt in sorted_counts if cnt == top_count]
    else:
        winning_moves = [sorted_counts[0][0]]

    winners = [uid for uid, mv in valid_choices.items() if mv in winning_moves]

    new_round = current_round + 1
    conn.execute("UPDATE channel_loop_state SET round_id=?, players_choice='{}', predictions='{}', round_start_time=datetime('now') WHERE chat_id=?",
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
