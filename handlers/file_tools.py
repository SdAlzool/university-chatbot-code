"""رفع ملف -> تلخيص أو ترجمة (بوت التيليجرام)."""
import asyncio
import logging

from google.genai import types
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import client, MODEL_NAME
from gemini_services import call_gemini_with_retry
from pdf_utils import text_to_pdf_bytes

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
