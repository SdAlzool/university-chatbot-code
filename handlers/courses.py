"""Course, sheet, and summarisation handlers."""
import asyncio
import logging
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import db, client, MODEL_NAME
from database import get_instructor_by_chat_id, get_student_by_chat_id
from gemini_services import call_gemini_with_retry
from github_utils import get_file_download_url_by_path, github_headers, list_course_files_with_sha
from utils import extract_pdf_text

async def _all_courses():
    docs = await asyncio.to_thread(lambda: list(db.collection("courses").stream()))
    courses = {doc.id: doc.to_dict() for doc in docs}
    instructors = await asyncio.to_thread(lambda: list(db.collection("instructors").stream()))
    for instructor in instructors:
        for course in instructor.to_dict().get("courses", []):
            if course.get("folder"):
                courses.setdefault(course["folder"], course)
    return list(courses.values())

async def show_courses(update, context):
    if not await _can_access_materials(update):
        await update.message.reply_text("هذه الخدمة للطلاب المسجلين أو الأدمن فقط. اكتب /login.")
        return
    courses = await _all_courses()
    await update.message.reply_text("المقررات المتاحة:\n" + ("\n".join(f"- {c.get('name', '')}" for c in courses) or "لا توجد مقررات."))

async def _can_access_materials(update):
    from .admin import user_is_admin
    _, student = await asyncio.to_thread(get_student_by_chat_id, update.effective_chat.id)
    if student:
        return True
    _, instructor = await asyncio.to_thread(get_instructor_by_chat_id, update.effective_chat.id)
    if instructor:
        return True
    return await user_is_admin(update)

async def _send_file(target, file):
    try:
        url = await asyncio.to_thread(get_file_download_url_by_path, file["path"])
        if not url:
            await target.reply_text("تعذر العثور على الملف في المستودع.")
            return
        response = await asyncio.to_thread(requests.get, url, headers=github_headers(), timeout=60)
        if response.status_code != 200:
            await target.reply_text("تعذر تحميل الملف من المستودع.")
            return
        await target.reply_document(response.content, filename=file["name"])
    except Exception:
        logging.exception("File download failed")
        await target.reply_text("تعذر تحميل الملف الآن.")

async def _send_sheet(target, context, folder):
    files = await asyncio.to_thread(list_course_files_with_sha, folder)
    if not files:
        await target.reply_text("لا توجد ملفات لهذه المادة.")
        return
    if len(files) == 1:
        context.user_data["last_file"] = files[0]
        await _send_file(target, files[0])
        return
    context.user_data["pending_files"] = files
    buttons = [[InlineKeyboardButton(file["name"], callback_data=f"filesel:{i}")] for i, file in enumerate(files)]
    await target.reply_text("اختر الملف:", reply_markup=InlineKeyboardMarkup(buttons))

async def get_sheet(update, context):
    if not await _can_access_materials(update):
        await update.message.reply_text("هذه الخدمة للطلاب المسجلين أو الأدمن فقط. اكتب /login.")
        return
    if context.args:
        await _send_sheet(update.message, context, context.args[0])
        return
    courses = await _all_courses()
    buttons = [[InlineKeyboardButton(c.get("name", "مادة"), callback_data=f"sheet:{c.get('folder', '')}")] for c in courses]
    await update.message.reply_text("اختر المادة:", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_sheet_button(update, context):
    query = update.callback_query
    await query.answer()
    await _send_sheet(query.message, context, query.data.removeprefix("sheet:"))

async def handle_file_button(update, context):
    query = update.callback_query
    await query.answer()
    files = context.user_data.get("pending_files", [])
    try:
        file = files[int(query.data.removeprefix("filesel:"))]
    except (ValueError, IndexError):
        await query.message.reply_text("انتهت صلاحية القائمة. اطلب الملفات مرة أخرى.")
        return
    context.user_data["last_file"] = file
    await _send_file(query.message, file)

async def summarize_last_file(update, context):
    file = context.user_data.get("last_file")
    if not await _can_access_materials(update) or not file:
        await update.message.reply_text("سجل دخولك كطالب (أو استخدم حساب أدمن) ثم اطلب الملف أولاً.")
        return
    try:
        url = await asyncio.to_thread(get_file_download_url_by_path, file["path"])
        response = await asyncio.to_thread(requests.get, url, headers=github_headers(), timeout=60)
        text = await asyncio.to_thread(extract_pdf_text, response.content)
        if not text.strip():
            await update.message.reply_text("هذا الملف ليس PDF أو لا يمكن استخراج نص منه للتلخيص.")
            return
        result = await call_gemini_with_retry(
            client.models.generate_content,
            model=MODEL_NAME,
            contents=(
                "لخص النص التالي في نقاط واضحة ومرتبة. "
                "مهم جداً: اكتشف لغة النص الأصلي واكتب الملخص بنفس تلك اللغة تماماً "
                "(لو النص إنجليزي اكتب الملخص بالإنجليزي، ولو عربي اكتب الملخص بالعربي).\n\n"
                f"النص:\n{text[:6000]}"
            ),
        )
        await update.message.reply_text(f"ملخص {file['name']}:\n\n{result.text}")
    except Exception:
        logging.exception("Summarisation failed")
        await update.message.reply_text("تعذر تلخيص الملف الآن.")