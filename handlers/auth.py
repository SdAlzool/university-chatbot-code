"""Authentication handlers."""
import asyncio
import logging
import secrets
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters
from config import db
from database import get_instructor_by_chat_id, get_student_by_chat_id
from utils import send_otp_email

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
    buttons = [
        [InlineKeyboardButton("❓ سؤال عن الجامعة", callback_data="student:university")],
        [InlineKeyboardButton("📚 سؤال عن مادة", callback_data="student:course_question")],
        [InlineKeyboardButton("📖 موادّي", callback_data="student:mycourses")],
    ]
    await message.reply_text(
        "✅ تم تسجيل الدخول بنجاح!\n\n"
        "اختر ما تريد:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def _show_instructor_welcome(message):
    """Show welcome menu for instructors after login."""
    buttons = [
        [InlineKeyboardButton("📚 عرض المواد", callback_data="instructor:view_courses")],
        [InlineKeyboardButton("➕ إضافة مادة", callback_data="instructor:add_course")],
        [InlineKeyboardButton("🗑️ حذف مادة", callback_data="instructor:delete_course")],
    ]
    await message.reply_text(
        "✅ تم تسجيل الدخول بنجاح!\n\n"
        "مرحباً بك أستاذي! اختر ما تريد:",
        reply_markup=InlineKeyboardMarkup(buttons)
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
        # Show courses list
        from handlers.courses import _available_courses_for_user
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
        from handlers.courses import show_my_courses
        await show_my_courses(update, context)


async def handle_ask_course(update, context):
    """Handle when student selects a course to ask about."""
    query = update.callback_query
    await query.answer()
    folder = query.data.removeprefix("askcourse:")
    
    context.user_data["question_type"] = "course"
    context.user_data["question_course"] = folder
    
    await query.message.reply_text(f"اكتب سؤالك عن هذه المادة:")


async def handle_instructor_callback(update, context):
    """Handle instructor menu callbacks."""
    query = update.callback_query
    await query.answer()
    
    action = query.data.removeprefix("instructor:")
    
    if action == "view_courses":
        from handlers.courses import _all_courses
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
        # Show courses to delete
        from handlers.courses import _all_courses
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