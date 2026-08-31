import asyncio
import logging
import math
import re
import time
from google.genai import types
from config import client, FAST_MODEL, MODEL_NAME, INTENT_MODEL_NAME
from database import get_knowledge_base_text, get_student_by_chat_id, get_chat_language

_fast_cooldown_until = 0.0
_quota_cooldown_until = 0.0
_lite_cooldown_until = 0.0


def _is_daily_quota_error(e):
    msg = str(e)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg


async def call_gemini_with_retry(func, *args, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            return await asyncio.to_thread(func, *args, **kwargs)
        except Exception as e:
            msg = str(e)
            is_rate_limit = "429" in msg or "RESOURCE_EXHAUSTED" in msg
            is_daily_quota = "quota" in msg.lower() or "free_tier" in msg.lower()
            if is_rate_limit and not is_daily_quota and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 10
                logging.warning(f"تجاوز حدود الاستخدام (429). جاري الانتظار {wait_time} ثانية...")
                await asyncio.sleep(wait_time)
            else:
                raise e

# ============================================================
# Security: Prompt Injection guard
# Scans user input for common prompt-injection / jailbreak
# / social-engineering patterns before it reaches the LLM.
# ============================================================
_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions|prompts|directions|context)", re.I),
    re.compile(r"(disregard|forget|ignore).{0,30}(instructions|prompts|constraints|rules)", re.I),
    re.compile(r"you\s+are\s+now\s+(a\s+)?(dan|developer|unfiltered|no\s+(restrictions|limits))", re.I),
    re.compile(r"(act|behave|pretend)\s+as\s+(if\s+)?(a\s+)?(chatgpt|gpt|the\s+ai|superior|god)", re.I),
    re.compile(r"reveal|expose|print|show.{0,20}(system\s+prompt|system\s+instruction|secret|api\s+key|password|token)", re.I),
    re.compile(r"(تجاهل|انسى|نسي).{0,30}(التعليمات|الاوامر|القواعد|السياق)", re.I),
    re.compile(r"انت\s+(الان\s+)?(دان|مساعد\s+بلا\s+قوانين|بلا\s+قيود|الفطر\s+المحرر)", re.I),
)

_INJECTION_SAFE_REPLY_EN = (
    "I can't do that. I'm only here to help with university services. "
    "If you need help, please contact university support."
)
_INJECTION_SAFE_REPLY_AR = (
    "ما أقدر أعمل كده. أنا موجود فقط لمساعدة الطلاب في خدمات الجامعة. "
    "لو محتاج مساعدة تواصل مع الدعم الجامعي."
)


def prompt_injection_guard(text):
    """Returns True if the input looks like a prompt-injection attack."""
    return any(p.search(text) for p in _INJECTION_PATTERNS)


def injection_safe_reply(language="ar"):
    return _INJECTION_SAFE_REPLY_EN if language == "en" else _INJECTION_SAFE_REPLY_AR


_ADD_KEYWORDS = ("اضيف", "أضيف", "ارفع", "رفع", "اضافة", "إضافة", "زود", "اضيفو", "رفعت")
_DELETE_KEYWORDS = ("احزف", "احذف", "حذف", "امسح", "مسح", "ازيل", "إزالة", "شيل", "امسحي", "احذفو")
_SUMMARIZE_KEYWORDS = (
    "لخص", "لخّص", "تلخيص", "ملخص", "لخصلي",
    "summarize", "summarise", "summary", "sum up", "tldr", "tl;dr",
)
_LOGIN_KEYWORDS = ("تسجيل دخول", "سجل دخول", "دخول", "login", "لوجن", "سجلني")
_LOGOUT_KEYWORDS = ("تسجيل خروج", "خروج", "logout", "لوقاوت")
_COURSES_KEYWORDS = ("مقررات", "موادي", "المواد", "كورسات", "الكورسات", "المواد بتاعتي")
_SHEETS_KEYWORDS = ("شيت", "شيتات", "محاضرة", "ملف", "pdf", "ملازم", "ملفات")


