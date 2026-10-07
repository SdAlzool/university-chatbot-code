"""تيليجرام: المواد، تسجيل الدخول، إدارة المحتوى، الملفات، والرسائل العامة."""

import asyncio
import logging
import re
import secrets
import time

import requests
from firebase_admin import firestore
from google.genai import types
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import MODEL_NAME
from services.email_service import send_otp_email
from services.firebase_db import (
    db,
    get_instructor_by_chat_id,
    get_student_by_chat_id,
    set_chat_language,
)
from services.gemini_service import (
    call_gemini_with_retry,
    client,
    detect_user_intent,
    generate_answer,
    get_effective_language,
    parse_language_toggle,
)
from services.github_tools import (
    get_file_download_url_by_path,
    github_delete_file,
    github_headers,
    github_upload_file,
    list_course_files_with_sha,
    slugify_course_name,
)
from telegram_bot.admin_panel import (
    add_admin_by_id,
    add_person_by_text,
    delete_person_by_text,
    edit_person_by_text,
    list_admins,
    list_all_people,
    list_instructors,
    list_students,
    remove_admin_by_id,
    user_is_admin,
)
from utils.formatting import help_message
from utils.pdf_utils import extract_pdf_text, text_to_pdf_bytes


# ============================================================
# من الملف الأصلي: handlers/courses.py
# ============================================================


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

