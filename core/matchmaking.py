import asyncio
import logging
import time
from typing import Optional, Dict, List, Tuple
import db
import state

logger = logging.getLogger(__name__)

class MatchmakingQueue:
    """نظام مطابقة متقدم مع قوائم انتظار وإلغاء تلقائي"""
    
    def __init__(self):
        self.queues = {}  # game_type -> list of user_ids
        self.match_timeouts = {}  # user_id -> timestamp
        self.lock = asyncio.Lock()
        self.TIMEOUT_SECONDS = 30
        self.CLEANUP_INTERVAL = 10
    
    async def add_player(self, user_id: int, game_type: str = "random") -> Tuple[bool, Optional[int]]:
        """
        إضافة لاعب إلى قائمة الانتظار
        Returns: (تمت المطابقة, opponent_id أو None)
        """
        async with self.lock:
            # التحقق من وجود اللاعب بالفعل في القائمة
            if user_id in self.match_timeouts:
                return False, None
            
            # إضافة اللاعب لقائمة الانتظار
            if game_type not in self.queues:
                self.queues[game_type] = []
            
            # البحث عن خصم
            queue = self.queues[game_type]
            if queue:
                opponent_id = queue.pop(0)
                # إنشاء اللعبة
                game_id = await self._create_match(user_id, opponent_id, game_type)
                if game_id:
                    # إزالة التايم أوت
                    self.match_timeouts.pop(user_id, None)
                    self.match_timeouts.pop(opponent_id, None)
                    return True, opponent_id
                else:
                    # فشل إنشاء اللعبة، إعادة الخصم للقائمة
                    queue.append(opponent_id)
                    return False, None
            else:
                # إضافة للقائمة
                queue.append(user_id)
                self.match_timeouts[user_id] = time.time()
                # جدولة الإلغاء التلقائي
                asyncio.create_task(self._auto_cancel(user_id, game_type))
                return False, None
    
    async def _create_match(self, user1: int, user2: int, game_type: str) -> Optional[str]:
        """إنشاء مباراة جديدة بين لاعبين"""
        try:
            game_id = f"{game_type}_{user1}_{user2}_{int(time.time())}"
            conn = db.get_conn()
            conn.execute(
                "INSERT INTO active_games (game_id, player1, player2, type, status, data) VALUES (?,?,?,?,?,?)",
                (game_id, user1, user2, game_type, "waiting", "{}")
            )
            conn.commit()
            conn.close()
            return game_id
        except Exception as e:
            logger.error(f"فشل إنشاء المباراة: {e}")
            return None
    
    async def _auto_cancel(self, user_id: int, game_type: str):
        """إلغاء تلقائي للاعب إذا انتهى الوقت"""
        await asyncio.sleep(self.TIMEOUT_SECONDS)
        async with self.lock:
            if user_id in self.match_timeouts:
                # حذف من قائمة الانتظار
                if game_type in self.queues:
                    queue = self.queues[game_type]
                    if user_id in queue:
                        queue.remove(user_id)
                self.match_timeouts.pop(user_id, None)
                # إخطار المستخدم (سيتم التعامل معه في الـ handler)
    
    async def cancel_matchmaking(self, user_id: int) -> bool:
        """إلغاء المطابقة للاعب"""
        async with self.lock:
            if user_id not in self.match_timeouts:
                return False
            # إزالة من جميع القوائم
            for queue in self.queues.values():
                if user_id in queue:
                    queue.remove(user_id)
            self.match_timeouts.pop(user_id, None)
            return True
    
    async def get_queue_status(self, user_id: int) -> Optional[Dict]:
        """الحصول على حالة اللاعب في قائمة الانتظار"""
        async with self.lock:
            if user_id not in self.match_timeouts:
                return None
            remaining = int(self.TIMEOUT_SECONDS - (time.time() - self.match_timeouts[user_id]))
            return {
                "position": 0,  # يمكن تحسينه بحساب الموقع الفعلي
                "timeout": max(0, remaining),
                "total_players": sum(len(q) for q in self.queues.values())
            }
    
    async def cleanup_old_matches(self):
        """تنظيف المباريات القديمة العالقة"""
        while True:
            await asyncio.sleep(self.CLEANUP_INTERVAL)
            try:
                cutoff = (datetime.now() - timedelta(minutes=5)).isoformat()
                conn = db.get_conn()
                conn.execute("DELETE FROM active_games WHERE status='waiting' AND created_at < ?", (cutoff,))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"خطأ في تنظيف المباريات العالقة: {e}")

# مثيل واحد للاستخدام
matchmaking = MatchmakingQueue()