def _keyword_intent(text):
    t = text.lower().strip()
    if any(w in t for w in _DELETE_KEYWORDS):
        return "DR_DELETE_CONTENT"
    if any(w in t for w in _ADD_KEYWORDS):
        return "DR_ADD_CONTENT"
    if any(w in t for w in _SUMMARIZE_KEYWORDS):
        return "SUMMARIZE"
    if any(w in t for w in _LOGIN_KEYWORDS):
        return "LOGIN"
    if any(w in t for w in _LOGOUT_KEYWORDS):
        return "LOGOUT"
    if any(w in t for w in _COURSES_KEYWORDS):
        return "GET_COURSES"
    if any(w in t for w in _SHEETS_KEYWORDS):
        return "GET_SHEETS"
    return None


async def detect_user_intent(text: str, is_instructor: bool = False) -> str:
    keyword = _keyword_intent(text)
    if keyword:
        return keyword
    if is_instructor:
        prompt = f"""
        صنف نية الدكتور التالية من النص المكتوب إلى واحدة فقط من الكلمات المفتاحية التالية:
        - DR_GET_COURSES: إذا كان يسأل عن مقرراته أو مواده أو يقول "عايز أشوف مقرراتي/موادي".
        - DR_GET_SHEETS: إذا ذكر كلمة شيت، محاضرة، ملف، أو PDF.
        - DR_ADD_CONTENT: إذا كان يريد إضافة أو رفع ملف/شيت/محاضرة أو مادة جديدة.
        - DR_DELETE_CONTENT: إذا كان يريد حذف ملف أو مادة كاملة.
        - LOGOUT: إذا صرح برغبته في تسجيل الخروج.
        - GENERAL_QUERY: أي سؤال عام أو تحية أو محادثة عادية.
        النص: "{text}"
        النتيجة (اختر كلمة واحدة فقط مما سبق):
        """
    else:
        prompt = f"""
        صنف نية المستخدم التالية من النص المكتوب إلى واحدة فقط من الكلمات المفتاحية التالية:
        - GET_COURSES: إذا كان يريد معرفة مواده، المقررات، الكورسات، أو جدول المحاضرات.
        - GET_SHEETS: إذا كان يطلب شيت، محاضرة، ملازم، ملفات، أو PDF.
        - SUMMARIZE: إذا كان يريد تلخيص الملف أو الشيت الأخير.
        - LOGIN: إذا صرح برغبته في تسجيل الدخول.
        - LOGOUT: إذا صرح برغبته في تسجيل الخروج.
        - GENERAL_QUERY: أي سؤال عام، استفسار عن الجامعة، تحية، أو محادثة عادية.
        النص: "{text}"
        النتيجة (اختر كلمة واحدة فقط مما سبق):
        """
    try:
        response = await call_gemini_with_retry(
            client.models.generate_content,
            model=INTENT_MODEL_NAME,
            contents=prompt
        )
        return response.text.strip().upper()
    except Exception as e:
        logging.error(f"Intent Detection Error: {e}")
        return "GENERAL_QUERY"

def build_system_instruction(knowledge_text, student_data=None, instructor_data=None, language="ar"):
    if language == "en":
        user_context = ""
        if student_data:
            user_context = f"\nThe student is logged in, name: {student_data.get('name','')}."
        elif instructor_data:
            user_context = f"\nThe user is a logged-in instructor, name: {instructor_data.get('name','')}."
        return f"""
You are a smart assistant for the University of Science and Technology (UST). Reply to students and faculty in English in a friendly, concise way.
Use ONLY this information and never invent anything not present in it:
{knowledge_text}
{user_context}
If the question is about something not in this information, politely say the information is not currently available and suggest contacting university support.
"""
    user_context = ""
    if student_data:
        user_context = f"\nالطالب مسجل دخول، اسمه {student_data.get('name','')}."
    elif instructor_data:
        user_context = f"\nالمستخدم دكتور مسجل دخول، اسمه {instructor_data.get('name','')}."
    return f"""
انت مساعد ذكي لخدمات جامعة العلوم والتقانة. رد على استفسارات الطلاب وأعضاء هيئة التدريس
بأسلوب ودود ومختصر باللهجة السودانية البسيطة.
استخدم المعلومات دي بس للإجابة، وما تخترعش أي معلومة مش موجودة فيها:
{knowledge_text}
{user_context}
لو السؤال عن حاجة مش موجودة في المعلومات دي، قول للمستخدم بأدب إن المعلومة
دي غير متوفرة حالياً وينصح يتواصل مع الدعم الجامعي.
"""

