import json
import redis
import logging
from typing import Optional, Any
import config.settings as settings

logger = logging.getLogger(__name__)

class RedisClient:
    """عميل Redis للتخزين المؤقت"""
    
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None and settings.REDIS_ENABLED:
            try:
                self._client = redis.Redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                self._client.ping()
                logger.info("✅ Redis connected successfully")
            except Exception as e:
                self._client = None
                logger.warning(f"⚠️ Redis connection failed: {e}")

    def is_connected(self) -> bool:
        return self._client is not None

    def get(self, key: str) -> Optional[Any]:
        if not self.is_connected():
            return None
        try:
            value = self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.debug(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        if not self.is_connected():
            return False
        try:
            self._client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.debug(f"Redis set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        if not self.is_connected():
            return False
        try:
            self._client.delete(key)
            return True
        except:
            return False

    def clear_pattern(self, pattern: str) -> int:
        if not self.is_connected():
            return 0
        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except:
            return 0

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        if not self.is_connected():
            return None
        try:
            return self._client.incr(key, amount)
        except:
            return None

    def expire(self, key: str, ttl: int) -> bool:
        if not self.is_connected():
            return False
        try:
            return self._client.expire(key, ttl)
        except:
            return False

    def set_json(self, key: str, value: Any, ttl: int = 3600) -> bool:
        return self.set(key, value, ttl)

    def get_json(self, key: str) -> Optional[Any]:
        return self.get(key)

# مثيل واحد للاستخدام
redis_client = RedisClient()
