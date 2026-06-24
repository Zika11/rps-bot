import asyncio

active_games = {}
pending_matches = []
active_locks = asyncio.Lock()
