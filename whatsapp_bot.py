"""WhatsApp Business Cloud API bot - يعمل بجانب بوت التيليجرام بنفس المنطق.

التشغيل:  python whatsapp_bot.py
المطلوب في .env: WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN
الـ Webhook: اعرض المنفذ (الافتراضي 8445) عبر ngrok وضعه في Meta Developers.
"""
import asyncio
import json
import logging
import random
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import requests
from firebase_admin import firestore
from google.genai import types

from config import (
    client, db, MODEL_NAME,
    WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN,
    WHATSAPP_API_VERSION, WHATSAPP_PORT, ADMIN_WHATSAPP_NUMBERS,
)
from database import get_student_by_chat_id, get_instructor_by_chat_id
from gemini_services import call_gemini_with_retry, detect_user_intent, generate_answer
from github_utils import (
    list_course_files_with_sha, github_upload_file, github_delete_file,
    download_file_bytes, slugify_course_name,
)
from utils import send_otp_email, extract_pdf_text
from handlers.admin import is_stored_admin
from handlers.courses import _all_courses
from handlers.general import _handle_admin_command

WA_BASE = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"
WA_MSG_URL = f"{WA_BASE}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
WA_HEADERS = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

_inbound_phone_id = None


def _base():
    return f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"


def _active_phone_id():
    return _inbound_phone_id or WHATSAPP_PHONE_NUMBER_ID


def _msg_url():
    return f"{_base()}/{_active_phone_id()}/messages"


def _media_url():
    return f"{_base()}/{_active_phone_id()}/media"

_state_lock = threading.Lock()
_wa_state = {}


def _get_state(phone):
    with _state_lock:
        return _wa_state.setdefault(phone, {
            "state": None, "data": {}, "last_file": None,
            "pending_files": [], "welcome_sent": False,
        })


def _reset_state(phone):
    with _state_lock:
        old = _wa_state.get(phone, {})
        _wa_state[phone] = {
            "state": None, "data": {}, "last_file": old.get("last_file"),
            "pending_files": [], "welcome_sent": old.get("welcome_sent", True),
        }


# ---------------------------------------------------------------- إرسال
def wa_send(payload):
    try:
        response = requests.post(_msg_url(), headers=WA_HEADERS, json=payload, timeout=30)
        if response.status_code not in (200, 201):
            logging.error("WhatsApp send failed (%s): %s", response.status_code, response.text[:500])
        return response
    except Exception:
        logging.exception("WhatsApp send error")
        return None


