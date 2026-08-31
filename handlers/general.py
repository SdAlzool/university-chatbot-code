"""General chat, welcome, and voice handlers."""
import asyncio
import logging
import re
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from google.genai import types
from config import client, MODEL_NAME
from database import get_instructor_by_chat_id, get_student_by_chat_id, set_chat_language
from gemini_services import (
    call_gemini_with_retry, detect_user_intent, generate_answer,
    parse_language_toggle, get_effective_language,
)
from .admin import (
    add_admin_by_id, list_admins, list_all_people, list_instructors,
    list_students, remove_admin_by_id, user_is_admin,
    add_person_by_text, edit_person_by_text, delete_person_by_text,
)

ADD_WORDS = ("اضف", "أضف", "إضافة", "اضيف", "أضيف", "تضيف", "زود", "أدخل", "ادخل")
DEL_WORDS = ("احذف", "حذف", "شيل", "اشيل", "أشيل", "ازل", "أزل", "مسح", "امسح", "أمسح")
EDIT_WORDS = ("عدل", "عدّل", "تعديل", "حدّث", "حدث", "اعدل", "أعدل", "تعدل", "تحدث")
LIST_WORDS = ("اعرض", "أعرض", "عرض", "وريني", "أرني", "اوريني", "أوريني",
              "اشوف", "أشوف", "شوف", "عايز", "عاوز", "عايزة", "عاوزه",
              "أبي", "ابي", "ابغى", "أبغى", "بغيت", "نبغي", "نبيه")
ADMIN_WORDS = ("ادمن", "أدمن", "المدير", "مدير", "مشرف", "المشرف", "مشرفين", "المشرفين")
STUDENT_WORDS = ("طالب", "طلاب", "الطالب", "الطلاب", "الطلبة")
INSTRUCTOR_WORDS = ("دكتور", "دكاترة", "الدكتور", "أستاذ", "أستاذة", "استاذ", "استاذة", "أساتذة", "الأساتذة", "اساتذة", "الاساتذة")
PEOPLE_WORDS = ("الناس", "الأشخاص", "الاشخاص", "الجميع", "الكل", "شخصيات", "الشخصيات", "المسجلين")
ACTION_ROLE_WORDS = ADD_WORDS + DEL_WORDS + EDIT_WORDS + STUDENT_WORDS + INSTRUCTOR_WORDS + PEOPLE_WORDS


def _extract_name(text: str, email: str, person_id: str) -> str:
    words = [w for w in text.split() if w not in (email, person_id)]
    while words and words[0] in ACTION_ROLE_WORDS:
        words.pop(0)
    return " ".join(words).strip() or "بدون اسم"


