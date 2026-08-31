"""Instructor content-management handlers (Telegram).

Add content (new/existing course + file) via /addcontent conversation.
Delete content (single file or whole course) via /deletecontent callbacks.
"""
import asyncio
import logging

from firebase_admin import firestore
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler, CommandHandler,
    ConversationHandler, MessageHandler, filters,
)

from config import db
from database import get_instructor_by_chat_id
from github_utils import (
    github_delete_file, github_upload_file, list_course_files_with_sha,
    slugify_course_name,
)
from .admin import user_is_admin
from .courses import _all_courses

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
    await update.effective_message.reply_text(
        "اختر نوع المادة التي تريد إضافة محتوى لها:",
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


async def _create_course(update, context):
    folder = context.user_data.get("add_course_folder")
    name = context.user_data.get("add_course_name")
    if not folder or not name:
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