def send_text(to, body):
    text = str(body)[:4000]
    return wa_send({"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text, "preview_url": False}})


def send_buttons(to, body, buttons):
    rows = [{"type": "reply", "reply": {"id": b_id, "title": b_title[:20]}} for b_id, b_title in buttons[:3]]
    if not rows:
        return None
    return wa_send({"messaging_product": "whatsapp", "to": to, "type": "interactive",
                    "interactive": {"type": "button", "body": {"text": str(body)[:1024]},
                                    "action": {"buttons": rows}}})


def send_list(to, body, items, header="", button_text="اختر"):
    rows = [{"id": r_id[:256], "title": r_title[:24], "description": (r_desc or "")[:72]}
            for r_id, r_title, r_desc in items]
    if not rows:
        return None
    sections = [{"title": f"الخيارات ({i // 10 + 1})", "rows": rows[i:i + 10]} for i in range(0, len(rows), 10)]
    return wa_send({"messaging_product": "whatsapp", "to": to, "type": "interactive",
                    "interactive": {"type": "list", "header": {"type": "text", "text": str(header)[:60]},
                                    "body": {"text": str(body)[:1024]},
                                    "action": {"button": str(button_text)[:20], "sections": sections}}})


def upload_media(data, mime, filename):
    url = _media_url()
    try:
        response = requests.post(url, headers=WA_HEADERS,
                                 files={"file": (filename, data, mime)},
                                 data={"messaging_product": "whatsapp", "type": mime}, timeout=120)
        if response.status_code != 200:
            logging.error("Media upload failed (%s): %s", response.status_code, response.text[:500])
            return None
        return (response.json() or {}).get("id")
    except Exception:
        logging.exception("Media upload error")
        return None


def get_media_info(media_id):
    try:
        response = requests.get(f"{WA_BASE}/{media_id}", headers=WA_HEADERS, timeout=30)
        return response.json() if response.status_code == 200 else None
    except Exception:
        logging.exception("Media info error")
        return None


def download_media(media_id):
    info = get_media_info(media_id)
    if not info or not info.get("url"):
        return None, None
    try:
        response = requests.get(info["url"], headers=WA_HEADERS, timeout=120)
        if response.status_code != 200:
            return None, info.get("mime_type")
        return response.content, info.get("mime_type")
    except Exception:
        logging.exception("Media download error")
        return None, None


def send_document(to, media_id, filename):
    return wa_send({"messaging_product": "whatsapp", "to": to, "type": "document",
                    "document": {"id": media_id, "filename": filename[:240]}})


def _guess_mime(filename):
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    return {
        "pdf": "application/pdf", "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "ppt": "application/vnd.ms-powerpoint",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "zip": "application/zip", "png": "image/png", "jpg": "image/jpeg",
        "jpeg": "image/jpeg", "gif": "image/gif", "mp3": "audio/mpeg",
    }.get(ext, "application/octet-stream")


def send_file_from_github(to, file):
    try:
        data = download_file_bytes(file["path"])
        if not data:
            send_text(to, "تعذر تحميل الملف من المستودع.")
            return
        media_id = upload_media(data, _guess_mime(file["name"]), file["name"])
        if not media_id:
            send_text(to, "تعذر رفع الملف إلى واتساب.")
            return
        send_document(to, media_id, file["name"])
    except Exception:
        logging.exception("WhatsApp file send failed")
        send_text(to, "تعذر إرسال الملف الآن.")


# ---------------------------------------------------------------- قائمة/مساعدة
def wa_help(phone):
    send_text(phone, (
        "🎓 بوت خدمات الجامعة\n\n"
        "💬 اسألني أي سؤال عن الجامعة.\n"
        "📚 المقررات والشيتات (للمسجلين).\n"
        "📄 أرسل ملفاً وسألخصه أو أترجمه.\n"
        "🎙️ أرسل صوتاً وسأحوّله لنص.\n\n"
        "🔑 سجّل الدخول لفتح الشيتات.\n"
        "👨‍🏫 للدكاترة: إدارة المحتوى.\n\n"
        "اكتب سؤالك مباشرة، أو اطلب القائمة."
    ))


def wa_show_main_menu(phone):
    items = [
        ("menu:ask", "اسألني سؤالاً", "أي سؤال عن الجامعة"),
        ("menu:courses", "المقررات", "عرض المقررات المتاحة"),
        ("menu:sheets", "الشيتات", "اختر مادة لعرض ملفاتها"),
        ("menu:upload", "رفع ملف", "تلخيص أو ترجمة ملف"),
        ("menu:admin", "إدارة المحتوى", "للدكاترة والأدمن"),
    ]
    send_list(phone, "اختر خدمة:", items, header="القائمة الرئيسية")


async def wa_menu_action(phone, action):
    if action == "ask":
        send_text(phone, "اكتب سؤالك مباشرة وسأجيبك.")
        return
    if action == "courses":
        await wa_show_courses(phone)
        return
    if action == "sheets":
        await route_text(phone, "الشيتات")
        return
    if action == "upload":
        send_text(phone, "أرسل الملف الآن، وسأسألك: تلخيص أم ترجمة؟")
        return
    if action == "admin":
        instructor_id, _ = await asyncio.to_thread(get_instructor_by_chat_id, "wa:" + phone)
        if instructor_id or wa_is_admin(phone):
            send_buttons(phone, "اختر:", [("admin:add", "إضافة محتوى"), ("admin:delete", "حذف محتوى")])
        else:
            send_text(phone, "هذه الخدمة لأعضاء هيئة التدريس أو الأدمن فقط.")
        return


# ---------------------------------------------------------------- أدمن
def wa_is_admin(phone):
    return phone in ADMIN_WHATSAPP_NUMBERS or is_stored_admin(phone)


def _phone_int(phone):
    try:
        return int(phone)
    except (TypeError, ValueError):
        return 0


def _make_update(phone):
    message = SimpleNamespace(reply_text=lambda t, **kw: send_text(phone, t))
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=_phone_int(phone), full_name=""),
        effective_chat=SimpleNamespace(id="wa:" + phone),
        effective_message=message,
    )


