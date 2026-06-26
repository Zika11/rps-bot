import json
import logging
from typing import Optional, Any
from core.redis_client import redis_client
import db

logger = logging.getLogger(__name__)

class CacheService:
    """خدمة التخزين المؤقت للبيانات"""
    
    CACHE_TTL = {
        "user": 300,      # 5 دقائق
        "rating": 600,    # 10 دقائق
        "leaderboard": 300,
        "clan": 600,
        "settings": 3600, # ساعة
    }

    @staticmethod
    def get_user(user_id: int) -> Optional[dict]:
        """جلب المستخدم من Cache أو قاعدة البيانات"""
        cache_key = f"user:{user_id}"
        cached = redis_client.get(cache_key)
        if cached:
            return cached
        
        user = db.get_user(user_id)
        if user:
            redis_client.set(cache_key, user, CacheService.CACHE_TTL["user"])
        return user

    @staticmethod
    def update_user(user_id: int, **kwargs) -> None:
        """تحديث المستخدم وتحديث Cache"""
        db.update_user(user_id, **kwargs)
        cache_key = f"user:{user_id}"
        redis_client.delete(cache_key)

    @staticmethod
    def get_rating(user_id: int) -> Optional[int]:
        """جلب التصنيف من Cache"""
        cache_key = f"rating:{user_id}"
        cached = redis_client.get(cache_key)
        if cached:
            return cached
        
        rating = db.get_user_rating(user_id)
        if rating:
            redis_client.set(cache_key, rating, CacheService.CACHE_TTL["rating"])
        return rating

    @staticmethod
    def update_rating(user_id: int, new_rating: int) -> None:
        """تحديث التصنيف وتحديث Cache"""
        db.update_rating(user_id, new_rating)
        redis_client.delete(f"rating:{user_id}")
        redis_client.delete("leaderboard:global")

    @staticmethod
    def get_leaderboard(limit: int = 10) -> list:
        """جلب لوحة المتصدرين من Cache"""
        cache_key = f"leaderboard:global:{limit}"
        cached = redis_client.get(cache_key)
        if cached:
            return cached
        
        leaderboard = db.get_top_ratings(limit)
        redis_client.set(cache_key, leaderboard, CacheService.CACHE_TTL["leaderboard"])
        return leaderboard

    @staticmethod
    def get_settings() -> dict:
        """جلب إعدادات البوت من Google Sheets مع Cache"""
        cache_key = "settings:gsheets"
        cached = redis_client.get(cache_key)
        if cached:
            return cached
        
        from core.google_sheets import gsheets
        if gsheets.is_connected():
            settings = gsheets.get_settings()
            if settings:
                redis_client.set(cache_key, settings, CacheService.CACHE_TTL["settings"])
                return settings
        return {}

    @staticmethod
    def clear_user_cache(user_id: int) -> None:
        """مسح جميع Cache الخاصة بمستخدم"""
        patterns = [
            f"user:{user_id}",
            f"rating:{user_id}",
            f"user_gems:{user_id}",
            f"user_points:{user_id}",
        ]
        for pattern in patterns:
            redis_client.delete(pattern)

# مثيل للاستخدام
cache = CacheService()
