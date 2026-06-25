# core/game_engine.py
import random
from config import WIN_MAP, CHOICES
import utils

def get_result(p1, p2):
    """حساب نتيجة جولة"""
    if p1 == p2:
        return "draw"
    return "win" if WIN_MAP[p1] == p2 else "loss"

def bot_choice(user_id=None):
    """اختيار البوت للحركة (مع خيار Markov)"""
    if user_id:
        return utils.markov_bot_choice(user_id)
    return random.choice(list(CHOICES.keys()))

def calculate_winner(move1, move2):
    """إرجاع الفائز (1 أو 2 أو 0 للتعادل)"""
    res = get_result(move1, move2)
    if res == "win":
        return 1
    elif res == "loss":
        return 2
    return 0
