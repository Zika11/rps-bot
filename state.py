import asyncio

active_games = {}
pending_matches = []
active_locks = asyncio.Lock()

spectate_challenges = {}
spectate_lock = asyncio.Lock()

group_game_sessions = {}
group_session_lock = asyncio.Lock()

# تحديات مفتوحة في القنوات
open_challenges = {}
open_challenge_lock = asyncio.Lock()

# تتبع ألعاب المجموعة الفردية (لاعب -> بيانات)
group_solo_games = {}

async def add_pending(user_id):
    async with active_locks:
        if user_id in pending_matches:
            return None
        if user_id in active_games:
            return None
        if pending_matches:
            opp = pending_matches.pop(0)
            active_games[user_id] = {"type": "random", "opponent": opp}
            active_games[opp] = {"type": "random", "opponent": user_id}
            return opp
        else:
            pending_matches.append(user_id)
            return True

async def remove_game(user_id):
    async with active_locks:
        game = active_games.pop(user_id, None)
        if game and game["type"] == "random":
            opp = game.get("opponent")
            if opp and opp in active_games:
                del active_games[opp]
