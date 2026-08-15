import asyncio
import logging
from google.genai import types
from config import client, MODEL_NAME, INTENT_MODEL_NAME
from database import get_knowledge_base_text, get_student_by_chat_id

async def call_gemini_with_retry(func, *args, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            return await asyncio.to_thread(func, *args, **kwargs)
        except Exception as e:
            is_rate_limit = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
            if is_rate_limit and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 10
                logging.warning(f"تجاوز حدود الاستخدام (429). جاري الانتظار {wait_time} ثانية...")
                await asyncio.sleep(wait_time)
            else:
                raise e

_ADD_KEYWORDS = ("اضيف", "أضيف", "ارفع", "رفع", "اضافة", "إضافة", "زود", "اضيفو", "رفعت")
_DELETE_KEYWORDS = ("احزف", "احذف", "حذف", "امسح", "مسح", "ازيل", "إزالة", "شيل", "امسحي", "احذفو")
_SUMMARIZE_KEYWORDS = ("لخص", "لخّص", "تلخيص", "ملخص", "لخصلي")
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

def build_system_instruction(knowledge_text, student_data=None, instructor_data=None):
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

async def generate_answer(user_message, chat_id, instructor_data=None):
    knowledge_text = await asyncio.to_thread(get_knowledge_base_text)
    student_data = None
    if not instructor_data:
        _, student_data = await asyncio.to_thread(get_student_by_chat_id, chat_id)
    system_instruction = build_system_instruction(knowledge_text, student_data, instructor_data)
    try:
        response = await call_gemini_with_retry(
            client.models.generate_content,
            model=MODEL_NAME,
            contents=user_message,
            config=types.GenerateContentConfig(system_instruction=system_instruction),
        )
        return response.text
    except Exception as e:
        logging.error(f"Gemini error: {e}")
        return "معليش، حصل خطأ تقني. جرب تاني بعد شوية."