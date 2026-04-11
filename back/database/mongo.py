from pymongo import MongoClient, ASCENDING
from back.core.settings import settings
from datetime import datetime
from typing import List, Dict, Any, Optional

_mongo_client: Optional[MongoClient] = None


def get_mongo_client():
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(settings.MONGO_URL)
    return _mongo_client


def get_chat_collection():
    client = get_mongo_client()
    db = client[settings.MONGO_DB]
    return db["pharma_logs"]


def add_chat_message(user_id: str, role: str, content: str, tool: str = None) -> bool:
    try:
        collection = get_chat_collection()
        collection.insert_one({
            "user_id": user_id,
            "role": role,
            "content": content,
            "tool": tool,
            "timestamp": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow()
        })
        return True
    except Exception as e:
        print("MongoDB insert_chat_message failed")
        print("Reason:", e)
        return False


def get_chat_history(user_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    try:
        collection = get_chat_collection()

        query = {"user_id": user_id}
        cursor = collection.find(query, {"_id": 0}).sort("created_at", ASCENDING)

        if limit is not None:
            cursor = cursor.limit(limit)

        return list(cursor)
    except Exception as e:
        print("MongoDB get_chat_history failed")
        print("Reason:", e)
        return []


def get_last_chat_message(user_id: str) -> Optional[Dict[str, Any]]:
    try:
        collection = get_chat_collection()
        doc = collection.find_one(
            {"user_id": user_id},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        return doc
    except Exception as e:
        print("MongoDB get_last_chat_message failed")
        print("Reason:", e)
        return None


def clear_chat_history(user_id: str) -> bool:
    try:
        collection = get_chat_collection()
        collection.delete_many({"user_id": user_id})
        return True
    except Exception as e:
        print("MongoDB clear_chat_history failed")
        print("Reason:", e)
        return False


def insert_chat(user_id, messages):
    collection = get_chat_collection()

    if isinstance(messages, list):
        docs = []
        now = datetime.utcnow()
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            docs.append({
                "user_id": user_id,
                "role": msg.get("role"),
                "content": msg.get("content"),
                "tool": msg.get("tool"),
                "timestamp": msg.get("timestamp", now.isoformat()),
                "created_at": now
            })

        if docs:
            collection.insert_many(docs)
    else:
        collection.insert_one({
            "user_id": user_id,
            "messages": messages,
            "created_at": datetime.utcnow()
        })


if __name__ == "__main__":
    try:
        client = get_mongo_client()
        client.admin.command("ping")
        print("MongoDB connected successfully")

    except Exception as e:
        print("MongoDB connection failed")
        print("Reason:", e)