# ---------------------------------------------------------------- دخول
def start_login(phone):
    send_text(phone, "اكتب رقمك الجامعي أو معرف الدكتور:")
    _get_state(phone)["state"] = "LOGIN_ASK_ID"


async def handle_login_id(phone, user_id):
    user_id = user_id.strip()
    for collection, role in (("students", "student"), ("instructors", "instructor")):
        doc = await asyncio.to_thread(db.collection(collection).document(user_id).get)
        if doc.exists:
            data = doc.to_dict()
            break
    else:
        send_text(phone, "الرقم غير موجود.")
        _reset_state(phone)
        return
    if not data.get("email"):
        send_text(phone, "لا يوجد بريد إلكتروني لهذا الحساب.")
        _reset_state(phone)
        return
    code = str(random.randint(100000, 999999))
    state = _get_state(phone)
    state["data"] = {"code": code, "user_id": user_id, "role": role, "expires": time.time() + 300}
    state["state"] = "LOGIN_ASK_OTP"
    try:
        await asyncio.to_thread(send_otp_email, data["email"], code)
    except Exception:
        logging.exception("Unable to send OTP")
        send_text(phone, "تعذر إرسال رمز التحقق.")
        _reset_state(phone)
        return
    send_text(phone, "أرسلنا رمز التحقق إلى بريدك. اكتبه هنا:")


async def handle_login_otp(phone, otp):
    state = _get_state(phone)
    pending = state.get("data") or {}
    if not pending or time.time() > pending.get("expires", 0):
        send_text(phone, "انتهت جلسة التحقق. ابدأ من جديد.")
        _reset_state(phone)
        return
    if otp.strip() != pending.get("code"):
        send_text(phone, "الرمز غير صحيح، حاول مرة أخرى:")
        return
    collection = "students" if pending["role"] == "student" else "instructors"
    await asyncio.to_thread(db.collection(collection).document(pending["user_id"]).update,
                            {"chat_id": "wa:" + phone, "last_active": time.time()})
    _reset_state(phone)
    send_text(phone, "تم تسجيل الدخول بنجاح ✅")
    wa_show_main_menu(phone)


def wa_logout(phone):
    key = "wa:" + phone
    for collection, finder in (("students", get_student_by_chat_id), ("instructors", get_instructor_by_chat_id)):
        user_id, user = finder(key)
        if user:
            db.collection(collection).document(user_id).update({"chat_id": None, "last_active": None})
            send_text(phone, "تم تسجيل الخروج بنجاح 👋")
            return
    send_text(phone, "أنت غير مسجل دخول.")


# ---------------------------------------------------------------- مواد/شيتات
async def wa_show_courses(phone):
    courses = await _all_courses()
    if not courses:
        send_text(phone, "لا توجد مقررات.")
        return
    lines = ["المقررات المتاحة:"] + [f"- {c.get('name', '')}" for c in courses[:40]]
    send_text(phone, "\n".join(lines))


async def wa_sheets_for(phone, folder):
    files = await asyncio.to_thread(list_course_files_with_sha, folder) or []
    if not files:
        send_text(phone, "لا توجد ملفات لهذه المادة.")
        return
    state = _get_state(phone)
    state["pending_files"] = files
    if len(files) == 1:
        state["last_file"] = files[0]
        await asyncio.to_thread(send_file_from_github, phone, files[0])
        return
    items = [(f"file:{i}", f["name"][:24], f["name"][:72]) for i, f in enumerate(files[:100])]
    send_list(phone, "اختر الملف:", items, header="الملفات")