async def generate_answer(user_message, chat_id, instructor_data=None, language="ar"):
    global _fast_cooldown_until, _quota_cooldown_until, _lite_cooldown_until

    # Security shield: reject prompt-injection attempts before any LLM call.
    if prompt_injection_guard(user_message):
        logging.warning(f"[SECURITY] Prompt-injection attempt blocked for chat_id={chat_id}")
        return injection_safe_reply(language)

    _g0 = time.time()
    try:
        knowledge_text = await asyncio.to_thread(get_knowledge_base_text)
    except Exception as e:
        logging.error(f"KB load error: {e}")
        knowledge_text = ""
    logging.info(f"[TIMING] KB load took {time.time()-_g0:.2f}s")
    student_data = None
    if not instructor_data:
        _, student_data = await asyncio.to_thread(get_student_by_chat_id, chat_id)
    system_instruction = build_system_instruction(knowledge_text, student_data, instructor_data, language)

    # 3-tier fallback chain (primary -> secondary -> local TF-IDF engine).
    tiers = (
        (FAST_MODEL, "fast"),
        (MODEL_NAME, "quota"),
        (INTENT_MODEL_NAME, "lite"),
    )
    for model, kind in tiers:
        cooldown = {
            "fast": _fast_cooldown_until,
            "quota": _quota_cooldown_until,
            "lite": _lite_cooldown_until,
        }[kind]
        if time.time() < cooldown:
            continue
        _t = time.time()
        try:
            response = await call_gemini_with_retry(
                client.models.generate_content,
                model=model,
                contents=user_message,
                config=types.GenerateContentConfig(system_instruction=system_instruction),
            )
            logging.info(f"[TIMING] Gemini({model}) generate took {time.time()-_t:.2f}s")
            return response.text
        except Exception as e:
            logging.info(f"[TIMING] Gemini({model}) FAILED after {time.time()-_t:.2f}s")
            logging.error(f"Gemini ({model}) error: {e}")
            if _is_daily_quota_error(e):
                if kind == "fast":
                    _fast_cooldown_until = time.time() + 600
                elif kind == "lite":
                    _lite_cooldown_until = time.time() + 600
                else:
                    _quota_cooldown_until = time.time() + 600
    fallback = await asyncio.to_thread(fallback_kb_answer, user_message, language)
    if fallback:
        return fallback
    return _NO_INFO_REPLY_EN if language == "en" else "معليش، حصل خطأ تقني. جرب تاني بعد شوية."

_AR_STOPWORDS = {
    "شنو", "شو", "ايه", "اي", "ما", "ماهي", "ماهو", "هل", "في", "وين", "كيف", "ليش",
    "علشان", "عشان", "انا", "انتو", "اني", "انت", "عايز", "عايزة", "بغيت", "اريد",
    "ابغى", "بس", "برضو", "لو", "اذا", "ال", "دي", "ده", "ديه", "كده", "كدا", "دا",
    "من", "عن", "مع", "على", "علي", "اللي", "بتاع", "بتاعة", "ديل", "هذه", "هذا",
    "ذلك", "كان", "كانت", "يكون", "يعني", "زاتو", "مش", "مو", "ولا", "محتاج", "تاني",
    "اكتر", "أكتر", "قعد", "قال", "فيني", "تتكلم", "جاوب", "جواب", "عندك", "عندي",
    "كم", "متي", "اين", "هي", "هو", "هم", "هن", "ان", "و", "ل", "كن", "هنا", "بعد",
    "قبل", "كل", "جميع", "بعض", "تقريبا", "دلوقتي", "حاجة", "شئ", "شي", "شيء",
    "المعلومات", "معلومات", "تحب", "تعرف", "اريد", "نريد", "ايهم", "ايش", "منو",
    "مساء", "صباح", "سلام", "السلام", "عليكم", "مرحبا", "اهلا", "هلا", "هلو",
    "طيب", "تمام", "ازيك", "اخبار", "عامل", "نورت", "اعرف", "معرفه", "عند",
    "سمحت", "فضلك", "يا", "شكرا", "ممكن", "يالا", "مرحبين",
}

