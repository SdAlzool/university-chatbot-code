"""التقييم بالنجوم وإحصائيات الردود (Feedback Stars).

كل رد جوهري من البوت يتسجّل كمحادثة، والمستخدم يقيّمه من 1 إلى 5 نجوم.
السجلّ يغذّي لوحة تحكم المشرفين بثلاثة مؤشرات كما وردت في الدراسة:
 - متوسط تقييم الردود
 - المحادثات الناجحة (تقييم 4 أو 5)
 - متوسط زمن الاستجابة
"""

import logging
from datetime import datetime, timedelta, timezone

from firebase_admin import firestore

from services.firebase_db import db

COLLECTION = "feedback"
SUCCESS_MIN_RATING = 4  # المحادثة "ناجحة" إذا كانت4 أو 5
MAX_QUESTION_CHARS = 300
MAX_ANSWER_CHARS = 600

# سياسة رسالة التقييم المؤجّلة: يُطلب التقييم في رسالة منفصلة بعد الرد
# مباشرةً بدل أزرار تحته، وبحد أقصى مرة واحدة كل24 ساعة لكل مستخدم.
PROMPT_DELAY_SECONDS = 5 * 60        # التأخير قبل طلب التقييم (5 دقائق)
PROMPT_COOLDOWN_SECONDS = 24 * 3600  # لا تكرار الطلب لنفس المستخدم/القناة
PROMPT_EXPIRE_SECONDS = 24 * 3600    # إلغاء أي طلب تجاوز24 ساعة دون إرسال
PROMPT_SWEEP_SECONDS = 60            # دورة فحص المستحقات (ثانية)


def _utcnow():
    """وقت UTC بلا منطقة زمنية (Firestore يعيد التواريخ هكذا)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_feedback(user_id, channel, question, answer, latency_ms=None):
    """يسجّل محادثة جديدة بحالة «لم يُقيَّم بعد» ويعيد معرّف مستندها.

    يعيد None عند الفشل حتى لا تتعطّل رسالة الرد بسبب مشكلة في التسجيل.
    """
    try:
        now = _utcnow()
        ref = db.collection(COLLECTION).document()
        ref.set({
            "user_id": str(user_id or ""),
            "channel": str(channel or ""),
            "question": str(question or "")[:MAX_QUESTION_CHARS],
            "answer": str(answer or "")[:MAX_ANSWER_CHARS],
            "rating": None,
            "latency_ms": int(latency_ms) if latency_ms else None,
            "created_at": firestore.SERVER_TIMESTAMP,
            "rated_at": None,
            # رسالة التقييم المؤجّلة (تُرسل بعد PROMPT_DELAY_SECONDS كحد أدنى)
            "prompt_status": "pending",
            "prompt_due_at": now + timedelta(seconds=PROMPT_DELAY_SECONDS),
            "prompted_at": None,
        })
        return ref.id
    except Exception:
        logging.exception("create_feedback failed")
        return None


def rate_feedback(doc_id, rating, user_id=None):
    """يختم التقييم (1-5) على محادثة. يعيد True عند القبول.

    التقييم نهائي: لا يُعاد فتحه، ولا يقيّم أحدٌ غير صاحب المحادثة.
    """
    if not doc_id:
        return False
    try:
        rating = max(1, min(5, int(rating)))
    except (TypeError, ValueError):
        return False
    try:
        ref = db.collection(COLLECTION).document(str(doc_id))
        snap = ref.get()
        if not snap.exists:
            return False
        data = snap.to_dict() or {}
        if data.get("rating") is not None:
            return False
        owner = str(data.get("user_id") or "")
        if user_id is not None and owner and owner != str(user_id):
            return False
        ref.update({"rating": rating, "rated_at": firestore.SERVER_TIMESTAMP})
        return True
    except Exception:
        logging.exception("rate_feedback failed")
        return False


# ============================================================
# طلبات التقييم المؤجّلة (رسالة منفصلة بعد الرد)
# ============================================================

def _as_naive_utc(value):
    """يحوّل قيمة تاريخ من Firestore إلى UTC بلا منطقة زمنية، أو None."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    return None


def _set_prompt_status(ref, status):
    try:
        ref.update({"prompt_status": status})
    except Exception:
        logging.exception("set prompt_status=%s failed", status)


def _recently_prompted(target, channel, now):
    """True إذا أُرسل طلب تقييم لهذا المستخدم خلال فترة الكولداون (24 ساعة)."""
    cutoff = now - timedelta(seconds=PROMPT_COOLDOWN_SECONDS)
    try:
        docs = (
            db.collection(COLLECTION)
            .where("user_id", "==", str(target))
            .stream()
        )
    except Exception:
        logging.exception("recently_prompted query failed")
        return True  # عند الخطأ نمنع الإرسال حتى لا نزعج المستخدم
    for doc in docs:
        data = doc.to_dict() or {}
        if data.get("channel") != channel:
            continue
        prompted = _as_naive_utc(data.get("prompted_at"))
        if prompted and prompted >= cutoff:
            return True
    return False