async def wa_summarize(phone):
    state = _get_state(phone)
    file = state.get("last_file")
    if not file:
        send_text(phone, "اطلب ملفاً أولاً ثم اطلب التلخيص.")
        return
    try:
        data = await asyncio.to_thread(download_file_bytes, file["path"])
        if not data:
            send_text(phone, "تعذر تحميل الملف.")
            return
        text = await asyncio.to_thread(extract_pdf_text, data)
        if not text.strip():
            send_text(phone, "هذا الملف ليس PDF أو لا يمكن استخراج نص منه للتلخيص.")
            return
        result = await call_gemini_with_retry(client.models.generate_content, model=MODEL_NAME,
                                              contents=f"لخص في نقاط واضحة:\n{text[:6000]}")
        send_text(phone, f"ملخص {file['name']}:\n\n{result.text[:4000]}")
    except Exception:
        logging.exception("Summarise failed")
        send_text(phone, "تعذر تلخيص الملف الآن.")


# ---------------------------------------------------------------- محتوى: إضافة
async def _wa_available_courses(phone):
    instructor_id, instructor = await asyncio.to_thread(get_instructor_by_chat_id, "wa:" + phone)
    if instructor_id:
        return instructor.get("courses") or []
    if wa_is_admin(phone):
        return await _all_courses()
    return []


def wa_add_content_start(phone, is_admin):
    state = _get_state(phone)
    state["data"]["content_is_admin"] = bool(is_admin)
    send_buttons(phone, "اختر نوع المادة:", [("addmenu:existing", "مادة موجودة"), ("addmenu:new", "مادة جديدة")])
    state["state"] = "ADD_MENU"


async def wa_add_menu_choice(phone, action):
    state = _get_state(phone)
    if action == "addmenu:new":
        send_text(phone, "اكتب اسم المادة الجديدة:")
        state["state"] = "ADD_NEW_NAME"
        return
    courses = await _wa_available_courses(phone)
    if not courses:
        send_text(phone, "لا توجد مواد متاحة. اختر مادة جديدة.")
        state["state"] = "ADD_NEW_NAME"
        return
    items = [(f"addcourse:{c.get('folder', '')}", (c.get('name') or 'مادة')[:24], (c.get('folder') or '')[:72])
             for c in courses[:100]]
    state["state"] = "ADD_SELECT_COURSE"
    send_list(phone, "اختر المادة:", items, header="إضافة محتوى")


async def wa_add_new_name(phone, name):
    state = _get_state(phone)
    folder = slugify_course_name(name)
    state["data"].update(add_course_folder=folder, add_new_course_name=name, add_is_new_course=True)
    send_buttons(phone, "هل تريد إرسال ملف الآن؟", [("addnewfile:yes", "إرسال ملف"), ("addnewfile:no", "إنشاء بدون ملف")])
    state["state"] = "ADD_NEW_CONFIRM"


async def wa_add_new_confirm(phone, action):
    state = _get_state(phone)
    if action == "addnewfile:yes":
        send_text(phone, "أرسل الملف الآن:")
        state["state"] = "ADD_WAIT_FILE"
        return
    await wa_create_course(phone, state)
    send_text(phone, "تم إنشاء المادة.")
    _reset_state(phone)


async def wa_create_course(phone, state):
    entry = {"name": state["data"]["add_new_course_name"], "folder": state["data"]["add_course_folder"]}
    instructor_id, instructor = await asyncio.to_thread(get_instructor_by_chat_id, "wa:" + phone)
    creator = instructor.get("name") if instructor else "أدمن"
    await asyncio.to_thread(db.collection("courses").document(entry["folder"]).set, {**entry, "created_by": creator})
    if instructor_id and not state["data"].get("content_is_admin"):
        await asyncio.to_thread(db.collection("instructors").document(instructor_id).update,
                                {"courses": firestore.ArrayUnion([entry])})


async def wa_add_course_selected(phone, action):
    state = _get_state(phone)
    state["data"].update(add_course_folder=action.removeprefix("addcourse:"), add_is_new_course=False)
    send_text(phone, "أرسل الملف الآن:")
    state["state"] = "ADD_WAIT_FILE"