_GREETING_PAT = re.compile(r"\b(مساء|صباح|مرحبا|اهلا|هلا|هلو|مرحبتين|السلام|هاي|هيلو|hello|hi|hey|good\s?(evening|morning|afternoon|day))\b")

_GENERIC_REPLY = "ممكن توضح سؤالك أكثر؟ تقدر تسألني عن كليات الجامعة، التسجيل، الرسوم، أو الامتحانات."
_GREETING_REPLY = "أهلاً وسهلاً! كيف أقدر أساعدك؟ تقدر تسألني عن كليات الجامعة، التسجيل، الرسوم، أو مواعيد الامتحانات."
_NO_INFO_REPLY = "المعلومة دي غير متوفرة في قاعدة المعرفة حالياً. تواصل مع الدعم الجامعي أو أعد صياغة السؤال."
_GENERIC_REPLY_EN = "Could you clarify your question? You can ask about UST colleges, admission, tuition fees, or exams."
_GREETING_REPLY_EN = "Hello! How can I help you? You can ask me about UST colleges, admission, tuition fees, or exams."
_NO_INFO_REPLY_EN = "That information is not in the knowledge base right now. Please contact university support or rephrase your question."

_EN_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "do", "does", "did",
    "what", "which", "who", "whom", "where", "when", "why", "how", "of", "for", "to", "in",
    "on", "at", "by", "with", "and", "or", "not", "you", "your", "yours", "i", "me", "my",
    "we", "our", "us", "it", "its", "they", "them", "their", "he", "him", "she", "her",
    "can", "could", "will", "would", "should", "shall", "please", "tell", "about",
    "information", "info", "know", "want", "need", "have", "has", "had", "from", "this",
    "that", "these", "those", "there", "here", "all", "any", "some", "one", "two", "just",
}

_AR_CHARS = re.compile(r"[\u0600-\u06FF]")


def detect_text_language(text):
    return "ar" if _AR_CHARS.search(text) else "en"


_EN_LANG_WORDS = {"english", "eng", "en", "انجليزي", "انجليزيه", "انكليزي", "انكليزيه"}
_AR_LANG_WORDS = {"عربي", "عربيه", "arabic"}
_SWITCH_WORDS = {"switch", "change", "set", "speak", "talk", "reply", "بدل", "غيره", "حول", "تحويل", "خليني", "خليها", "كلمني", "رجع", "غير", "حوّل"}


def parse_language_toggle(text):
    t = _norm_ar(text.lower())
    words = set()
    for w in re.findall(r"[a-z]+|[\u0621-\u064a]+", t):
        c = _canon(w)
        if c:
            words.add(c)
    if len(words) > 5:
        return None
    target = "en" if words & _EN_LANG_WORDS else ("ar" if words & _AR_LANG_WORDS else None)
    if target:
        if len(words) <= 1 or (words & (_SWITCH_WORDS | {"لغه", "language", "lang"})):
            return target
        return None
    if words & {"لغه", "language", "lang"}:
        return "show"
    return None


# FIXED: Stored language preference is now checked FIRST before falling back to detection
def get_effective_language(chat_id, text):
    stored = get_chat_language(chat_id)
    if stored in ("ar", "en"):
        return stored
    return detect_text_language(text)


def _norm_ar(text):
    text = text.lower()
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ة", "ه"), ("ى", "ي"), ("ؤ", "و"), ("ئ", "ي")):
        text = text.replace(a, b)
    text = re.sub(r"[\u064b-\u0652\u0640]", "", text)
    text = re.sub(r"\b(تاسست|انشيت|انشات|انشا)\b", "انشا", text)
    return text


