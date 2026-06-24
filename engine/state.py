import asyncio

# إعدادات القنوات النشطة (chat_id -> {interval, ttl, task, message_id})
channel_settings = {}
channel_settings_lock = asyncio.Lock()

# أقفال التصويت لكل قناة
vote_locks = {}
vote_lock_creation = asyncio.Lock()

# منع التصويت المتكرر (cooldown)
vote_cooldowns = {}
vote_cooldown_seconds = 2
vote_cooldown_lock = asyncio.Lock()

async def get_vote_lock(chat_id):
    """إرجاع قفل خاص بالقناة وإنشاؤه إذا لزم الأمر"""
    async with vote_lock_creation:
        if chat_id not in vote_locks:
            vote_locks[chat_id] = asyncio.Lock()
        return vote_locks[chat_id]

async def is_spam_vote(chat_id, user_id) -> bool:
    """تعيد True إذا كان التصويت مكرراً قبل مرور فترة التبريد"""
    async with vote_cooldown_lock:
        if chat_id not in vote_cooldowns:
            vote_cooldowns[chat_id] = {}
        now = asyncio.get_event_loop().time()
        last = vote_cooldowns[chat_id].get(user_id, 0)
        if now - last < vote_cooldown_seconds:
            return True
        vote_cooldowns[chat_id][user_id] = now
        return False