async def _handle_admin_command(update, context, text):
    normalized = text.lower()
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    id_match = re.search(r"\b\d{5,}\b", normalized)
    admin_id = int(id_match.group()) if id_match else None

    has_add = any(w in normalized for w in ADD_WORDS)
    has_del = any(w in normalized for w in DEL_WORDS)
    has_edit = any(w in normalized for w in EDIT_WORDS)
    asks_list = any(w in normalized for w in LIST_WORDS)
    asks_admins = any(w in normalized for w in ADMIN_WORDS)
    asks_students = any(w in normalized for w in STUDENT_WORDS)
    asks_instructors = any(w in normalized for w in INSTRUCTOR_WORDS)
    asks_people = any(w in normalized for w in PEOPLE_WORDS)

    if asks_admins:
        if admin_id and has_add:
            await add_admin_by_id(update, admin_id)
            return True
        if admin_id and has_del:
            await remove_admin_by_id(update, admin_id)
            return True
        if asks_list:
            await list_admins(update, context)
            return True

    if (asks_students and asks_instructors) or asks_people:
        await list_all_people(update, context)
        return True

    if asks_students:
        collection_name, label = "students", "طالب"
    elif asks_instructors:
        collection_name, label = "instructors", "أستاذ"
    else:
        return False

    if has_edit:
        if admin_id:
            await edit_person_by_text(update, collection_name, label, str(admin_id), text)
        else:
            await update.effective_message.reply_text(
                f"الصيغة: عدّل {label} <المعرف> <اسم الحقل> <القيمة الجديدة>\n"
                f"مثال: عدّل {label} 123456 name الاسم الجديد\n"
                f"الحقول المسموحة: name, email"
            )
        return True
    if has_add:
        if admin_id and email_match:
            name = _extract_name(text, email_match.group(), str(admin_id))
            await add_person_by_text(update, collection_name, label, str(admin_id), email_match.group(), name)
        else:
            await update.effective_message.reply_text(
                f"الصيغة: أضف {label} <المعرف> <البريد الإلكتروني> <الاسم>\n"
                f"مثال: أضف {label} 123456789 name@uni.edu.sd الاسم الكامل\n\n"
                f"ملاحظة: المعرف رقمي (5 أرقام على الأقل)"
            )
        return True
    if has_del:
        if admin_id:
            await delete_person_by_text(update, collection_name, label, str(admin_id))
        else:
            await update.effective_message.reply_text(
                f"الصيغة: احذف {label} <المعرف>\n"
                f"مثال: احذف {label} 123456789"
            )
        return True
    if asks_list:
        if collection_name == "students":
            await list_students(update, context)
        else:
            await list_instructors(update, context)
        return True
    return False


HELP_TEXT = (
    "🎓 <b>بوت خدمات الجامعة</b>\n"
    "أنا هنا لمساعدتك في الآتي:\n\n"
    "💬 <b>أسئلة عامة</b>: اسألني أي سؤال عن الجامعة أو المقررات.\n"
    "📚 <b>المقررات والشيتات</b>: اعرض المقررات واطلب الملفات (للمسجلين).\n"
    "📄 <b>رفع ملف</b>: أرسل لي ملف PDF/Word/صورة وسألخصه أو أترجمه.\n"
    "🎙️ <b>رسائل صوتية</b>: أرسل صوتاً وسأحوّله إلى نص وأجيبك.\n\n"
    "🔑 <b>تسجيل الدخول</b>: لفتح المقررات والشيتات اكتب /login\n\n"
    "─── أوامر الأدمن ───\n"
    "أضف طالب <المعرف> <البريد> <الاسم>\n"
    "مثال: أضف طالب 123456789 ali@uni.edu.sd علي أحمد\n\n"
    "أضف دكتور <المعرف> <البريد> <الاسم>\n"
    "مثال: أضف دكتور 987654321 omar@uni.edu.sd عمر محمد\n\n"
    "احذف طالب <المعرف> | احذف دكتور <المعرف>\n"
    "مثال: احذف طالب 123456789\n\n"
    "عرض الطلاب | عرض الأساتذة | عرض الأدمن\n\n"
    "اكتب سؤالك ببساطة أو أرسل ملفاً للبدء 🚀"
)


async def start(update, context):
    chat_id = update.effective_chat.id
    _, student = await asyncio.to_thread(get_student_by_chat_id, chat_id)
    _, instructor = await asyncio.to_thread(get_instructor_by_chat_id, chat_id)
    if student or instructor:
        await update.message.reply_text("أهلاً بك مجدداً. كيف أساعدك؟ اكتب /help لعرض الخدمات.")
        return
    keyboard = [[InlineKeyboardButton("تسجيل الدخول", callback_data="btn_start_login"),
                 InlineKeyboardButton("المتابعة كزائر", callback_data="btn_guest_mode")]]
    await update.message.reply_text(HELP_TEXT, reply_markup=InlineKeyboardMarkup(keyboard))


async def help_command(update, context):
    await update.message.reply_text(HELP_TEXT)


