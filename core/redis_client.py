import json
import redis
from typing import Optional, Any
import config.settings as settings

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
                self._client.ping()  # اختبار الاتصال
            except Exception as e:
                self._client = None
                print(f"⚠️ Redis connection failed: {e}")

    def is_connected(self) -> bool:
        return self._client is not None

    def get(self, key: str) -> Optional[Any]:
        """جلب قيمة من Redis"""
        if not self.is_connected():
            return None
        try:
            value = self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except:
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """تخزين قيمة في Redis مع TTL (ثواني)"""
        if not self.is_connected():
            return False
        try:
            self._client.setex(key, ttl, json.dumps(value))
            return True
        except:
            return False

    def delete(self, key: str) -> bool:
        """حذف مفتاح من Redis"""
        if not self.is_connected():
            return False
        try:
            self._client.delete(key)
            return True
        except:
            return False

    def clear_pattern(self, pattern: str) -> int:
        """حذف جميع المفاتيح التي تطابق النمط"""
        if not self.is_connected():
            return 0
        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except:
            return 0

# مثيل واحد للاستخدام في جميع أنحاء البوت
redis_client = RedisClient()
