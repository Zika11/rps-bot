import sqlite3, json, logging, random
from datetime import datetime, timedelta
from collections import Counter
import config

DB = config.DB_NAME
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
        (chat_id, active, status, interval_sec, ttl_sec, round_id, predictions, round_start_time, end_time)
        VALUES (?,1,'ACTIVE',?,?,0,'{}',?,?)
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

    current_round = state["round_id"]
    conn.execute("""
        INSERT INTO channel_votes (chat_id, user_id, move, round_id) 
        VALUES (?,?,?,?)
        ON CONFLICT(chat_id, user_id, round_id) DO UPDATE SET move=excluded.move
    """, (chat_id, user_id, move, current_round))
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
    state = conn.execute("SELECT round_id FROM channel_loop_state WHERE chat_id=? AND active=1 AND status='ACTIVE'", (chat_id,)).fetchone()
    if not state:
        conn.close()
        return 0
    count = conn.execute("SELECT COUNT(*) as cnt FROM channel_votes WHERE chat_id=? AND round_id=?", (chat_id, state["round_id"])).fetchone()
    conn.close()
    return count["cnt"] if count else 0

def finish_channel_round(chat_id, event=None):
    conn = get_conn()
    state = conn.execute("SELECT * FROM channel_loop_state WHERE chat_id=? AND active=1 AND status='ACTIVE'", (chat_id,)).fetchone()
    if not state:
        conn.close()
        return None

    current_round = state["round_id"]

    votes = conn.execute("SELECT user_id, move FROM channel_votes WHERE chat_id=? AND round_id=?", (chat_id, current_round)).fetchall()
    if not votes:
        conn.execute("UPDATE channel_loop_state SET status='WAITING' WHERE chat_id=?", (chat_id,))
        conn.commit()
        conn.close()
        return {"players": {}, "counts": {}, "winners": [], "draw": False, "winning_moves": []}

    valid_choices = {str(v["user_id"]): v["move"] for v in votes}
    moves = list(valid_choices.values())
    counts = dict(Counter(moves))
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)

    draw = False
    winning_moves = []
    winners = []
    filtered = None

    # تطبيق قواعد الفوضى إن وجدت
    if event:
        if event == "reverse_win":
            if sorted_counts:
                min_count = sorted_counts[-1][1]
                winning_moves = [move for move, cnt in counts.items() if cnt == min_count]
                draw = len(winning_moves) > 1
        elif event == "random_winner":
            if counts:
                winning_moves = [random.choice(list(counts.keys()))]
                draw = False
        elif event in config.BANNED_MOVE_EVENTS:
            banned_move = config.BANNED_MOVE_EVENTS[event]
            filtered = {uid: mv for uid, mv in valid_choices.items() if mv != banned_move}
            if filtered:
                pass
            else:
                winning_moves = []
                draw = False

    # إذا لم يتم تعيين winning_moves من أحداث الفوضى، نطبق Real RPS Logic
    if not winning_moves and not draw:
        data = filtered if filtered else valid_choices
        if not data:
            winning_moves = []
            draw = False
        else:
            data_moves = list(data.values())
            data_counts = dict(Counter(data_moves))
            rock_count = data_counts.get("rock", 0)
            paper_count = data_counts.get("paper", 0)
            scissors_count = data_counts.get("scissors", 0)

            # Real RPS Logic
            if rock_count > 0 and scissors_count > 0 and paper_count == 0:
                winning_moves = ["rock"]
                draw = False
            elif scissors_count > 0 and paper_count > 0 and rock_count == 0:
                winning_moves = ["scissors"]
                draw = False
            elif paper_count > 0 and rock_count > 0 and scissors_count == 0:
                winning_moves = ["paper"]
                draw = False
            elif rock_count > 0 and paper_count > 0 and scissors_count > 0:
                winning_moves = []
                draw = True
            else:
                present = [move for move, cnt in data_counts.items() if cnt > 0]
                if len(present) == 1:
                    winning_moves = [present[0]]
                    draw = False
                else:
                    winning_moves = []
                    draw = False

    if winning_moves:
        winners = [uid for uid, mv in valid_choices.items() if mv in winning_moves]
    else:
        winners = []

    new_round = current_round + 1
    conn.execute("UPDATE channel_loop_state SET round_id=?, predictions='{}', status='WAITING', round_start_time=datetime('now') WHERE chat_id=?",
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