async def wa_add_receive_file(phone, filename, media_id):
    state = _get_state(phone)
    folder = state["data"].get("add_course_folder")
    if not folder:
        send_text(phone, "لم تُحدد مادة. ابدأ من جديد بكتابة 'أضف شيت'.")
        _reset_state(phone)
        return
    send_text(phone, "جاري رفع الملف…")
    try:
        data, _ = await asyncio.to_thread(download_media, media_id)
        if not data:
            send_text(phone, "تعذر تحميل الملف من الواتساب.")
            return
        ok = await asyncio.to_thread(github_upload_file, folder, filename, data, f"add {filename}")
        if ok and state["data"].get("add_is_new_course"):
            await wa_create_course(phone, state)
        send_text(phone, "تم رفع الملف بنجاح ✅" if ok else "تعذر رفع الملف.")
    except Exception:
        logging.exception("Add content failed")
        send_text(phone, "تعذر رفع الملف.")
    finally:
        _reset_state(phone)


# ---------------------------------------------------------------- محتوى: حذف
async def wa_delete_start(phone):
    state = _get_state(phone)
    send_buttons(phone, "ماذا تريد أن تحذف؟", [("delmenu:single", "حذف شيت/ملف"), ("delmenu:whole", "حذف مادة كاملة")])
    state["state"] = "DEL_MENU"


async def wa_del_menu(phone, action):
    state = _get_state(phone)
    courses = await _wa_available_courses(phone)
    if not courses:
        send_text(phone, "لا توجد مواد.")
        _reset_state(phone)
        return
    prefix = "delwhole" if action == "delmenu:whole" else "delcourse"
    items = [(f"{prefix}:{c.get('folder', '')}", (c.get('name') or 'مادة')[:24], (c.get('folder') or '')[:72])
             for c in courses[:100]]
    state["state"] = "DEL_SELECT_COURSE"
    send_list(phone, "اختر المادة:", items, header="الحذف")


async def wa_del_select_course(phone, action):
    state = _get_state(phone)
    prefix, folder = action.split(":", 1)
    if prefix == "delwhole":
        send_buttons(phone, "سيتم حذف المادة وكل شيتاتها نهائياً. متأكد؟",
                     [("delwholeconfirm:yes", "تأكيد الحذف"), ("delwholeconfirm:no", "إلغاء")])
        state["data"]["delete_whole_folder"] = folder
        state["state"] = "DEL_WHOLE_CONFIRM"
        return
    files = await asyncio.to_thread(list_course_files_with_sha, folder) or []
    if not files:
        send_text(phone, "لا توجد ملفات لهذه المادة.")
        _reset_state(phone)
        return
    state["pending_files"] = files
    items = [(f"delfile:{i}", f["name"][:24], f["name"][:72]) for i, f in enumerate(files[:100])]
    state["state"] = "DEL_SELECT_FILE"
    send_list(phone, "اختر الملف للحذف:", items, header="الملفات")


async def wa_del_select_file(phone, action):
    state = _get_state(phone)
    try:
        index = int(action.split(":", 1)[1])
        file = state["pending_files"][index]
    except (ValueError, IndexError):
        send_text(phone, "قائمة منتهية الصلاحية. ابدأ من جديد.")
        _reset_state(phone)
        return
    send_buttons(phone, f"حذف {file['name']}؟", [("delfileconfirm:yes", "نعم احذف"), ("delfileconfirm:no", "إلغاء")])
    state["data"]["del_file_index"] = index
    state["state"] = "DEL_FILE_CONFIRM"


async def wa_del_file_confirm(phone, action):
    state = _get_state(phone)
    if action == "delfileconfirm:no":
        send_text(phone, "تم الإلغاء.")
        _reset_state(phone)
        return
    try:
        file = state["pending_files"][state["data"]["del_file_index"]]
        ok = await asyncio.to_thread(github_delete_file, file["path"], file["sha"], f"delete {file['name']}")
        send_text(phone, "تم الحذف ✅" if ok else "تعذر الحذف.")
    except Exception:
        logging.exception("Delete file failed")
        send_text(phone, "تعذر الحذف.")
    finally:
        _reset_state(phone)


