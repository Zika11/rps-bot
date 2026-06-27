import json
import logging
from typing import Optional, Any
from core.redis_client import redis_client
import db

logger = logging.getLogger(__name__)

class CacheService:
    """خدمة التخزين المؤقت للبيانات"""
    
    CACHE_TTL = {
        "user": 300,
        "rating": 600,
        "leaderboard": 300,
        "clan": 600,
        "settings": 3600,
        "boss": 60,
        "tournament": 300,
        "game_state": 60,
    }

    @staticmethod
    def get_user(user_id: int) -> Optional[dict]:
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
        db.update_user(user_id, **kwargs)
        cache_key = f"user:{user_id}"
        redis_client.delete(cache_key)

    @staticmethod
    def get_rating(user_id: int) -> Optional[int]:
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
        db.update_rating(user_id, new_rating)
        redis_client.delete(f"rating:{user_id}")
        redis_client.delete("leaderboard:global")

    @staticmethod
    def get_leaderboard(limit: int = 10) -> list:
        cache_key = f"leaderboard:global:{limit}"
        cached = redis_client.get(cache_key)
        if cached:
            return cached
        leaderboard = db.get_top_ratings(limit)
        redis_client.set(cache_key, leaderboard, CacheService.CACHE_TTL["leaderboard"])
        return leaderboard

    @staticmethod
    def get_settings() -> dict:
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
    def get_tournament(tour_id: int) -> Optional[dict]:
        cache_key = f"tournament:{tour_id}"
        cached = redis_client.get(cache_key)
        if cached:
            return cached
        tournament = db.get_tournament(tour_id)
        if tournament:
            redis_client.set(cache_key, tournament, CacheService.CACHE_TTL["tournament"])
        return tournament

    @staticmethod
    def update_tournament(tour_id: int, **kwargs) -> None:
        db.update_tournament(tour_id, **kwargs)
        redis_client.delete(f"tournament:{tour_id}")

    @staticmethod
    def get_world_boss() -> Optional[dict]:
        cache_key = "world_boss:active"
        cached = redis_client.get(cache_key)
        if cached:
            return cached
        boss = db.get_world_boss()
        if boss:
            redis_client.set(cache_key, boss, CacheService.CACHE_TTL["boss"])
        return boss

    @staticmethod
    def clear_user_cache(user_id: int) -> None:
        patterns = [
            f"user:{user_id}",
            f"rating:{user_id}",
            f"user_gems:{user_id}",
            f"user_points:{user_id}",
        ]
        for pattern in patterns:
            redis_client.delete(pattern)

    @staticmethod
    def clear_all_cache() -> None:
        patterns = ["user:*", "rating:*", "leaderboard:*", "tournament:*", "world_boss:*"]
        for pattern in patterns:
            redis_client.clear_pattern(pattern)

# مثيل للاستخدام
cache = CacheService()
