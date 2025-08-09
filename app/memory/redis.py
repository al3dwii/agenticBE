import redis.asyncio as redis
from app.core.config import settings

_client = None
_queue = None

def get_redis():
    global _client
    if _client is None:
        _client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client

def get_queue():
    global _queue
    if _queue is None:
        _queue = redis.from_url(settings.REDIS_URL_QUEUE, decode_responses=True)
    return _queue
