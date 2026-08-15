"""Authentication handlers."""
import asyncio
import logging
import random
import time
from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters
from config import db
from database import get_instructor_by_chat_id, get_student_by_chat_id
from utils import send_otp_email

ASK_ID, ASK_OTP = range(2)
_pending_otp = {}

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
    code = str(random.randint(100000, 999999))
    _pending_otp[update.effective_chat.id] = {"code": code, "user_id": user_id, "role": role, "expires": time.time() + 300}
    try:
        await asyncio.to_thread(send_otp_email, data["email"], code)
    except Exception:
        logging.exception("Unable to send OTP")
        await update.message.reply_text("تعذر إرسال رمز التحقق.")
        return ConversationHandler.END
    await update.message.reply_text("أرسلنا رمز التحقق إلى بريدك. اكتبه هنا:")
    return ASK_OTP

async def login_ask_otp(update, context):
    chat_id = update.effective_chat.id
    pending = _pending_otp.get(chat_id)
    if not pending or time.time() > pending["expires"]:
        _pending_otp.pop(chat_id, None)
        await update.message.reply_text("انتهت جلسة التحقق. ابدأ بـ /login.")
        return ConversationHandler.END
    if update.message.text.strip() != pending["code"]:
        await update.message.reply_text("الرمز غير صحيح، حاول مرة أخرى:")
        return ASK_OTP
    collection = "students" if pending["role"] == "student" else "instructors"
    await asyncio.to_thread(db.collection(collection).document(pending["user_id"]).update, {"chat_id": str(chat_id), "last_active": time.time()})
    _pending_otp.pop(chat_id, None)
    await update.message.reply_text("تم تسجيل الدخول بنجاح ✅")
    return ConversationHandler.END

async def logout(update, context):
    chat_id = update.effective_chat.id
    for collection, finder in (("students", get_student_by_chat_id), ("instructors", get_instructor_by_chat_id)):
        user_id, user = await asyncio.to_thread(finder, chat_id)
        if user:
            await asyncio.to_thread(db.collection(collection).document(user_id).update, {"chat_id": None, "last_active": None})
            await update.message.reply_text("تم تسجيل الخروج بنجاح 👋")
            return
    await update.message.reply_text("أنت غير مسجل دخول.")

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
