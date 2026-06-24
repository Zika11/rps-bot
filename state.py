import asyncio

active_games_lock = asyncio.Lock()
pending_matches_lock = asyncio.Lock()
channel_games_lock = asyncio.Lock()
channel_tasks_lock = asyncio.Lock()

pending_matches = []
active_games = {}
channel_tasks = {}
channel_games = {}
channel_last_play = {}
