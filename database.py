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

def get_chat_language(chat_id):
    doc = db.collection("preferences").document(str(chat_id)).get()
    if doc.exists:
        return doc.to_dict().get("language")
    return None

def set_chat_language(chat_id, language):
    db.collection("preferences").document(str(chat_id)).set({
        "chat_id": str(chat_id),
        "language": language,
    })

WELCOME_COOLDOWN_SECONDS = 5 * 3600

def was_welcome_sent(phone):
    doc = db.collection("wa_welcome").document(phone).get()
    if doc.exists:
        last = doc.to_dict().get("last_sent", 0)
        return (time.time() - last) < WELCOME_COOLDOWN_SECONDS
    return False

def mark_welcome_sent(phone):
    db.collection("wa_welcome").document(phone).set({
        "last_sent": time.time(),
    })

def save_pending_upload(phone, file_data, filename):
    import base64 as _b64
    if isinstance(file_data, bytes):
        if len(file_data) > 800_000:
            return
        encoded = _b64.b64encode(file_data).decode()
    else:
        encoded = file_data
    db.collection("wa_uploads").document(phone).set({
        "data": encoded,
        "filename": filename,
        "created": time.time(),
    })

def get_pending_upload(phone):
    doc = db.collection("wa_uploads").document(phone).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    if time.time() - data.get("created", 0) > 3600:
        db.collection("wa_uploads").document(phone).delete()
        return None
    import base64 as _b64
    raw = data.get("data", "")
    file_data = _b64.b64decode(raw) if isinstance(raw, str) and raw else raw
    return {"data": file_data, "mime": data.get("mime", "application/octet-stream"), "filename": data.get("filename", "file")}

def clear_pending_upload(phone):
    try:
        db.collection("wa_uploads").document(phone).delete()
    except Exception:
        pass