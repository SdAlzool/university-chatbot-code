"""Instructor content-management handlers."""
import asyncio
from firebase_admin import firestore
from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import db
from database import get_instructor_by_chat_id
from github_utils import github_delete_file, github_upload_file, list_course_files_with_sha, slugify_course_name
from .admin import user_is_admin

ADD_MENU, ADD_SELECT_COURSE, ADD_NEW_NAME, ADD_NEW_CONFIRM, ADD_WAIT_FILE = range(5)

async def _instructor(update):
    instructor_id, instructor = await asyncio.to_thread(get_instructor_by_chat_id, update.effective_chat.id)
    if instructor:
        return instructor_id, instructor
    if await user_is_admin(update):
        courses = await asyncio.to_thread(lambda: list(db.collection("courses").stream()))
        return None, {
            "name": update.effective_user.full_name,
            "courses": [{"name": course.to_dict().get("name", course.id), "folder": course.id} for course in courses],
            "is_project_admin": True,
        }
    return None, None

async def addcontent_start(update, context):
    _, instructor = await _instructor(update)
    if not instructor:
        await update.message.reply_text("هذه الخدمة لأعضاء هيئة التدريس أو أدمن المشروع فقط.")
        return ConversationHandler.END
    context.user_data["content_is_admin"] = bool(instructor.get("is_project_admin"))
    buttons = [[InlineKeyboardButton("مادة موجودة", callback_data="addmenu:existing")], [InlineKeyboardButton("مادة جديدة", callback_data="addmenu:new")]]
    await update.message.reply_text("اختر نوع المادة:", reply_markup=InlineKeyboardMarkup(buttons))
    return ADD_MENU

async def addcontent_menu_choice(update, context):
    query = update.callback_query; await query.answer()
    _, instructor = await _instructor(update)
    if not instructor: return ConversationHandler.END
    if query.data == "addmenu:new":
        await query.message.reply_text("اكتب اسم المادة الجديدة:")
        return ADD_NEW_NAME
    courses = instructor.get("courses", [])
    buttons = [[InlineKeyboardButton(c.get("name", "مادة"), callback_data=f"addcourse:{c.get('folder', '')}")] for c in courses]
    await query.message.reply_text("اختر المادة:", reply_markup=InlineKeyboardMarkup(buttons))
    return ADD_SELECT_COURSE

async def addcontent_course_selected(update, context):
    query = update.callback_query; await query.answer()
    context.user_data.update(add_course_folder=query.data.removeprefix("addcourse:"), add_is_new_course=False)
    await query.message.reply_text("أرسل الملف:")
    return ADD_WAIT_FILE

async def addcontent_new_name(update, context):
    name = update.message.text.strip()
    context.user_data.update(add_course_folder=slugify_course_name(name), add_new_course_name=name, add_is_new_course=True)
    buttons = [[InlineKeyboardButton("إرسال ملف", callback_data="addnewfile:yes")], [InlineKeyboardButton("إنشاء بدون ملف", callback_data="addnewfile:no")]]
    await update.message.reply_text("هل تريد إرسال ملف الآن؟", reply_markup=InlineKeyboardMarkup(buttons))
    return ADD_NEW_CONFIRM

async def _create_course(instructor_id, instructor, context):
    entry = {"name": context.user_data["add_new_course_name"], "folder": context.user_data["add_course_folder"]}
    await asyncio.to_thread(db.collection("courses").document(entry["folder"]).set, {**entry, "created_by": instructor.get("name")})
    if not context.user_data.get("content_is_admin"):
        await asyncio.to_thread(db.collection("instructors").document(instructor_id).update, {"courses": firestore.ArrayUnion([entry])})

async def addcontent_new_confirm(update, context):
    query = update.callback_query; await query.answer()
    if query.data == "addnewfile:yes":
        await query.message.reply_text("أرسل الملف:"); return ADD_WAIT_FILE
    instructor_id, instructor = await _instructor(update)
    if not instructor: return ConversationHandler.END
    await _create_course(instructor_id, instructor, context)
    await query.message.reply_text("تم إنشاء المادة.")
    return ConversationHandler.END

