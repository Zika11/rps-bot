import json
import logging
import random
from collections import defaultdict
from config import *
import db

def is_founder(user_id):
    """التحقق مما إذا كان المستخدم هو المؤسس."""
    return user_id == FOUNDER_ID

def get_choices_for_user(user_id):
    u = db.get_user(user_id)
    theme = (u.get("theme") if u else None) or "theme_1"
    return THEME_ICONS.get(theme, CHOICES)

def get_result(p1, p2):
    return "draw" if p1 == p2 else ("win" if WIN_MAP[p1] == p2 else "loss")

# 🧠 ذكاء اصطناعي متطور - Markov Chain Order-2
def markov_bot_choice(user_id):
    u = db.get_user(user_id)
    if not u:
        return random.choice(list(CHOICES.keys()))
    try:
        moves = json.loads(u.get("move_history", "[]"))
    except:
        moves = []
    if len(moves) < 3:
        return random.choice(list(CHOICES.keys()))

    chain = defaultdict(lambda: defaultdict(int))
    for i in range(len(moves) - 2):
        key = (moves[i], moves[i+1])
        next_move = moves[i+2]
        chain[key][next_move] += 1

    last_two = (moves[-2], moves[-1])
    possible = chain.get(last_two)
    if not possible:
        predicted = random.choice(list(CHOICES.keys()))
    else:
        predicted = max(possible, key=possible.get)

    for k, v in WIN_MAP.items():
        if v == predicted:
            return k
    return random.choice(list(CHOICES.keys()))

def update_user_moves(user_id, move):
    u = db.get_user(user_id)
    if not u: return
    try:
        moves = json.loads(u.get("move_history", "[]"))
    except:
        moves = []
    moves.append(move)
    if len(moves) > 50: moves = moves[-50:]
    db.update_user(user_id, move_history=json.dumps(moves))
