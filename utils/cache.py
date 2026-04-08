import redis
import json
from flask import current_app

# Redis client
redis_client = None

def init_redis(app):
    """Initialize Redis client."""
    global redis_client
    redis_url = app.config.get('CACHE_REDIS_URL', 'redis://localhost:6379/3')
    redis_client = redis.from_url(redis_url, decode_responses=True)
    return redis_client


def cache_get(key):
    """Get value from cache."""
    if redis_client is None:
        return None
    
    try:
        value = redis_client.get(key)
        if value:
            return json.loads(value)
    except Exception as e:
        print(f"Cache get error: {e}")
    return None


def cache_set(key, value, timeout=300):
    """Set value in cache with timeout."""
    if redis_client is None:
        return False
    
    try:
        redis_client.setex(key, timeout, json.dumps(value))
        return True
    except Exception as e:
        print(f"Cache set error: {e}")
    return False


def cache_delete(key):
    """Delete value from cache."""
    if redis_client is None:
        return False
    
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        print(f"Cache delete error: {e}")
    return False


def invalidate_cache(pattern):
    """Invalidate cache by pattern."""
    if redis_client is None:
        return False
    
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
        return True
    except Exception as e:
        print(f"Cache invalidate error: {e}")
    return False


def invalidate_prefix(prefix):
    """Invalidate all keys starting with prefix."""
    return invalidate_cache(f"{prefix}*")
