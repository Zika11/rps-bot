import asyncio

# لتخزين الألعاب النشطة (مفتاح: user_id أو معرف اللعبة، قيمة: تفاصيل)
active_games = {}
pending_matches = {}  # مباريات عشوائية بانتظار خصم
active_locks = asyncio.Lock()
