import json
import logging
import redis
from typing import Any, Optional
from backend.config.settings import settings

logger = logging.getLogger("trade_intel.cache.redis")

class RedisCacheClient:
    def __init__(self):
        self.client = None
        self._local_cache = {}
        try:
            logger.info(f"Connecting to Redis at {settings.REDIS_URL}...")
            self.client = redis.Redis.from_url(
                settings.REDIS_URL, 
                socket_timeout=2.0, 
                decode_responses=True
            )
            self.client.ping()
            logger.info("Successfully connected to Redis cache.")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis cache: {e}. Falling back to In-Memory Cache.")
            self.client = None

    def get(self, key: str) -> Optional[str]:
        if self.client:
            try:
                return self.client.get(key)
            except Exception:
                pass
        return self._local_cache.get(key)

    def set(self, key: str, value: str, ex_seconds: int = 3600):
        if self.client:
            try:
                self.client.set(key, value, ex=ex_seconds)
                return
            except Exception:
                pass
        self._local_cache[key] = value

    def get_json(self, key: str) -> Optional[Any]:
        val = self.get(key)
        if val:
            try:
                return json.loads(val)
            except Exception:
                pass
        return None

    def set_json(self, key: str, value: Any, ex_seconds: int = 3600):
        try:
            self.set(key, json.dumps(value), ex_seconds=ex_seconds)
        except Exception:
            pass

redis_cache = RedisCacheClient()