_EN_SYN = {
    "registration": "register", "reg": "register",
    "fees": "fee", "tuition": "fee", "fee": "fee",
    "faculties": "faculty", "colleges": "faculty", "college": "faculty", "faculty": "faculty",
    "admissions": "admission", "admission": "admission",
    "established": "founded", "establish": "founded", "founded": "founded",
    "located": "location", "location": "location", "located": "location",
    "courses": "course", "course": "course", "materials": "material",
    "sheets": "sheet", "sheet": "sheet", "lectures": "lecture", "lecture": "lecture",
    "exams": "exam", "exam": "exam", "examination": "exam",
    "scientific": "science", "science": "science", "research": "research",
}


def _canon(word):
    w = word
    if len(w) <= 3:
        return _EN_SYN.get(w, w)
    if w.startswith("و"):
        w = w[1:]
    for p in ("وال", "بال", "كال", "لل", "ال"):
        if w.startswith(p) and len(w) > len(p) + 1:
            w = w[len(p):]
            break
    return _EN_SYN.get(w, w)


def _topic_of(norm_p):
    t = norm_p[len("عربي: "):] if norm_p.startswith("عربي: ") else norm_p
    colon = t.find(": ")
    return t[:colon] if colon != -1 else t[:80]


def _word_set(text):
    return {_canon(w) for w in re.findall(r"[a-z0-9]+|[\u0621-\u064a]+", _norm_ar(text))}


def _tokens(text):
    toks = []
    for w in re.findall(r"[a-z0-9]+|[\u0621-\u064a]+", _norm_ar(text)):
        if len(w) >= 2 and w not in _AR_STOPWORDS and w not in _EN_STOPWORDS:
            c = _canon(w)
            if c and len(c) >= 2 and c not in _AR_STOPWORDS and c not in _EN_STOPWORDS:
                toks.append(c)
    return list(dict.fromkeys(toks))


def fallback_kb_answer(question, language="ar"):
    norm = _norm_ar(question)
    if _GREETING_PAT.search(norm) and len(_tokens(question)) <= 2:
        return _GREETING_REPLY_EN if language == "en" else _GREETING_REPLY
    tokens = _tokens(question)
    if not tokens:
        return _GENERIC_REPLY_EN if language == "en" else _GENERIC_REPLY
    try:
        kb = get_knowledge_base_text()
    except Exception:
        return None
    parts = kb.split("\n- ")
    if not parts or not parts[0].startswith("- "):
        return None
    n = len(parts)
    df = {t: 0 for t in tokens}
    for p in parts:
        ws = _word_set(p)
        for t in tokens:
            if t in ws:
                df[t] += 1
    best_score, best = 0.0, None
    for p in parts:
        norm_p = _norm_ar(p)
        topic = _topic_of(norm_p)
        topic_ws = _word_set(topic)
        content_ws = _word_set(norm_p)
        score = 0.0
        for t in tokens:
            if t in content_ws:
                idf = math.log((n + 1) / (df[t] + 1)) + 1.0
                score += idf * 2.5 if t in topic_ws else idf
        if score > best_score:
            best_score, best = score, best
    if not best or best_score <= 0:
        return _NO_INFO_REPLY_EN if language == "en" else _NO_INFO_REPLY
    matched = [t for t in tokens if t in _word_set(best)]
    if not any(df[t] <= 12 for t in matched):
        return _NO_INFO_REPLY_EN if language == "en" else _NO_INFO_REPLY
    best = _pick_best_section(best, tokens, n, df)
    content = best.split(": ", 1)[1] if ": " in best else best
    content = re.sub(r"\s+", " ", content).strip()
    return content[:1000]


def _pick_best_section(part, tokens, n, df):
    starts = [(m.start(), m.end()) for m in re.finditer(r"(?m)^\d+\s*\.\s+", part)]
    if len(starts) < 2:
        return part
    sections = []
    for i, (s, _e) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(part)
        sections.append(part[s:end])
    best_sub, best_score = part, 0.0
    for sec in sections:
        ws = _word_set(sec)
        score = sum((math.log((n + 1) / (df[t] + 1)) + 1.0) for t in tokens if t in ws)
        if score > best_score:
            best_score, best_sub = score, sec
    return best_sub