import json, logging, sqlite3
from datetime import datetime
import engine.voting as voting
import engine.rewards as rewards
import engine.state as state
import config

logger = logging.getLogger(__name__)

class GameEngine:
    def __init__(self):
        pass

    async def start_round(self, chat_id, interval=60, ttl=30):
        end_time = voting.start_channel_loop(chat_id, interval, ttl)
        return end_time

    async def vote(self, chat_id, user_id, move):
        lock = await state.get_vote_lock(chat_id)
        async with lock:
            return voting.record_channel_vote(chat_id, user_id, move)

    async def predict(self, chat_id, user_id, predicted_move):
        lock = await state.get_vote_lock(chat_id)
        async with lock:
            return voting.record_prediction(chat_id, user_id, predicted_move)

    async def finish_round(self, chat_id, event=None):
        lock = await state.get_vote_lock(chat_id)
        async with lock:
            result = voting.finish_channel_round(chat_id, event=event)
        return result

    def get_round_status(self, chat_id):
        loop = voting.get_channel_loop(chat_id)
        if not loop:
            return None
        return {
            "chat_id": chat_id,
            "round_id": loop["round_id"],
            "players_count": voting.get_voter_count(chat_id),
            "interval_sec": loop["interval_sec"],
            "ttl_sec": loop["ttl_sec"],
            "status": loop["status"],
            "end_time": loop.get("end_time")
        }

    def get_voter_count(self, chat_id):
        return voting.get_voter_count(chat_id)

    def process_rewards(self, chat_id, players_rewards):
        rewards.batch_process_channel_rewards_with_streak(chat_id, players_rewards, config.STREAK_BONUS)

    def get_predictions(self, chat_id):
        return voting.get_predictions(chat_id)

    def get_live_stats(self, chat_id):
        loop = voting.get_channel_loop(chat_id)
        if not loop or loop["status"] != "ACTIVE":
            return None
        conn = sqlite3.connect(voting.DB)
        conn.row_factory = sqlite3.Row
        votes = conn.execute("SELECT move, COUNT(*) as cnt FROM channel_votes WHERE chat_id=? AND round_id=? GROUP BY move",
                             (chat_id, loop["round_id"])).fetchall()
        conn.close()
        counts = {"rock": 0, "paper": 0, "scissors": 0}
        for v in votes:
            counts[v["move"]] = v["cnt"]
        total = sum(counts.values())
        return {"counts": counts, "total": total, "status": "ACTIVE"}
