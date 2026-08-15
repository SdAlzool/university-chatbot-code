import time
from google.cloud.firestore_v1.base_query import FieldFilter
from config import db

CACHE_TTL_SECONDS = 300
_cached_text = {"text": "", "last_updated": 0}

SESSION_EXPIRATION_SECONDS = 86400
LAST_ACTIVE_THROTTLE_SECONDS = 600

def get_knowledge_base_text():
    now = time.time()
    if now - _cached_text["last_updated"] < CACHE_TTL_SECONDS and _cached_text["text"]:
        return _cached_text["text"]
    docs = db.collection("knowledge_base").stream()
    knowledge = [f"- {d.to_dict().get('topic','')}: {d.to_dict().get('content','')}" for d in docs]
    _cached_text["text"] = "\n".join(knowledge)
    _cached_text["last_updated"] = now
    return _cached_text["text"]

def _get_active_user(collection_name, chat_id):
    query = db.collection(collection_name).where(
        filter=FieldFilter("chat_id", "==", str(chat_id))
    ).limit(1).stream()
    
    for doc in query:
        data = doc.to_dict()
        last_active = data.get("last_active", 0)
        now = time.time()
        if now - last_active > SESSION_EXPIRATION_SECONDS:
            db.collection(collection_name).document(doc.id).update({
                "chat_id": None, "last_active": None
            })
            return None, None
        if now - last_active >= LAST_ACTIVE_THROTTLE_SECONDS:
            db.collection(collection_name).document(doc.id).update({"last_active": now})
        return doc.id, data
    return None, None

def get_student_by_chat_id(chat_id):
    return _get_active_user("students", chat_id)

def get_instructor_by_chat_id(chat_id):
    return _get_active_user("instructors", chat_id)