import json
import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from back.database.redis import get_redis_client, set_cache, get_cache
from back.database.mongo import (
    add_chat_message,
    get_chat_history,
    get_last_chat_message,
    clear_chat_history
)

logger = logging.getLogger(__name__)


class ConversationMemory:
    CONVERSATION_TTL = 86400
    MAX_MESSAGES = 10

    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id or str(uuid.uuid4())
        self.redis_client = get_redis_client()
        self._conversation_key = f"conv:{self.user_id}"
        self._context_key = f"context:{self.user_id}"
        self._metadata_key = f"meta:{self.user_id}"

    @staticmethod
    def _to_str(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        return str(value)

    def add_message(self, role: str, content: str, tool_used: Optional[str] = None) -> bool:
        try:
            saved = add_chat_message(
                user_id=self.user_id,
                role=role,
                content=content,
                tool=tool_used
            )

            if not saved:
                return False

            self._update_metadata()
            return True

        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return False

    def get_conversation_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        try:
            messages = get_chat_history(self.user_id, limit=limit)
            return messages
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []

    def get_last_message(self) -> Optional[Dict[str, Any]]:
        try:
            return get_last_chat_message(self.user_id)
        except Exception as e:
            logger.error(f"Error getting last message: {e}")
            return None

    def get_recent_context(self, limit: int = 5) -> str:
        try:
            messages = self.get_conversation_history(limit)

            context_lines = []
            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "")

                if len(content) > 300:
                    content = content[:300] + "..."

                context_lines.append(f"{role}: {content}")

            return "\n".join(context_lines)

        except Exception as e:
            logger.error(f"Error building context: {e}")
            return ""

    def set_context(self, context_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        try:
            set_cache(
                self._context_key,
                context_data,
                ttl or self.CONVERSATION_TTL
            )
            return True

        except Exception as e:
            logger.error(f"Error setting context: {e}")
            return False

    def get_context(self) -> Optional[Dict[str, Any]]:
        try:
            context = get_cache(self._context_key)

            if isinstance(context, str):
                try:
                    return json.loads(context)
                except Exception:
                    return {"value": context}

            return context

        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return None

    def _update_metadata(self) -> bool:
        try:
            metadata = self._get_metadata()

            if not metadata.get("created_at"):
                metadata["created_at"] = datetime.now().isoformat()

            metadata["last_updated"] = datetime.now().isoformat()
            metadata["user_id"] = self.user_id

            set_cache(
                self._metadata_key,
                metadata,
                self.CONVERSATION_TTL
            )
            return True

        except Exception as e:
            logger.error(f"Error updating metadata: {e}")
            return False

    def _get_metadata(self) -> Dict[str, Any]:
        try:
            metadata = get_cache(self._metadata_key)

            if isinstance(metadata, str):
                try:
                    return json.loads(metadata)
                except Exception:
                    return {}

            return metadata or {}

        except Exception as e:
            logger.error(f"Error getting metadata: {e}")
            return {}

    def clear(self) -> bool:
        try:
            self.redis_client.delete(self._context_key)
            self.redis_client.delete(self._metadata_key)
            self.redis_client.delete(self._conversation_key)
            clear_chat_history(self.user_id)
            return True

        except Exception as e:
            logger.error(f"Error clearing memory: {e}")
            return False


class MemoryManager:

    def __init__(self):
        self.memories: Dict[str, ConversationMemory] = {}
        self.redis_client = get_redis_client()

    def get_or_create_memory(self, user_id: str) -> ConversationMemory:
        if user_id not in self.memories:
            self.memories[user_id] = ConversationMemory(user_id)
        return self.memories[user_id]

    def get_memory(self, user_id: str) -> Optional[ConversationMemory]:
        if user_id not in self.memories:
            self.memories[user_id] = ConversationMemory(user_id)
        return self.memories.get(user_id)

    def clear_user_memory(self, user_id: str) -> bool:
        try:
            memory = self.get_or_create_memory(user_id)
            success = memory.clear()

            if user_id in self.memories:
                del self.memories[user_id]

            return success

        except Exception as e:
            logger.error(f"Error clearing user memory: {e}")
            return False


_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    global _memory_manager

    if _memory_manager is None:
        _memory_manager = MemoryManager()

    return _memory_manager