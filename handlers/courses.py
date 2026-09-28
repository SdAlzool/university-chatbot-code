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

async def show_my_courses(update, context):
    """Show only the student's assigned courses with options."""
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
    
    from formatting import my_courses_list
    await update.message.reply_text(
        my_courses_list(courses),
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

async def handle_my_course_button(update, context):
    """Handle when student clicks on a course."""
    query = update.callback_query
    await query.answer()
    folder = query.data.removeprefix("mycourse:")
    
    # Store selected course
    context.user_data["selected_course"] = folder
    
    # Get course name
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
    """Handle course options (syllabus, refs, exams, sheets)."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.removeprefix("courseopt:").split(":", 1)
    if len(parts) != 2:
        return
    
    option, folder = parts

    if not await _can_access_folder(update, folder):
        await query.message.reply_text("ليس لديك صلاحية الوصول إلى هذا المقرر.")
        return
    
    # Get files from GitHub
    files = await asyncio.to_thread(list_course_files_with_sha, folder)
    if not files:
        await query.message.reply_text("لا توجد ملفات لهذه المادة.")
        return
    
    # Filter files based on option
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
    
    # Show files
    if len(filtered_files) == 1:
        context.user_data["last_file"] = filtered_files[0]
        await _send_file_with_options(query.message, context, filtered_files[0], folder)
        return
    
    context.user_data["pending_files"] = filtered_files
    context.user_data["current_folder"] = folder
    buttons = [[InlineKeyboardButton(f["name"], callback_data=f"filesel:{i}")] for i, f in enumerate(filtered_files)]
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"mycourse:{folder}")])
    await query.message.reply_text(
        "اختر الملف:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def _send_file_with_options(target, context, file, folder):
    """Show file with options (download, translate, summarize)."""
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
    """Handle download, translation, and summary actions for a selected course file."""
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
    """Translate a PDF file."""
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
    """Summarize a PDF file."""
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
    """Handle back button to show my courses again."""
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
    from .admin import user_is_admin
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
        # Return only courses assigned to this student
        assigned_courses = student.get("courses") or []
        if not assigned_courses:
            return [], student_id
        # Get full course details for assigned courses
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

async def assign_course_to_student(student_id, course_folder):
    """Assign a course to a student."""
    from config import db
    from firebase_admin import firestore
    await asyncio.to_thread(
        db.collection("students").document(student_id).update,
        {"courses": firestore.ArrayUnion([course_folder])}
    )

async def remove_course_from_student(student_id, course_folder):
    """Remove a course from a student."""
    from config import db
    from firebase_admin import firestore
    await asyncio.to_thread(
        db.collection("students").document(student_id).update,
        {"courses": firestore.ArrayRemove([course_folder])}
    )

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