async def addcontent_receive_file(update, context):
    instructor_id, instructor = await _instructor(update)
    if not instructor or not update.message.document: return ConversationHandler.END
    folder = context.user_data.get("add_course_folder")
    if not folder: return ConversationHandler.END
    document = update.message.document
    telegram_file = await context.bot.get_file(document.file_id)
    success = await asyncio.to_thread(github_upload_file, folder, document.file_name, bytes(await telegram_file.download_as_bytearray()), f"add {document.file_name}")
    if success and context.user_data.get("add_is_new_course"):
        await _create_course(instructor_id, instructor, context)
    await update.message.reply_text("تم رفع الملف بنجاح." if success else "تعذر رفع الملف.")
    return ConversationHandler.END

async def deletecontent_start(update, context):
    _, instructor = await _instructor(update)
    if not instructor: return
    context.user_data["content_is_admin"] = bool(instructor.get("is_project_admin"))
    buttons = [
        [InlineKeyboardButton("حذف شيت/ملف", callback_data="delmenu:single")],
        [InlineKeyboardButton("حذف مادة كاملة", callback_data="delmenu:whole")],
    ]
    await update.message.reply_text("ماذا تريد أن تحذف؟", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_delcourse_button(update, context):
    query = update.callback_query; await query.answer()
    folder = query.data.removeprefix("delcourse:")
    files = await asyncio.to_thread(list_course_files_with_sha, folder) or []
    context.user_data.update(delete_course_folder=folder, delete_files=files)
    await query.message.reply_text("اختر الملف:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f["name"], callback_data=f"delfile:{i}")] for i, f in enumerate(files)]))

async def handle_delfile_button(update, context):
    query = update.callback_query; await query.answer()
    files = context.user_data.get("delete_files", [])
    try: file = files[int(query.data.removeprefix("delfile:"))]
    except (ValueError, IndexError): return
    success = await asyncio.to_thread(github_delete_file, file["path"], file["sha"], f"delete {file['name']}")
    await query.message.reply_text("تم الحذف." if success else "تعذر الحذف.")

async def handle_delmenu_button(update, context):
    query = update.callback_query; await query.answer()
    _, instructor = await _instructor(update)
    if not instructor: return
    action = query.data.removeprefix("delmenu:")
    prefix = "delwhole" if action == "whole" else "delcourse"
    buttons = [[InlineKeyboardButton(c.get("name", "مادة"), callback_data=f"{prefix}:{c.get('folder', '')}")] for c in instructor.get("courses", [])]
    await query.message.reply_text("اختر المادة:", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_delwhole_select(update, context):
    query = update.callback_query; await query.answer()
    context.user_data["delete_whole_folder"] = query.data.removeprefix("delwhole:")
    buttons = [[InlineKeyboardButton("تأكيد الحذف", callback_data="delwholeconfirm:yes"), InlineKeyboardButton("إلغاء", callback_data="delwholeconfirm:no")]]
    await query.message.reply_text("سيتم حذف المادة وكل شيتاتها نهائيًا. متأكد؟", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_delwhole_confirm(update, context):
    query = update.callback_query; await query.answer()
    if query.data == "delwholeconfirm:no":
        await query.message.reply_text("تم الإلغاء."); return
    folder = context.user_data.get("delete_whole_folder")
    if not folder: return
    files = await asyncio.to_thread(list_course_files_with_sha, folder) or []
    success = all(await asyncio.to_thread(github_delete_file, file["path"], file["sha"], f"delete {file['name']}") for file in files)
    if success:
        await asyncio.to_thread(db.collection("courses").document(folder).delete)
        await query.message.reply_text("تم حذف المادة وكل الشيتات.")
    else:
        await query.message.reply_text("تعذر حذف بعض ملفات المادة؛ لم تُحذف بيانات المادة من قاعدة البيانات.")

addcontent_conv = ConversationHandler(
    entry_points=[CommandHandler("addcontent", addcontent_start)],
    states={
        ADD_MENU: [CallbackQueryHandler(addcontent_menu_choice, pattern="^addmenu:")],
        ADD_SELECT_COURSE: [CallbackQueryHandler(addcontent_course_selected, pattern="^addcourse:")],
        ADD_NEW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, addcontent_new_name)],
        ADD_NEW_CONFIRM: [CallbackQueryHandler(addcontent_new_confirm, pattern="^addnewfile:")],
        ADD_WAIT_FILE: [MessageHandler(filters.Document.ALL, addcontent_receive_file)],
    },
    fallbacks=[CommandHandler("cancel", lambda update, context: ConversationHandler.END)],
    per_message=False,
)