def claim_due_prompts(channel, limit=25):
    """يختار طلبات التقييم المستحقة للإرسال ويعيد [(doc_id, target)].

    السياسة:
     - كل رد مسجّل يصبح مستحقاً بعد PROMPT_DELAY_SECONDS (5 دقائق).
     - لكل مستخدم/قناة طلب واحد فقط: يُختار أحدث الردود المستحقة،
       وما سواه يُلغى (superseded).
     - لا تكرار قبل مضيّ PROMPT_COOLDOWN_SECONDS (24 ساعة).
     - الطلبات الأقدم من PROMPT_EXPIRE_SECONDS تُلغى (expired) فلا تُزعج.
    """
    try:
        now = _utcnow()
        pending = (
            db.collection(COLLECTION)
            .where("prompt_status", "==", "pending")
            .stream()
        )
        due = {}  # target -> [(due_at, ref)]
        for doc in pending:
            data = doc.to_dict() or {}
            if data.get("channel") != channel:
                continue
            target = str(data.get("user_id") or "")
            if not target:
                continue
            due_at = _as_naive_utc(data.get("prompt_due_at"))
            if due_at is None or due_at > now:
                continue
            if (now - due_at).total_seconds() > PROMPT_EXPIRE_SECONDS:
                _set_prompt_status(doc.reference, "expired")
                continue
            due.setdefault(target, []).append((due_at, doc.reference))
    except Exception:
        logging.exception("claim_due_prompts query failed")
        return []

    result = []
    for target, items in list(due.items())[:limit]:
        items.sort(key=lambda x: x[0])  # الأقدم أولاً
        latest_ref = items[-1][1]
        for _, ref in items[:-1]:
            _set_prompt_status(ref, "superseded")
        if _recently_prompted(target, channel, now):
            _set_prompt_status(latest_ref, "rate_limited")
            continue
        try:
            latest_ref.update({"prompt_status": "sent", "prompted_at": now})
        except Exception:
            logging.exception("claim prompt update failed")
            continue
        result.append((latest_ref.id, target))
    return result


def feedback_stats():
    """إحصائيات لوحة التحكم. ترجع قيم صفراً عند أي خطأ بدل أن تفشل."""
    empty = {
        "total": 0,
        "rated": 0,
        "avg_rating": 0.0,
        "success": 0,
        "success_pct": 0.0,
        "avg_latency_ms": 0,
    }
    try:
        docs = list(db.collection(COLLECTION).stream())
    except Exception:
        logging.exception("feedback_stats failed")
        return dict(empty)

    ratings = []
    latencies = []
    success = 0
    for doc in docs:
        data = doc.to_dict() or {}
        rating = data.get("rating")
        if isinstance(rating, (int, float)):
            ratings.append(rating)
            if rating >= SUCCESS_MIN_RATING:
                success += 1
        latency = data.get("latency_ms")
        if isinstance(latency, (int, float)) and latency >= 0:
            latencies.append(latency)

    rated = len(ratings)
    return {
        "total": len(docs),
        "rated": rated,
        "avg_rating": (sum(ratings) / rated) if rated else 0.0,
        "success": success,
        "success_pct": (100.0 * success / rated) if rated else 0.0,
        "avg_latency_ms": int(sum(latencies) / len(latencies)) if latencies else 0,
    }


def format_stats(stats=None):
    """يجهّز نص المؤشرات جاهزاً للعرض في لوحة التحكم."""
    if stats is None:
        stats = feedback_stats()
    if not stats["rated"]:
        return (
            "⭐ التقييمات\n"
            "لا توجد تقييمات بعد\n"
            f"المحادثات المسجّلة: {stats['total']}\n"
            "لم يقيّم أحد ردود البوت حتى الآن."
        )
    latency = stats["avg_latency_ms"] / 1000.0
    return (
        "⭐ التقييمات وإحصائيات الردود\n\n"
        f"المحادثات المسجّلة: {stats['total']}\n"
        f"تم تقييمها: {stats['rated']}\n"
        f"متوسط التقييم: {stats['avg_rating']:.2f} / 5\n"
        f"المحادثات الناجحة (4-5 ⭐): {stats['success']} "
        f"({stats['success_pct']:.0f}%)\n"
        f"متوسط زمن الاستجابة: {latency:.2f} ثانية"
    )
