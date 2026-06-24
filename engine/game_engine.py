import json, logging
from datetime import datetime
import engine.voting as voting
import engine.rewards as rewards
import engine.state as state
import config

logger = logging.getLogger(__name__)

async def start_round(chat_id, interval=60, ttl=30):
    """
    بدء جولة جديدة في القناة.
    تعيد الوقت المتوقع لنهاية الجولة (ISO format).
    """
    end_time = voting.start_channel_loop(chat_id, interval, ttl)
    return end_time

async def vote(chat_id, user_id, move):
    """
    تسجيل تصويت لمستخدم في القناة.
    تعيد True إذا تم التسجيل بنجاح، False إذا فشل (انتهت الجولة أو لا يوجد جولة نشطة).
    """
    lock = await state.get_vote_lock(chat_id)
    async with lock:
        return voting.record_channel_vote(chat_id, user_id, move)

async def predict(chat_id, user_id, predicted_move):
    """
    تسجيل توقع لمستخدم في القناة.
    تعيد True إذا تم التسجيل بنجاح، False إذا فشل.
    """
    lock = await state.get_vote_lock(chat_id)
    async with lock:
        return voting.record_prediction(chat_id, user_id, predicted_move)

async def finish_round(chat_id):
    """
    إنهاء الجولة الحالية في القناة.
    تعيد نتائج الجولة (قاموس players, counts, winners, winning_moves, draw) أو None إذا لا توجد جولة.
    """
    lock = await state.get_vote_lock(chat_id)
    async with lock:
        result = voting.finish_channel_round(chat_id)
    return result

def get_round_status(chat_id):
    """
    الحصول على حالة الجولة الحالية.
    تعيد قاموس بمعلومات الجولة، أو None إذا لا يوجد.
    """
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

def get_voter_count(chat_id):
    """عدد المصوتين في الجولة الحالية."""
    return voting.get_voter_count(chat_id)

def process_rewards(chat_id, players_rewards):
    """توزيع المكافآت بعد الجولة."""
    rewards.batch_process_channel_rewards_with_streak(chat_id, players_rewards, config.STREAK_BONUS)

def get_predictions(chat_id):
    """جلب توقعات الجولة الحالية."""
    return voting.get_predictions(chat_id)
