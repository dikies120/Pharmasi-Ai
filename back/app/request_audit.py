import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from back.core.settings import settings
from back.database.mongo import get_mongo_client
from back.database.redis import set_cache

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 86400
MAX_PREVIEW_LENGTH = 4000


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()
        except Exception:
            pass

    if hasattr(value, "dict"):
        try:
            return value.dict()
        except Exception:
            pass

    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]

    return str(value)


def _clip_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if len(value) <= MAX_PREVIEW_LENGTH:
        return value
    return value[:MAX_PREVIEW_LENGTH] + "..."


def _normalize_payload(value: Any) -> Any:
    data = _to_jsonable(value)

    if isinstance(data, dict):
        return {k: _clip_text(v) for k, v in data.items()}

    if isinstance(data, list):
        return [_clip_text(v) for v in data]

    return _clip_text(data)


def persist_api_io(
    endpoint: str,
    method: str,
    request_data: Any = None,
    response_data: Any = None,
    status: str = "success",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Best-effort audit logging to Redis cache and MongoDB."""
    log_id = uuid.uuid4().hex
    created_at = datetime.utcnow()

    doc = {
        "log_id": log_id,
        "endpoint": endpoint,
        "method": method,
        "status": status,
        "user_id": user_id,
        "request": _normalize_payload(request_data),
        "response": _normalize_payload(response_data),
        "timestamp": created_at.isoformat(),
        "created_at": created_at,
    }

    redis_doc = {
        **doc,
        "created_at": created_at.isoformat(),
    }

    redis_saved = False
    mongo_saved = False

    try:
        redis_saved = set_cache(f"api_log:{log_id}", redis_doc, CACHE_TTL_SECONDS)
    except Exception as e:
        logger.warning(f"Audit Redis save failed: {e}")

    try:
        client = get_mongo_client()
        db = client[settings.MONGO_DB]
        db["api_request_logs"].insert_one(doc)
        mongo_saved = True
    except Exception as e:
        logger.warning(f"Audit Mongo save failed: {e}")

    return {
        "log_id": log_id,
        "redis_saved": redis_saved,
        "mongo_saved": mongo_saved,
    }
