import asyncio

active_games = {}
pending_matches = []
active_locks = asyncio.Lock()

# تحديات المشاهدة: مفتاح challenge_id، قيمة dict {players, group_id, moves, ...}
spectate_challenges = {}
spectate_lock = asyncio.Lock()

async def add_pending(user_id):
    """إضافة لاعب لقائمة الانتظار أو إرجاع الخصم لو فيه لاعب منتظر"""
    async with active_locks:
        if user_id in pending_matches:
            return None  # بالفعل في الانتظار
        if user_id in active_games:
            return None  # مشغول بلعبة حالياً
        if pending_matches:
            opp = pending_matches.pop(0)
            active_games[user_id] = {"type": "random", "opponent": opp}
            active_games[opp] = {"type": "random", "opponent": user_id}
            return opp
        else:
            pending_matches.append(user_id)
            return True  # بانتظار خصم

async def remove_game(user_id):
    """إزالة اللعبة من الذاكرة لكلا الطرفين إن وُجدا"""
    async with active_locks:
        game = active_games.pop(user_id, None)
        if game and game["type"] == "random":
            opp = game.get("opponent")
            if opp and opp in active_games:
                del active_games[opp]