async def show_my_courses(update, context):
    if not await _can_access_materials(update):
        await update.message.reply_text("هذه الخدمة للطلاب المسجلين أو الأدمن فقط. اكتب /login.")
        return
    courses, student_id = await _available_courses_for_user(update)
    if not courses:
        await update.message.reply_text("لا توجد مواد مخصصة لك. تواصل مع الأدمن.")
        return
    buttons = []
    for c in courses:
        name = c.get("name", "مادة")
        folder = c.get("folder", "")
        buttons.append([InlineKeyboardButton(f"📚 {name}", callback_data=f"mycourse:{folder}")])
    from utils.formatting import my_courses_list
    await update.message.reply_text(
        my_courses_list(courses),
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

async def handle_my_course_button(update, context):
    query = update.callback_query
    await query.answer()
    folder = query.data.removeprefix("mycourse:")
    context.user_data["selected_course"] = folder
    courses = await _all_courses()
    course_name = "المادة"
    for c in courses:
        if c.get("folder") == folder:
            course_name = c.get("name", "المادة")
            break
    buttons = [
        [InlineKeyboardButton("📋 المقرر", callback_data=f"courseopt:syllabus:{folder}")],
        [InlineKeyboardButton("📖 المراجع", callback_data=f"courseopt:refs:{folder}")],
        [InlineKeyboardButton("📝 الامتحانات", callback_data=f"courseopt:exams:{folder}")],
        [InlineKeyboardButton("📄 الشيتات", callback_data=f"courseopt:sheets:{folder}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="backmycourses")],
    ]
    await query.edit_message_text(
        f"📚 **{course_name}**\n\nاختر:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

async def handle_course_option(update, context):
    query = update.callback_query
    await query.answer()
    parts = query.data.removeprefix("courseopt:").split(":", 1)
    if len(parts) != 2:
        return
    option, folder = parts
    if not await _can_access_folder(update, folder):
        await query.message.reply_text("ليس لديك صلاحية الوصول إلى هذا المقرر.")
        return
    files = await asyncio.to_thread(list_course_files_with_sha, folder)
    if not files:
        await query.message.reply_text("لا توجد ملفات لهذه المادة.")
        return
    filtered_files = []
    for f in files:
        name_lower = f["name"].lower()
        if option == "syllabus" and any(kw in name_lower for kw in ["مقرر", "syllabus", "curriculum"]):
            filtered_files.append(f)
        elif option == "refs" and any(kw in name_lower for kw in ["مرجع", "ref", "reference", "book"]):
            filtered_files.append(f)
        elif option == "exams" and any(kw in name_lower for kw in ["امتحان", "exam", "quiz", "final", "midterm"]):
            filtered_files.append(f)
        elif option == "sheets":
            filtered_files = files
            break
    if not filtered_files:
        await query.message.reply_text("لا توجد ملفات لهذا القسم.")
        return
    if len(filtered_files) == 1:
        context.user_data["last_file"] = filtered_files[0]
        await _send_file_with_options(query.message, context, filtered_files[0], folder)
        return
    context.user_data["pending_files"] = filtered_files
    context.user_data["current_folder"] = folder
    buttons = [[InlineKeyboardButton(f["name"], callback_data=f"filesel:{i}")] for i, f in enumerate(filtered_files)]
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"mycourse:{folder}")])
    await query.message.reply_text("اختر الملف:", reply_markup=InlineKeyboardMarkup(buttons))

async def _send_file_with_options(target, context, file, folder):
    context.user_data["last_file"] = file
    context.user_data["current_folder"] = folder
    buttons = [
        [InlineKeyboardButton("⬇️ تنزيل", callback_data="coursefile:download")],
        [InlineKeyboardButton("🌐 ترجمة", callback_data="coursefile:translate")],
        [InlineKeyboardButton("📝 تلخيص", callback_data="coursefile:summarize")],
        [InlineKeyboardButton("🔙 رجوع", callback_data=f"mycourse:{folder}")],
    ]
    await target.reply_text(
        f"📄 **{file['name']}**\n\nاختر:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown",
    )

async def handle_course_file_action(update, context):
    query = update.callback_query
    await query.answer()
    action = query.data.removeprefix("coursefile:")
    file = context.user_data.get("last_file")
    folder = context.user_data.get("current_folder", "")
    if action not in {"download", "translate", "summarize"} or not file:
        await query.message.reply_text("انتهت صلاحية الملف. اطلبه مرة أخرى.")
        return
    if not await _can_access_folder(update, folder):
        await query.message.reply_text("ليس لديك صلاحية الوصول إلى هذا الملف.")
        return
    if action == "download":
        await _send_file(query.message, file)
    elif action == "translate":
        await _translate_file(query.message, file)
    else:
        await _summarize_file(query.message, file)

async def _translate_file(target, file):
    try:
        url = await asyncio.to_thread(get_file_download_url_by_path, file["path"])
        response = await asyncio.to_thread(requests.get, url, headers=github_headers(), timeout=60)
        text = await asyncio.to_thread(extract_pdf_text, response.content)
        if not text.strip():
            await target.reply_text("هذا الملف ليس PDF أو لا يمكن استخراج نص منه للترجمة.")
            return
        result = await call_gemini_with_retry(
            client.models.generate_content,
            model=MODEL_NAME,
            contents=(
                "ترجم النص التالي إلى العربية إذا كان بالإنجليزي، أو إلى الإنجليزي إذا كان بالعربي. "
                "اكتب الترجمة بشكل واضح ومرتب.\n\n"
                f"النص:\n{text[:6000]}"
            ),
        )
        await target.reply_text(f"ترجمة {file['name']}:\n\n{result.text[:4000]}")
    except Exception:
        logging.exception("Translation failed")
        await target.reply_text("تعذر ترجمة الملف الآن.")

async def _summarize_file(target, file):
    try:
        url = await asyncio.to_thread(get_file_download_url_by_path, file["path"])
        response = await asyncio.to_thread(requests.get, url, headers=github_headers(), timeout=60)
        text = await asyncio.to_thread(extract_pdf_text, response.content)
        if not text.strip():
            await target.reply_text("هذا الملف ليس PDF أو لا يمكن استخراج نص منه للتلخيص.")
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
        await target.reply_text(f"ملخص {file['name']}:\n\n{result.text[:4000]}")
    except Exception:
        logging.exception("Summarisation failed")
        await target.reply_text("تعذر تلخيص الملف الآن.")

async def handle_back_my_courses(update, context):
    query = update.callback_query
    await query.answer()
    courses, _ = await _available_courses_for_user(update)
    if not courses:
        await query.edit_message_text("لا توجد مواد مخصصة لك.")
        return
    buttons = []
    for c in courses:
        name = c.get("name", "مادة")
        folder = c.get("folder", "")
        buttons.append([InlineKeyboardButton(f"📚 {name}", callback_data=f"mycourse:{folder}")])
    await query.edit_message_text(
        "📚 **موادّي**\n\nاختر المادة لعرض التفاصيل:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

async def _can_access_materials(update):
    from telegram_bot.admin_panel import user_is_admin
    _, student = await asyncio.to_thread(get_student_by_chat_id, update.effective_chat.id)
    if student:
        return True
    _, instructor = await asyncio.to_thread(get_instructor_by_chat_id, update.effective_chat.id)
    if instructor:
        return True
    return await user_is_admin(update)

async def _available_courses_for_user(update):
    student_id, student = await asyncio.to_thread(get_student_by_chat_id, update.effective_chat.id)
    if student:
        assigned_courses = student.get("courses") or []
        if not assigned_courses:
            return [], student_id
        all_courses = await _all_courses()
        student_courses = [c for c in all_courses if c.get("folder") in assigned_courses]
        return student_courses, student_id
    instructor_id, instructor = await asyncio.to_thread(get_instructor_by_chat_id, update.effective_chat.id)
    if instructor:
        return instructor.get("courses") or [], instructor_id
    return [], None

async def _can_access_folder(update, folder):
    if await user_is_admin(update):
        return True
    courses, _ = await _available_courses_for_user(update)
    return any(str(course.get("folder", "")) == folder for course in courses)

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
    context.user_data["current_folder"] = folder
    context.user_data["pending_files"] = files
    buttons = [[InlineKeyboardButton(file["name"], callback_data=f"filesel:{i}")] for i, file in enumerate(files)]
    await target.reply_text("اختر الملف:", reply_markup=InlineKeyboardMarkup(buttons))

async def get_sheet(update, context):
    if not await _can_access_materials(update):
        await update.message.reply_text("هذه الخدمة للطلاب المسجلين أو الأدمن فقط. اكتب /login.")
        return
    if context.args:
        folder = context.args[0]
        if not await _can_access_folder(update, folder):
            await update.message.reply_text("ليس لديك صلاحية الوصول إلى هذا المقرر.")
            return
        await _send_sheet(update.message, context, folder)
        return
    courses = await _all_courses()
    buttons = [[InlineKeyboardButton(c.get("name", "مادة"), callback_data=f"sheet:{c.get('folder', '')}")] for c in courses]
    await update.message.reply_text("اختر المادة:", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_sheet_button(update, context):
    query = update.callback_query
    await query.answer()
    folder = query.data.removeprefix("sheet:")
    if not await _can_access_folder(update, folder):
        await query.message.reply_text("ليس لديك صلاحية الوصول لهذه المادة.")
        return
    await _send_sheet(query.message, context, folder)

async def handle_file_button(update, context):
    query = update.callback_query
    await query.answer()
    files = context.user_data.get("pending_files", [])
    folder = context.user_data.get("current_folder", "")
    try:
        file = files[int(query.data.removeprefix("filesel:"))]
    except (ValueError, IndexError):
        await query.message.reply_text("انتهت صلاحية القائمة. اطلب الملفات مرة أخرى.")
        return
    if not await _can_access_folder(update, file.get("path", "").split("/", 1)[0]):
        await query.message.reply_text("ليس لديك صلاحية الوصول لهذا الملف.")
        return
    context.user_data["last_file"] = file
    await _send_file_with_options(query.message, context, file, folder)

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


# ============================================================
# من الملف الأصلي: handlers/auth.py
# ============================================================


ASK_ID, ASK_OTP = range(2)
_pending_otp = {}
_last_otp_sent = {}
OTP_RESEND_COOLDOWN_SECONDS = 60

async def login_start(update, context):
    target = update.callback_query.message if update.callback_query else update.message
    chat_id = update.effective_chat.id
    _, student = await asyncio.to_thread(get_student_by_chat_id, chat_id)
    _, instructor = await asyncio.to_thread(get_instructor_by_chat_id, chat_id)
    if student or instructor:
        await target.reply_text("أنت مسجل دخول بالفعل.")
        return ConversationHandler.END
    await target.reply_text("اكتب رقمك الجامعي أو معرف الدكتور:")
    return ASK_ID

async def login_ask_id(update, context):
    user_id = update.message.text.strip()
    chat_id = update.effective_chat.id
    if time.time() - _last_otp_sent.get(chat_id, 0) < OTP_RESEND_COOLDOWN_SECONDS:
        await update.message.reply_text("انتظر دقيقة قبل طلب رمز جديد.")
        return ConversationHandler.END
    for collection, role in (("students", "student"), ("instructors", "instructor")):
        document = await asyncio.to_thread(db.collection(collection).document(user_id).get)
        if document.exists:
            data = document.to_dict()
            break
    else:
        await update.message.reply_text("الرقم غير موجود.")
        return ConversationHandler.END
    if not data.get("email"):
        await update.message.reply_text("لا يوجد بريد إلكتروني لهذا الحساب.")
        return ConversationHandler.END
    code = str(secrets.randbelow(900000) + 100000)
    try:
        logging.info("Sending OTP to %s for user %s", data["email"], user_id)
        await asyncio.to_thread(send_otp_email, data["email"], code)
        logging.info("OTP sent successfully to %s", data["email"])
    except Exception as e:
        logging.exception("Unable to send OTP email to %s: %s", data["email"], e)
        await update.message.reply_text(
            f"تعذر إرسال رمز التحقق إلى البريد الإلكتروني.\n"
            f"الخطأ: {str(e)[:200]}"
        )
        return ConversationHandler.END
    _last_otp_sent[chat_id] = time.time()
    _pending_otp[chat_id] = {"code": code, "user_id": user_id, "role": role, "expires": time.time() + 300, "attempts": 0}
    await update.message.reply_text("تم إرسال رمز التحقق إلى بريدك الإلكتروني. اكتبه هنا خلال 5 دقائق:")
    return ASK_OTP

async def login_ask_otp(update, context):
    chat_id = update.effective_chat.id
    pending = _pending_otp.get(chat_id)
    if not pending or time.time() > pending["expires"]:
        _pending_otp.pop(chat_id, None)
        await update.message.reply_text("انتهت جلسة التحقق. ابدأ بـ /login.")
        return ConversationHandler.END
    if update.message.text.strip() != pending["code"]:
        pending["attempts"] = pending.get("attempts", 0) + 1
        if pending["attempts"] >= 5:
            _pending_otp.pop(chat_id, None)
            await update.message.reply_text("تم إلغاء التحقق بعد محاولات كثيرة. ابدأ بـ /login.")
            return ConversationHandler.END
        await update.message.reply_text("الرمز غير صحيح، حاول مرة أخرى:")
        return ASK_OTP
    collection = "students" if pending["role"] == "student" else "instructors"
    await asyncio.to_thread(db.collection(collection).document(pending["user_id"]).update, {"chat_id": str(chat_id), "last_active": time.time()})
    _pending_otp.pop(chat_id, None)
    
    # Show appropriate menu based on role
    if pending["role"] == "student":
        await _show_student_welcome(update.message)
    else:
        await _show_instructor_welcome(update.message)
    
    return ConversationHandler.END


async def _show_student_welcome(message):
    """Show welcome menu for students after login."""
    from utils.formatting import student_welcome_menu
    buttons = [
        [InlineKeyboardButton("❓ سؤال عن الجامعة", callback_data="student:university")],
        [InlineKeyboardButton("📚 سؤال عن مادة", callback_data="student:course_question")],
        [InlineKeyboardButton("📖 موادّي", callback_data="student:mycourses")],
    ]
    await message.reply_text(
        student_welcome_menu(),
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def _show_instructor_welcome(message):
    """Show welcome menu for instructors after login."""
    from utils.formatting import instructor_welcome_menu
    buttons = [
        [InlineKeyboardButton("📚 عرض المواد", callback_data="instructor:view_courses")],
        [InlineKeyboardButton("➕ إضافة مادة", callback_data="instructor:add_course")],
        [InlineKeyboardButton("🗑️ حذف مادة", callback_data="instructor:delete_course")],
    ]
    await message.reply_text(
        instructor_welcome_menu(),
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def handle_student_callback(update, context):
    """Handle student menu callbacks."""
    query = update.callback_query
    await query.answer()
    
    action = query.data.removeprefix("student:")
    
    if action == "university":
        await query.message.reply_text("اكتب سؤالك عن الجامعة:")
        context.user_data["question_type"] = "university"
    elif action == "course_question":
        # عرض المواد المتاحة لاختيار واحدة قبل كتابة السؤال
        courses, _ = await _available_courses_for_user(update)
        if not courses:
            await query.message.reply_text("لا توجد مواد مخصصة لك.")
            return
        buttons = [[InlineKeyboardButton(c.get("name", "مادة"), callback_data=f"askcourse:{c.get('folder', '')}")] for c in courses]
        await query.message.reply_text(
            "اختر المادة لسؤالك:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif action == "mycourses":
        await show_my_courses(update, context)


async def handle_ask_course(update, context):
    """Handle when student selects a course to ask about."""
    query = update.callback_query
    await query.answer()
    folder = query.data.removeprefix("askcourse:")
    
    context.user_data["question_type"] = "course"
    context.user_data["question_course"] = folder
    
    await query.message.reply_text("اكتب سؤالك عن هذه المادة:")


async def handle_instructor_callback(update, context):
    """Handle instructor menu callbacks."""
    query = update.callback_query
    await query.answer()
    
    action = query.data.removeprefix("instructor:")
    
    if action == "view_courses":
        courses = await _all_courses()
        if not courses:
            await query.message.reply_text("لا توجد مواد مسجلة.")
            return
        lines = ["📚 **المواد المتاحة:**\n"]
        for c in courses:
            lines.append(f"• {c.get('name', 'مادة')}")
        await query.message.reply_text("\n".join(lines), parse_mode="Markdown")
    elif action == "add_course":
        await query.message.reply_text("اكتب اسم المادة الجديدة:")
        context.user_data["instructor_action"] = "add_course"
    elif action == "delete_course":
        # عرض المواد المتاحة للحذف
        courses = await _all_courses()
        if not courses:
            await query.message.reply_text("لا توجد مواد لحذفها.")
            return
        buttons = [[InlineKeyboardButton(c.get("name", "مادة"), callback_data=f"delcourse:{c.get('folder', '')}")] for c in courses]
        await query.message.reply_text(
            "اختر المادة لحذفها:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


async def login_cancel(update, context):
    _pending_otp.pop(update.effective_chat.id, None)
    await update.message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END

async def logout(update, context):
    """Clear the active Telegram session for a student or instructor."""
    chat_id = update.effective_chat.id
    logged_out = False

    for collection, lookup in (
        ("students", get_student_by_chat_id),
        ("instructors", get_instructor_by_chat_id),
    ):
        document_id, _ = await asyncio.to_thread(lookup, chat_id)
        if document_id:
            await asyncio.to_thread(
                db.collection(collection).document(document_id).update,
                {"chat_id": None, "last_active": None},
            )
            logged_out = True

    if logged_out:
        await update.effective_message.reply_text("Logged out successfully.")
    else:
        await update.effective_message.reply_text("You are not logged in.")


login_conv = ConversationHandler(
    entry_points=[
        CommandHandler("login", login_start),
        CallbackQueryHandler(login_start, pattern="^btn_start_login$"),
    ],
    states={
        ASK_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_ask_id)],
        ASK_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_ask_otp)],
    },
    fallbacks=[CommandHandler("cancel", login_cancel)],
    per_message=False,
)


# ============================================================
# من الملف الأصلي: handlers/content_mgmt.py
# ============================================================


ADD_MENU, ADD_SELECT_COURSE, ADD_NEW_NAME, ADD_NEW_CONFIRM, ADD_WAIT_FILE = range(5)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

async def _instructor_context(update):
    instructor_id, instructor = await asyncio.to_thread(
        get_instructor_by_chat_id, update.effective_chat.id
    )
    return instructor_id, instructor


async def _available_courses(update):
    instructor_id, instructor = await _instructor_context(update)
    if instructor_id:
        courses = instructor.get("courses") or []
        return courses, instructor_id
    if await user_is_admin(update):
        return await _all_courses(), None
    return [], None


def _course_keyboard(courses, prefix, limit=100):
    buttons = []
    for c in courses[:limit]:
        folder = c.get("folder", "")
        if not folder:
            continue
        label = (c.get("name") or folder)[:60]
        buttons.append([InlineKeyboardButton(label, callback_data=f"{prefix}:{folder}")])
    return buttons


async def _can_manage_content(update):
    """هل يستطيع هذا المستخدم إدارة المحتوى؟ (أدمن، أو عضو هيئة تدريس)."""
    if await user_is_admin(update):
        return True
    instructor_id, _ = await _instructor_context(update)
    return bool(instructor_id)


async def _can_manage_folder(update, folder):
    """عضو هيئة التدريس يدير مقرراته فقط؛ الأدمن يدير كل شيء (FR12)."""
    if await user_is_admin(update):
        return True
    instructor_id, _ = await _instructor_context(update)
    if not instructor_id:
        return False
    courses, _ = await _available_courses(update)
    return any(str(course.get("folder", "")) == str(folder) for course in courses)


# --------------------------------------------------------------------------
# Add content (conversation)
# --------------------------------------------------------------------------

async def addcontent_start(update, context):
    instructor_id, _ = await _instructor_context(update)
    if not instructor_id and not await user_is_admin(update):
        await update.effective_message.reply_text(
            "هذه الخدمة لأعضاء هيئة التدريس أو الأدمن فقط."
        )
        return ConversationHandler.END
    context.user_data.pop("add_course_folder", None)
    context.user_data.pop("add_course_name", None)
    context.user_data.pop("add_new_course", None)
    keyboard = [
        [InlineKeyboardButton("مادة موجودة", callback_data="addmenu:existing")],
        [InlineKeyboardButton("مادة جديدة", callback_data="addmenu:new")],
    ]
    from utils.formatting import add_content_prompt
    await update.effective_message.reply_text(
        add_content_prompt(),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ADD_MENU


async def handle_add_menu(update, context):
    query = update.callback_query
    await query.answer()
    choice = query.data.removeprefix("addmenu:")
    if choice == "new":
        await query.message.reply_text("اكتب اسم المادة الجديدة:")
        return ADD_NEW_NAME
    courses, _ = await _available_courses(update)
    if not courses:
        await query.message.reply_text(
            "لا توجد مواد مسجلة لك. اختر 'مادة جديدة' بدلاً من ذلك."
        )
        return ADD_MENU
    keyboard = _course_keyboard(courses, "addsel")
    await query.message.reply_text(
        "اختر المادة:", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADD_SELECT_COURSE


async def handle_add_course_selected(update, context):
    query = update.callback_query
    await query.answer()
    folder = query.data.removeprefix("addsel:")
    context.user_data["add_course_folder"] = folder
    context.user_data["add_new_course"] = False
    await query.message.reply_text("أرسل الملف (PDF/Word/صورة) الآن:")
    return ADD_WAIT_FILE


async def handle_add_new_name(update, context):
    name = (update.message.text or "").strip()
    if not name:
        await update.message.reply_text("اكتب اسم المادة الجديدة:")
        return ADD_NEW_NAME
    context.user_data["add_course_name"] = name
    context.user_data["add_course_folder"] = slugify_course_name(name)
    context.user_data["add_new_course"] = True
    keyboard = [
        [InlineKeyboardButton("إرسال ملف", callback_data="addnew:yes")],
        [InlineKeyboardButton("إنشاء بدون ملف", callback_data="addnew:no")],
    ]
    await update.message.reply_text(
        f"المادة الجديدة: {name}\nهل تريد إرسال ملف الآن؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ADD_NEW_CONFIRM


async def handle_add_new_confirm(update, context):
    query = update.callback_query
    await query.answer()
    choice = query.data.removeprefix("addnew:")
    if choice == "yes":
        await query.message.reply_text("أرسل الملف الآن:")
        return ADD_WAIT_FILE
    created = await _create_course(update, context)
    if created:
        await query.message.reply_text("تم إنشاء المادة بدون ملف ✅")
    context.user_data.pop("add_course_folder", None)
    context.user_data.pop("add_course_name", None)
    context.user_data.pop("add_new_course", None)
    return ConversationHandler.END


async def _create_course_named(update, context, name, folder=None):
    """ينشئ مادة جديدة في Firestore (ويربطها بالدكتور إن كان موظفاً)."""
    reply = update.effective_message
    name = (name or "").strip()
    if not name:
        await reply.reply_text("اكتب اسم المادة أولاً.")
        return False
    folder = folder or slugify_course_name(name)
    if not folder:
        await reply.reply_text("تعذر إنشاء اسم المجلد من هذا الاسم.")
        return False
    instructor_id, instructor = await _instructor_context(update)
    creator = instructor.get("name") if instructor else "أدمن"
    await asyncio.to_thread(
        db.collection("courses").document(folder).set,
        {"name": name, "folder": folder, "created_by": creator},
    )
    if instructor_id and not await user_is_admin(update):
        await asyncio.to_thread(
            db.collection("instructors").document(instructor_id).update,
            {"courses": firestore.ArrayUnion([{"name": name, "folder": folder}])},
        )
    return True


async def _create_course(update, context):
    folder = context.user_data.get("add_course_folder")
    name = context.user_data.get("add_course_name")
    if not folder or not name:
        return False
    return await _create_course_named(update, context, name, folder=folder)


async def handle_add_document(update, context):
    folder = context.user_data.get("add_course_folder")
    if not folder:
        await update.message.reply_text(
            "لم تُحدد مادة. استخدم /addcontent من البداية."
        )
        return ConversationHandler.END
    document = update.message.document
    name = document.file_name or "ملف.pdf"
    message = update.message
    if document.file_size and document.file_size > 20_000_000:
        await message.reply_text("الملف أكبر من 20MB. أرسل ملفاً أصغر.")
        return ADD_WAIT_FILE
    await message.reply_text("جاري رفع الملف…")
    try:
        telegram_file = await context.bot.get_file(document.file_id)
        data = bytes(await telegram_file.download_as_bytearray())
    except Exception:
        logging.exception("Telegram document download failed")
        await message.reply_text("تعذر تحميل الملف. حاول مرة أخرى.")
        return ADD_WAIT_FILE
    try:
        ok = await asyncio.to_thread(
            github_upload_file, folder, name, data, f"add {name}"
        )
    except Exception:
        logging.exception("GitHub upload failed")
        ok = False
    if ok and context.user_data.get("add_new_course"):
        await _create_course(update, context)
    await message.reply_text("تم رفع الملف بنجاح ✅" if ok else "تعذر رفع الملف.")
    context.user_data.pop("add_course_folder", None)
    context.user_data.pop("add_course_name", None)
    context.user_data.pop("add_new_course", None)
    return ConversationHandler.END


async def addcontent_cancel(update, context):
    context.user_data.pop("add_course_folder", None)
    context.user_data.pop("add_course_name", None)
    context.user_data.pop("add_new_course", None)
    await update.effective_message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END


addcontent_conv = ConversationHandler(
    entry_points=[CommandHandler("addcontent", addcontent_start)],
    states={
        ADD_MENU: [CallbackQueryHandler(handle_add_menu, pattern="^addmenu:")],
        ADD_SELECT_COURSE: [CallbackQueryHandler(handle_add_course_selected, pattern="^addsel:")],
        ADD_NEW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_new_name)],
        ADD_NEW_CONFIRM: [CallbackQueryHandler(handle_add_new_confirm, pattern="^addnew:")],
        ADD_WAIT_FILE: [MessageHandler(filters.Document.ALL, handle_add_document)],
    },
    fallbacks=[CommandHandler("cancel", addcontent_cancel)],
    per_message=False,
)


# --------------------------------------------------------------------------
# Delete content (callbacks)
# --------------------------------------------------------------------------

async def deletecontent_start(update, context):
    instructor_id, _ = await _instructor_context(update)
    if not instructor_id and not await user_is_admin(update):
        await update.effective_message.reply_text(
            "هذه الخدمة لأعضاء هيئة التدريس أو الأدمن فقط."
        )
        return
    keyboard = [
        [InlineKeyboardButton("حذف شيت/ملف", callback_data="delmenu:single")],
        [InlineKeyboardButton("حذف مادة كاملة", callback_data="delmenu:whole")],
    ]
    await update.effective_message.reply_text(
        "ماذا تريد أن تحذف؟", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_delmenu_button(update, context):
    query = update.callback_query
    await query.answer()
    choice = query.data.removeprefix("delmenu:")
    courses, _ = await _available_courses(update)
    if not courses:
        await query.message.reply_text("لا توجد مواد.")
        return
    if choice == "whole":
        keyboard = _course_keyboard(courses, "delwhole")
    else:
        keyboard = _course_keyboard(courses, "delcourse")
    await query.message.reply_text(
        "اختر المادة:", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_delcourse_button(update, context):
    query = update.callback_query
    await query.answer()
    folder = query.data.removeprefix("delcourse:")
    if not await _can_manage_folder(update, folder):
        await query.message.reply_text("ليس لديك صلاحية حذف المحتوى.")
        return
    files = await asyncio.to_thread(list_course_files_with_sha, folder) or []
    if not files:
        await query.message.reply_text("لا توجد ملفات لهذه المادة.")
        return
    context.user_data["del_files"] = files
    buttons = []
    for i, f in enumerate(files[:100]):
        label = f["name"][:60]
        buttons.append([InlineKeyboardButton(label, callback_data=f"delfile:{i}")])
    await query.message.reply_text(
        "اختر الملف للحذف:", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def handle_delfile_button(update, context):
    query = update.callback_query
    await query.answer()
    if not await _can_manage_content(update):
        await query.message.reply_text("ليس لديك صلاحية حذف المحتوى.")
        return
    files = context.user_data.get("del_files", [])
    try:
        file = files[int(query.data.removeprefix("delfile:"))]
    except (ValueError, IndexError):
        await query.message.reply_text("انتهت صلاحية القائمة. ابدأ من جديد.")
        return
    try:
        ok = await asyncio.to_thread(
            github_delete_file, file["path"], file["sha"], f"delete {file['name']}"
        )
        await query.message.reply_text(
            f"تم حذف {file['name']} ✅" if ok else "تعذر حذف الملف."
        )
    except Exception:
        logging.exception("Delete file failed")
        await query.message.reply_text("تعذر حذف الملف.")
    context.user_data.pop("del_files", None)


async def handle_delwhole_select(update, context):
    query = update.callback_query
    await query.answer()
    folder = query.data.removeprefix("delwhole:")
    if not await _can_manage_folder(update, folder):
        await query.message.reply_text("ليس لديك صلاحية حذف المحتوى.")
        return
    context.user_data["del_whole_folder"] = folder
    keyboard = [
        [InlineKeyboardButton("تأكيد الحذف", callback_data="delwholeconfirm:yes")],
        [InlineKeyboardButton("إلغاء", callback_data="delwholeconfirm:no")],
    ]
    await query.message.reply_text(
        "سيتم حذف المادة وكل شيتاتها نهائياً. هل أنت متأكد؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_delwhole_confirm(update, context):
    query = update.callback_query
    await query.answer()
    choice = query.data.removeprefix("delwholeconfirm:")
    folder = context.user_data.get("del_whole_folder")
    context.user_data.pop("del_whole_folder", None)
    if choice == "no" or not folder:
        await query.message.reply_text("تم الإلغاء.")
        return
    if not await _can_manage_folder(update, folder):
        await query.message.reply_text("ليس لديك صلاحية حذف المحتوى.")
        return
    files = await asyncio.to_thread(list_course_files_with_sha, folder) or []
    results = []
    for f in files:
        try:
            results.append(
                await asyncio.to_thread(
                    github_delete_file, f["path"], f["sha"], f"delete {f['name']}"
                )
            )
        except Exception:
            results.append(False)
    if all(results):
        await asyncio.to_thread(db.collection("courses").document(folder).delete)
        await query.message.reply_text("تم حذف المادة وكل الشيتات ✅")
    else:
        await query.message.reply_text(
            "تعذر حذف بعض الملفات؛ لم تُحذف المادة من قاعدة البيانات."
        )


# ============================================================
# من الملف الأصلي: handlers/file_tools.py
# ============================================================


MAX_INLINE_BYTES = 20_000_000


async def _ask_action(message, data, mime, name):
    if len(data) > MAX_INLINE_BYTES:
        await message.reply_text("الملف كبير جداً (أكبر من 20MB). أرسل ملفاً أصغر.")
        return
    buttons = [
        [InlineKeyboardButton("تلخيص كنص", callback_data="fileact:summarize")],
        [InlineKeyboardButton("تلخيص كـ PDF", callback_data="fileact:summarize_pdf")],
        [InlineKeyboardButton("ترجمة كنص", callback_data="fileact:translate")],
        [InlineKeyboardButton("ترجمة كـ PDF", callback_data="fileact:translate_pdf")],
    ]
    await message.reply_text(
        f"استلمت الملف ({name}) ✅ ماذا تريد أن أفعل به؟",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return {"data": data, "mime": mime, "name": name}


async def handle_document(update, context):
    message = update.message
    document = message.document
    name = document.file_name or "ملف"
    mime = document.mime_type or "application/octet-stream"
    if document.file_size and document.file_size > MAX_INLINE_BYTES:
        await message.reply_text("الملف كبير جداً (أكبر من 20MB). أرسل ملفاً أصغر.")
        return
    await message.reply_text("جاري تحميل الملف…")
    try:
        telegram_file = await context.bot.get_file(document.file_id)
        data = bytes(await telegram_file.download_as_bytearray(
            read_timeout=120,
            connect_timeout=30,
        ))
    except Exception:
        logging.exception("Telegram document download failed")
        await message.reply_text("تعذر تحميل الملف. تأكد أن حجمه أقل من 20MB ثم حاول مرة أخرى.")
        return
    context.user_data["pending_file"] = await _ask_action(message, data, mime, name)


async def handle_photo(update, context):
    message = update.message
    photo = message.photo[-1] if message.photo else None
    if not photo:
        return
    await message.reply_text("جاري تحميل الصورة…")
    try:
        telegram_file = await context.bot.get_file(photo.file_id)
        data = bytes(await telegram_file.download_as_bytearray(
            read_timeout=120,
            connect_timeout=30,
        ))
    except Exception:
        logging.exception("Telegram photo download failed")
        await message.reply_text("تعذر تحميل الصورة. حاول إرسال صورة أصغر.")
        return
    context.user_data["pending_file"] = await _ask_action(message, data, "image/jpeg", "صورة")


async def handle_file_action(update, context):
    query = update.callback_query
    await query.answer()
    pending = context.user_data.get("pending_file")
    if not pending or not pending.get("data"):
        await query.message.reply_text("لم أجد الملف. أرسله مرة أخرى.")
        return
    action = query.data.removeprefix("fileact:")
    await query.message.reply_text("جاري المعالجة…")
    try:
        pdf_mode = action.endswith("_pdf")
        base = action.removesuffix("_pdf")
        prompt = ("اكتشف لغة محتوى هذا الملف ثم ترجمه إلى اللغة المقابلة: إن كان بالعربية ترجمه "
                  "إلى الإنجليزية، وإن كان بالإنجليزية ترجمه إلى العربية، مع الحفاظ على المعنى والمصطلحات."
                  if base == "translate"
                  else "لخص محتوى هذا الملف في نقاط واضحة ومرتبة. اكتب الملخص بنفس لغة الملف الأصلية.")
        part = types.Part.from_bytes(data=pending["data"], mime_type=pending["mime"])
        response = await call_gemini_with_retry(client.models.generate_content, model=MODEL_NAME,
                                                contents=[prompt, part])
        result_text = (response.text or "").strip()
        if pdf_mode:
            title = "ترجمة" if base == "translate" else "ملخص"
            pdf_buf = await asyncio.to_thread(text_to_pdf_bytes, result_text, title)
            pdf_bytes = pdf_buf.read() if hasattr(pdf_buf, "read") else pdf_buf
            filename = "translation.pdf" if base == "translate" else "summary.pdf"
            await query.message.reply_document(document=pdf_bytes, filename=filename)
        else:
            await query.message.reply_text(result_text[:4000])
    except Exception:
        logging.exception("Telegram file processing failed")
        await query.message.reply_text("تعذرت معالجة الملف.")
    finally:
        context.user_data.pop("pending_file", None)


# ============================================================
# من الملف الأصلي: handlers/general.py
# ============================================================


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
COURSE_WORDS = ("مادة", "مواد", "المادة", "المواد", "مقرر", "المقرر", "مقررات", "المقررات")
ACTION_ROLE_WORDS = ADD_WORDS + DEL_WORDS + EDIT_WORDS + STUDENT_WORDS + INSTRUCTOR_WORDS + PEOPLE_WORDS + COURSE_WORDS


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
    asks_courses = any(w in normalized for w in COURSE_WORDS)

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

    if asks_courses:
        reply = update.effective_message
        if has_add:
            name = _extract_name(
                text,
                email_match.group() if email_match else "",
                str(admin_id) if admin_id else "",
            )
            if not name or name == "بدون اسم":
                await reply.reply_text("الصيغة: إضافة مادة <اسم المادة>")
                return True
            if await _create_course_named(update, context, name):
                await reply.reply_text(f"تم إنشاء المادة {name} ✅")
            return True
        if asks_list:
            try:
                docs = await asyncio.to_thread(lambda: list(db.collection("courses").stream()))
            except Exception:
                docs = []
            if not docs:
                await reply.reply_text("📋 لا توجد مواد مسجلة.")
            else:
                lines = [f"📋 قائمة المواد ({len(docs)}):", ""]
                lines += [f"📚 {d.id} — {(d.to_dict() or {}).get('name', d.id)}" for d in docs[:50]]
                await reply.reply_text("\n".join(lines))
            return True
        if has_del:
            await reply.reply_text("لحذف مادة أو ملفاتها استخدم الأمر /deletecontent")
            return True
        await reply.reply_text("الصيغة: إضافة مادة <اسم المادة> — أو عرض المواد")
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


HELP_TEXT = help_message()


async def start(update, context):
    chat_id = update.effective_chat.id
    _, student = await asyncio.to_thread(get_student_by_chat_id, chat_id)
    _, instructor = await asyncio.to_thread(get_instructor_by_chat_id, chat_id)
    if student or instructor:
        pass
        if student:
            await _show_student_welcome(update.message)
        else:
            await _show_instructor_welcome(update.message)
        return
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    welcome_text = (
        "🎓 أهلاً بك في بوت الخدمات الجامعية!\n\n"
        "كيف تريد المتابعة؟"
    )
    keyboard = [
        [InlineKeyboardButton("🔐 تسجيل الدخول", callback_data="btn_start_login")],
        [InlineKeyboardButton("👤 متابعة كزائر", callback_data="btn_guest_mode")],
    ]
    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def help_command(update, context):
    await update.message.reply_text(HELP_TEXT)


async def handle_welcome_buttons(update, context):
    query = update.callback_query
    await query.answer()
    from utils.formatting import guest_menu
    await query.edit_message_text(guest_menu())


async def handle_message(update, context):
    t0 = time.time()
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    # إجراء معلّق من قوائم الترحيب: "➕ إضافة مادة" ينتظر اسم المادة
    pending_action = context.user_data.pop("instructor_action", None)
    if pending_action == "add_course" and text.startswith("/"):
        pending_action = None  # أمر حقيقي — لا نستخدمه كاسم مادة
    if pending_action == "add_course":
        if not await _can_manage_content(update):
            await update.message.reply_text("هذه الخدمة لأعضاء هيئة التدريس أو الأدمن فقط.")
            return
        if await _create_course_named(update, context, text):
            await update.message.reply_text(f"تم إنشاء المادة {text} ✅")
        return

    # سؤال محدّد عن مادة مختارة مسبقاً من القائمة
    question_course = None
    if context.user_data.pop("question_type", None) == "course":
        question_course = context.user_data.pop("question_course", None)

    if text.casefold() in {"adminpanel", "لوحة الادمن", "لوحة الأدمن"}:
        if not await user_is_admin(update):
            await update.message.reply_text("ليس لديك صلاحية الوصول لهذه اللوحة.")
            return
        from telegram_bot.admin_panel import admin_panel
        await admin_panel(update, context)
        return
    if text.lower() in ("مساعدة", "help", "المساعدة", "الخدمات", "menu", "قائمة"):
        await update.message.reply_text(HELP_TEXT)
        return
    if text.strip() in ("موادّي", "موادي", "my courses", "mycourses"):
        await show_my_courses(update, context)
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
        prompt = text
        if question_course:
            course_name = question_course
            for c in await _all_courses():
                if c.get("folder") == question_course:
                    course_name = c.get("name") or question_course
                    break
            prompt = f"سؤال الطالب عن مادة «{course_name}»:\n{text}"
        await update.message.reply_text(await generate_answer(prompt, chat_id, instructor_data=instructor, language=language))
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
