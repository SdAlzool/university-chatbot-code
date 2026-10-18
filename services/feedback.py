"""التقييم بالنجوم وإحصائيات الردود (Feedback Stars).

كل رد جوهري من البوت يتسجّل كمحادثة، والمستخدم يقيّمه من 1 إلى 5 نجوم.
السجلّ يغذّي لوحة تحكم المشرفين بثلاثة مؤشرات كما وردت في الدراسة:
 - متوسط تقييم الردود
 - المحادثات الناجحة (تقييم 4 أو 5)
 - متوسط زمن الاستجابة
"""

import logging

from firebase_admin import firestore

from services.firebase_db import db

COLLECTION = "feedback"
SUCCESS_MIN_RATING = 4  # المحادثة "ناجحة" إذا كانت4 أو 5
MAX_QUESTION_CHARS = 300
MAX_ANSWER_CHARS = 600


def create_feedback(user_id, channel, question, answer, latency_ms=None):
    """يسجّل محادثة جديدة بحالة «لم يُقيَّم بعد» ويعيد معرّف مستندها.

    يعيد None عند الفشل حتى لا تتعطّل رسالة الرد بسبب مشكلة في التسجيل.
    """
    try:
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