async def wa_del_whole_confirm(phone, action):
    state = _get_state(phone)
    if action == "delwholeconfirm:no":
        send_text(phone, "تم الإلغاء.")
        _reset_state(phone)
        return
    folder = state["data"].get("delete_whole_folder")
    if not folder:
        _reset_state(phone)
        return
    files = await asyncio.to_thread(list_course_files_with_sha, folder) or []
    ok = all(await asyncio.to_thread(github_delete_file, f["path"], f["sha"], f"delete {f['name']}") for f in files)
    if ok:
        await asyncio.to_thread(db.collection("courses").document(folder).delete)
        send_text(phone, "تم حذف المادة وكل الشيتات ✅")
    else:
        send_text(phone, "تعذر حذف بعض الملفات؛ لم تُحذف المادة من قاعدة البيانات.")
    _reset_state(phone)


async def wa_process_upload(phone, action):
    state = _get_state(phone)
    up = state.get("upload_file")
    if not up:
        send_text(phone, "لم أجد الملف. أرسله مرة أخرى.")
        _reset_state(phone)
        return
    send_text(phone, "جاري المعالجة…")
    try:
        data, mime = await asyncio.to_thread(download_media, up["media_id"])
        if not data:
            send_text(phone, "تعذر تحميل الملف.")
            return
        mime = mime or _guess_mime(up.get("name") or "")
        if action == "translate":
            prompt = "ترجم محتوى هذا الملف إلى اللغة العربية مع الحفاظ على المعنى والمصطلحات."
        else:
            prompt = "لخص محتوى هذا الملف في نقاط واضحة ومرتبة باللغة العربية."
        part = types.Part.from_bytes(data=data, mime_type=mime)
        response = await call_gemini_with_retry(client.models.generate_content, model=MODEL_NAME,
                                                contents=[prompt, part])
        send_text(phone, (response.text or "").strip()[:4000])
    except Exception:
        logging.exception("Upload processing failed")
        send_text(phone, "تعذرت معالجة الملف.")
    finally:
        _reset_state(phone)


# ---------------------------------------------------------------- توجيه
async def handle_callback(phone, payload):
    state = _get_state(phone)
    if payload == "login":
        start_login(phone)
        return
    if payload == "guest":
        send_text(phone, (
            "أهلاً بك كزائر 👋 يمكنك الآن:\n"
            "• طرح أي سؤال عن الجامعة.\n"
            "• إرسال ملف وسألخصه أو أترجمه.\n"
            "• إرسال رسالة صوتية وسأحوّلها لنص.\n\n"
            "للدخول إلى المقررات والشيتات سجّل الدخول."
        ))
        return
    if payload.startswith("menu:"):
        await wa_menu_action(phone, payload.removeprefix("menu:"))
        return
    if payload.startswith("sheet:"):
        await wa_sheets_for(phone, payload.removeprefix("sheet:"))
        return
    if payload.startswith("file:"):
        try:
            index = int(payload.split(":", 1)[1])
            file = state["pending_files"][index]
            state["last_file"] = file
            await asyncio.to_thread(send_file_from_github, phone, file)
        except (ValueError, IndexError):
            send_text(phone, "انتهت صلاحية القائمة. اطلب الملفات مرة أخرى.")
        return
    if payload.startswith("uploadact:"):
        await wa_process_upload(phone, payload.removeprefix("uploadact:"))
        return
    if payload.startswith("addmenu:"):
        await wa_add_menu_choice(phone, payload)
        return
    if payload.startswith("addcourse:"):
        await wa_add_course_selected(phone, payload)
        return
    if payload.startswith("addnewfile:"):
        await wa_add_new_confirm(phone, payload)
        return
    if payload.startswith("delmenu:"):
        await wa_del_menu(phone, payload)
        return
    if payload.startswith("delwhole:") or payload.startswith("delcourse:"):
        await wa_del_select_course(phone, payload)
        return
    if payload.startswith("delwholeconfirm:"):
        await wa_del_whole_confirm(phone, payload)
        return
    if payload.startswith("delfile:"):
        await wa_del_select_file(phone, payload)
        return
    if payload.startswith("delfileconfirm:"):
        await wa_del_file_confirm(phone, payload)
        return