async def handle_welcome_buttons(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "btn_start_login":
        await query.edit_message_text("اكتب /login لبدء تسجيل الدخول.")
    else:
        await query.edit_message_text(
            "أهلاً بك كزائر 👋 يمكنك الآن:\n"
            "• طرح أي سؤال عن الجامعة.\n"
            "• إرسال ملف وسألخصه أو أترجمه.\n"
            "• إرسال رسالة صوتية وسأحوّلها لنص.\n\n"
            "للدخول إلى المقررات والشيتات سجّل الدخول من /login"
        )


async def handle_message(update, context):
    from .auth import logout
    from .courses import get_sheet, show_courses, summarize_last_file
    t0 = time.time()
    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    if text.lower() in ("مساعدة", "help", "المساعدة", "الخدمات", "menu", "قائمة"):
        await update.message.reply_text(HELP_TEXT)
        return
    lang_cmd = parse_language_toggle(text)
    if lang_cmd:
        if lang_cmd == "show":
            await update.message.reply_text("اختر اللغة بكتابة English أو عربي\nChoose a language: type 'English' or 'عربي'")
        elif lang_cmd == "en":
            set_chat_language(str(chat_id), "en")
            await update.message.reply_text("Done! I will now reply in English. Type 'عربي' to switch back.")
        else:
            set_chat_language(str(chat_id), "ar")
            await update.message.reply_text("تم! الآن سأرد بالعربية. اكتب English للتبديل.")
        return
    if await user_is_admin(update):
        if await _handle_admin_command(update, context, text):
            logging.info(f"[TIMING] admin-command path finished in {time.time()-t0:.2f}s")
            return
    _, instructor = await asyncio.to_thread(get_instructor_by_chat_id, chat_id)
    intent = await detect_user_intent(text, is_instructor=bool(instructor))
    logging.info(f"[TIMING] intent-detection took {time.time()-t0:.2f}s")
    if intent in ("GET_COURSES", "DR_GET_COURSES"):
        await show_courses(update, context)
        logging.info(f"[TIMING] GET_COURSES total {time.time()-t0:.2f}s")
    elif intent in ("GET_SHEETS", "DR_GET_SHEETS"):
        await get_sheet(update, context)
        logging.info(f"[TIMING] GET_SHEETS total {time.time()-t0:.2f}s")
    elif intent == "SUMMARIZE":
        await summarize_last_file(update, context)
        logging.info(f"[TIMING] SUMMARIZE total {time.time()-t0:.2f}s")
    elif intent == "LOGOUT":
        await logout(update, context)
        logging.info(f"[TIMING] LOGOUT total {time.time()-t0:.2f}s")
    elif intent == "LOGIN":
        await update.message.reply_text("اكتب /login لبدء تسجيل الدخول.")
    elif intent == "DR_ADD_CONTENT":
        await update.message.reply_text("لإضافة مادة أو رفع ملف استخدم الأمر /addcontent")
    elif intent == "DR_DELETE_CONTENT":
        await update.message.reply_text("لحذف ملف أو مادة استخدم الأمر /deletecontent")
    else:
        language = get_effective_language(str(chat_id), text)
        await update.message.reply_text(await generate_answer(text, chat_id, instructor_data=instructor, language=language))
        logging.info(f"[TIMING] FULL reply (intent {time.time()-t0:.2f}s total) — note this includes intent-detection ({time.time()-(t0+0)}s since start)")


async def handle_voice(update, context):
    await update.message.reply_text("جاري معالجة الرسالة الصوتية…")
    try:
        voice = await context.bot.get_file(update.message.voice.file_id)
        audio = bytes(await voice.download_as_bytearray())
        part = types.Part.from_bytes(data=audio, mime_type="audio/ogg")
        response = await call_gemini_with_retry(
            client.models.generate_content,
            model=MODEL_NAME,
            contents=["استخرج النص المنطوق فقط.", part],
        )
        text = response.text.strip()
        if text:
            language = get_effective_language(str(update.effective_chat.id), text)
            await update.message.reply_text(await generate_answer(text, update.effective_chat.id, language=language))
    except Exception:
        logging.exception("Voice processing failed")
        await update.message.reply_text("تعذرت معالجة الرسالة الصوتية.")
