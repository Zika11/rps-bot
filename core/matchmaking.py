import asyncio
import logging
import random
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

import db
import state

logger = logging.getLogger(__name__)

class MatchmakingManager:
    """
    مدير المطابقة المتقدم - يدعم:
    - قوائم انتظار
    - إلغاء تلقائي بعد 30 ثانية
    - إعادة محاولة
    - إرسال إشعارات
    """
    
    # تخزين المباريات النشطة في الذاكرة
    _pending = {}  # user_id -> timestamp
    _games = {}    # game_id -> {"p1": id, "p2": id, "status": str}
    _locks = {}    # user_id -> asyncio.Lock
    
    @classmethod
    async def find_match(cls, user_id: int, timeout: int = 30) -> Optional[int]:
        """
        البحث عن خصم للمستخدم.
        تعيد user_id للخصم، أو None إذا لم يوجد.
        """
        async with cls._get_lock(user_id):
            # حذف المعلقين القدامى
            cls._cleanup_pending()
            
            # إضافة المستخدم لقائمة الانتظار
            cls._pending[user_id] = datetime.now()
            
            # البحث عن خصم
            opponent = cls._find_opponent(user_id)
            if opponent:
                # حذف المستخدمين من قائمة الانتظار
                cls._pending.pop(user_id, None)
                cls._pending.pop(opponent, None)
                return opponent
            
            # انتظار خصم (timeout)
            try:
                await asyncio.sleep(timeout)
                # البحث مرة أخرى
                opponent = cls._find_opponent(user_id)
                if opponent:
                    cls._pending.pop(user_id, None)
                    cls._pending.pop(opponent, None)
                    return opponent
            except asyncio.CancelledError:
                pass
            
            # لم يتم العثور على خصم
            cls._pending.pop(user_id, None)
            return None
    
    @classmethod
    def _find_opponent(cls, user_id: int) -> Optional[int]:
        """البحث عن خصم مناسب في قائمة الانتظار"""
        # استبعاد المستخدم نفسه
        candidates = [uid for uid in cls._pending.keys() if uid != user_id]
        if not candidates:
            return None
        
        # اختيار عشوائي لعدالة التوزيع
        return random.choice(candidates)
    
    @classmethod
    def _cleanup_pending(cls):
        """حذف المستخدمين المعلقين منذ أكثر من 60 ثانية"""
        now = datetime.now()
        expired = []
        for uid, timestamp in cls._pending.items():
            if (now - timestamp).total_seconds() > 60:
                expired.append(uid)
        for uid in expired:
            cls._pending.pop(uid, None)
            logger.debug(f"Removed expired pending user: {uid}")
    
    @classmethod
    async def _get_lock(cls, user_id: int):
        """الحصول على قفل للمستخدم"""
        if user_id not in cls._locks:
            cls._locks[user_id] = asyncio.Lock()
        return cls._locks[user_id]
    
    @classmethod
    def get_pending_count(cls) -> int:
        """عدد المستخدمين في قائمة الانتظار"""
        cls._cleanup_pending()
        return len(cls._pending)
    
    @classmethod
    def get_pending_users(cls) -> List[int]:
        """قائمة المستخدمين في قائمة الانتظار"""
        cls._cleanup_pending()
        return list(cls._pending.keys())

# مثيل افتراضي للاستخدام السريع
matchmaking = MatchmakingManager()