async def route_text(phone, text):
    _, student = await asyncio.to_thread(get_student_by_chat_id, "wa:" + phone)
    instructor_id, instructor = await asyncio.to_thread(get_instructor_by_chat_id, "wa:" + phone)
    is_admin = wa_is_admin(phone)

    if text.strip().lower() in ("قائمة", "menu", "مساعدة", "help", "الخدمات"):
        wa_show_main_menu(phone)
        return

    if is_admin and await _handle_admin_command(_make_update(phone), None, text):
        return

    intent = await detect_user_intent(text, is_instructor=bool(instructor))
    is_material_user = bool(student or instructor_id or is_admin)

    if intent == "LOGIN":
        if student or instructor_id:
            send_text(phone, "أنت مسجل دخول بالفعل.")
        else:
            start_login(phone)
        return
    if intent == "LOGOUT":
        wa_logout(phone)
        return
    if intent in ("GET_COURSES", "DR_GET_COURSES"):
        if not is_material_user:
            send_text(phone, "هذه الخدمة للطلاب المسجلين أو الأدمن فقط.")
            return
        await wa_show_courses(phone)
        return
    if intent in ("GET_SHEETS", "DR_GET_SHEETS"):
        if not is_material_user:
            send_text(phone, "هذه الخدمة للطلاب المسجلين أو الأدمن فقط.")
            return
        courses = await _all_courses()
        items = [(f"sheet:{c.get('folder', '')}", (c.get('name') or 'مادة')[:24], (c.get('folder') or '')[:72])
                 for c in courses[:100]]
        if not items:
            send_text(phone, "لا توجد مقررات.")
            return
        send_list(phone, "اختر المادة لعرض شيتاتها:", items, header="الشيتات")
        return
    if intent == "SUMMARIZE":
        if not is_material_user:
            send_text(phone, "هذه الخدمة للطلاب المسجلين أو الأدمن فقط.")
            return
        await wa_summarize(phone)
        return
    if intent == "DR_ADD_CONTENT":
        if not (instructor_id or is_admin):
            send_text(phone, "هذه الخدمة لأعضاء هيئة التدريس أو الأدمن فقط.")
            return
        wa_add_content_start(phone, bool(is_admin and not instructor_id))
        return
    if intent == "DR_DELETE_CONTENT":
        if not (instructor_id or is_admin):
            send_text(phone, "هذه الخدمة لأعضاء هيئة التدريس أو الأدمن فقط.")
            return
        await wa_delete_start(phone)
        return

    answer = await generate_answer(text, "wa:" + phone, instructor_data=instructor)
    send_text(phone, answer)


async def handle_voice(phone, media_id):
    send_text(phone, "جاري معالجة الرسالة الصوتية…")
    try:
        data, mime = await asyncio.to_thread(download_media, media_id)
        if not data:
            send_text(phone, "تعذر تحميل الرسالة الصوتية.")
            return
        part = types.Part.from_bytes(data=data, mime_type=mime or "audio/ogg")
        response = await call_gemini_with_retry(client.models.generate_content, model=MODEL_NAME,
                                                contents=["استخرج النص المنطوق فقط.", part])
        text = (response.text or "").strip()
        if text:
            await route_text(phone, text)
    except Exception:
        logging.exception("Voice processing failed")
        send_text(phone, "تعذرت معالجة الرسالة الصوتية.")


