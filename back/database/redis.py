import redis
import json
import logging
from typing import Optional, Any
from back.core.settings import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    global _redis_client

    if _redis_client is None:
        try:
            password = settings.REDIS_PASSWORD
            if isinstance(password, str):
                password = password.strip() or None

            def _build_client(pwd: Optional[str]) -> redis.Redis:
                return redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    password=pwd,
                    db=0,
                    decode_responses=True,
                )

            _redis_client = _build_client(password)
            try:
                _redis_client.ping()
            except redis.exceptions.AuthenticationError:
                logger.warning("[REDIS AUTH FALLBACK] Retry without password")
                _redis_client = _build_client(None)
                _redis_client.ping()

            logger.info(f"[REDIS CONNECTED] {settings.REDIS_HOST}:{settings.REDIS_PORT}")

        except Exception as e:
            logger.error(f"[REDIS CONNECTION ERROR] {e}")
            raise e

    return _redis_client


def set_cache(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    try:
        client = get_redis_client()

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        if ttl:
            client.setex(key, ttl, value)
        else:
            client.set(key, value)

        logger.info(f"[REDIS SET] {key}")
        return True

    except Exception as e:
        logger.error(f"[REDIS ERROR SET] {e}")
        return False


def get_cache(key: str) -> Optional[Any]:
    try:
        client = get_redis_client()
        value = client.get(key)

        logger.info(f"[REDIS GET] {key}")

        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

        return None

    except Exception as e:
        logger.error(f"[REDIS ERROR GET] {e}")
        return None


def delete_cache(key: str) -> bool:
    try:
        client = get_redis_client()
        client.delete(key)
        logger.info(f"[REDIS DEL] {key}")
        return True
    except Exception as e:
        logger.error(f"[REDIS ERROR DEL] {e}")
        return False