async def process_wa_message(phone, msg):
    state = _get_state(phone)
    if not state.get("welcome_sent"):
        state["welcome_sent"] = True
        wa_help(phone)
        send_buttons(phone, "كيف تريد المتابعة؟",
                     [("login", "تسجيل الدخول"), ("guest", "المتابعة كزائر")])

    msg_type = msg.get("type")
    if msg_type == "interactive":
        interactive = msg.get("interactive") or {}
        payload = None
        if interactive.get("type") == "button_reply":
            payload = (interactive.get("button_reply") or {}).get("id")
        elif interactive.get("type") == "list_reply":
            payload = (interactive.get("list_reply") or {}).get("id")
        if payload:
            await handle_callback(phone, payload)
        return

    if msg_type == "audio":
        media_id = (msg.get("audio") or {}).get("id")
        if media_id:
            await handle_voice(phone, media_id)
        return

    if msg_type in ("document", "image"):
        meta = msg.get(msg_type) or {}
        media_id = meta.get("id")
        if state.get("state") == "ADD_WAIT_FILE":
            await wa_add_receive_file(phone, meta.get("filename") or "file", media_id)
            return
        if not media_id:
            send_text(phone, "تعذر استلام الملف.")
            return
        state["upload_file"] = {
            "media_id": media_id,
            "name": meta.get("filename") or meta.get("caption") or "ملف",
        }
        state["state"] = "UPLOAD_ASK_ACTION"
        send_buttons(phone, "استلمت الملف ✅ ماذا تريد أن أفعل به؟",
                     [("uploadact:summarize", "تلخيص"), ("uploadact:translate", "ترجمة")])
        return

    if msg_type != "text":
        return

    text = (msg.get("text") or {}).get("body") or ""
    current = state.get("state")
    if current == "LOGIN_ASK_ID":
        await handle_login_id(phone, text)
        return
    if current == "LOGIN_ASK_OTP":
        await handle_login_otp(phone, text)
        return
    if current == "ADD_NEW_NAME":
        await wa_add_new_name(phone, text)
        return
    if current == "UPLOAD_ASK_ACTION":
        if any(w in text for w in ("لخص", "لخّص", "تلخيص")):
            await wa_process_upload(phone, "summarize")
        elif any(w in text for w in ("ترجم", "ترجمة")):
            await wa_process_upload(phone, "translate")
        else:
            send_text(phone, "استخدم الأزرار أو اكتب: لخص / ترجم")
        return
    if current in ("ADD_MENU", "ADD_SELECT_COURSE", "ADD_NEW_CONFIRM", "ADD_WAIT_FILE",
                   "DEL_MENU", "DEL_SELECT_COURSE", "DEL_SELECT_FILE", "DEL_FILE_CONFIRM",
                   "DEL_WHOLE_CONFIRM"):
        send_text(phone, "استخدم الأزرار أعلاه للمتابعة.")
        return

    await route_text(phone, text)


# ---------------------------------------------------------------- Webhook
def _handle_webhook_payload(payload):
    global _inbound_phone_id
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value") or {}
                metadata = value.get("metadata") or {}
                if metadata.get("phone_number_id"):
                    _inbound_phone_id = metadata["phone_number_id"]
                for msg in value.get("messages", []):
                    phone = msg.get("from")
                    if not phone:
                        continue
                    asyncio.run(process_wa_message(phone, msg))
    except Exception:
        logging.exception("Webhook processing failed")


class WAHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except Exception:
            pass

    def do_GET(self):
        if self.path in ("/", "/healthz", "/health"):
            self._send(200, "ok")
            return
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if WHATSAPP_VERIFY_TOKEN and query.get("hub.verify_token") == [WHATSAPP_VERIFY_TOKEN]:
            self._send(200, query.get("hub.challenge", [""])[0])
        else:
            self._send(403, "Forbidden")

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            payload = {}
        self._send(200, "OK")
        threading.Thread(target=_handle_webhook_payload, args=(payload,), daemon=True).start()


def main():
    missing = [name for name, value in (
        ("WHATSAPP_TOKEN", WHATSAPP_TOKEN),
        ("WHATSAPP_PHONE_NUMBER_ID", WHATSAPP_PHONE_NUMBER_ID),
        ("WHATSAPP_VERIFY_TOKEN", WHATSAPP_VERIFY_TOKEN),
    ) if not value]
    if missing:
        print(f"ناقص في .env: {', '.join(missing)}")
        return
    server = ThreadingHTTPServer(("0.0.0.0", WHATSAPP_PORT), WAHandler)
    print(f"WhatsApp webhook يعمل على المنفذ {WHATSAPP_PORT}...")
    print("اعرضه للإنترنت عبر:  ngrok http " + str(WHATSAPP_PORT))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("إيقاف البوت.")


if __name__ == "__main__":
    main()
