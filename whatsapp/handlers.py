"""منطق الأوامر والردود في واتساب."""

import asyncio
import logging
import secrets
import time
from types import SimpleNamespace

from firebase_admin import firestore
from google.genai import types

from config import ADMIN_WHATSAPP_NUMBERS, MODEL_NAME
from services.email_service import send_otp_email
from services.firebase_db import (
    clear_pending_upload,
    db,
    get_instructor_by_chat_id,
    get_pending_upload,
    get_student_by_chat_id,
    mark_welcome_sent,
    save_pending_upload,
    set_chat_language,
    was_welcome_sent,
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
    download_file_bytes,
    github_delete_file,
    github_upload_file,
    list_course_files_with_sha,
    slugify_course_name,
)
from telegram_bot.admin_panel import is_stored_admin
from telegram_bot.handlers import _all_courses, _handle_admin_command
from utils.pdf_utils import extract_pdf_text
from whatsapp.admin_panel import wa_admin_add_execute, wa_admin_callback, wa_admin_menu
from whatsapp.api import (
    _guess_mime,
    download_media,
    get_state,
    reset_state,
    send_buttons,
    send_file_from_github,
    send_list,
    send_text,
    upload_media,
)


# ============================================================
# من الملف الأصلي: whatsapp_handlers.py
# ============================================================


def wa_is_admin(phone):
    return phone in ADMIN_WHATSAPP_NUMBERS or is_stored_admin(phone)


def _phone_int(phone):
    try:
        return int(phone)
    except (TypeError, ValueError):
        return 0


def _make_update(phone):
    async def _reply_text(t, **kw):
        send_text(phone, t)
    message = SimpleNamespace(reply_text=_reply_text)
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=_phone_int(phone), full_name=""),
        effective_chat=SimpleNamespace(id="wa:" + phone),
        effective_message=message,
    )


# ============================================================
# Welcome / Main Menu
# ============================================================

def wa_show_welcome(phone):
    send_buttons(
        phone,
        "🎓 أهلاً بك في بوت الخدمات الجامعية!\n\nكيف تريد المتابعة؟",
        [("login", "🔐 تسجيل الدخول"), ("guest", "👤 متابعة كزائر")]
    )


def wa_show_guest_menu(phone):
    send_text(phone, (
        "👤 مرحباً بك كزائر!\n\n"
        "يمكنك الآن:\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💬 طرح أسئلة عن الجامعة\n"
        "📄 إرسال ملف لتلخيصه أو ترجمته\n"
        "🎙️ إرسال رسالة صوتية\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "للوصول للمقررات والشيتات سجّل الدخول"
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
    elif action == "courses":
        await wa_show_courses(phone)
    elif action == "sheets":
        await route_text(phone, "الشيتات")
    elif action == "upload":
        send_text(phone, "أرسل الملف الآن، وسأسألك: تلخيص أم ترجمة؟")
    elif action == "admin":
        instructor_id, _ = await asyncio.to_thread(get_instructor_by_chat_id, "wa:" + phone)
        if await asyncio.to_thread(wa_is_admin, phone):
            wa_admin_menu(phone)
        elif instructor_id:
            send_buttons(phone, "اختر:", [("admin:add", "إضافة محتوى"), ("admin:delete", "حذف محتوى")])
        else:
            send_text(phone, "هذه الخدمة لأعضاء هيئة التدريس أو الأدمن فقط.")


async def wa_welcome_menu_action(phone, action):
    """خيارات قوائم الترحيب (بعد تسجيل الدخول) في واتساب."""
    if action == "ask":
        send_text(phone, "اكتب سؤالك عن الجامعة مباشرة وسأجيبك.")
        return
    if action == "course":
        courses = await _wa_available_courses(phone)
        if not courses:
            send_text(phone, "لا توجد مواد متاحة لك.")
            return
        items = [
            (f"askcourse:{c.get('folder', '')}", (c.get("name") or "مادة")[:24], (c.get("folder") or "")[:72])
            for c in courses[:100]
        ]
        send_list(phone, "اختر المادة لسؤالك:", items, header="المواد")
        return
    if action == "my":
        await wa_show_my_courses(phone)
        return
    if action == "courses":
        await wa_show_courses(phone)
        return
    if action == "add":
        wa_add_content_start(phone, False)
        return
    if action == "del":
        await wa_delete_start(phone)
        return
    wa_show_main_menu(phone)


async def wa_ask_course_selected(phone, folder):
    if not await _wa_can_access_folder(phone, folder):
        send_text(phone, "ليس لديك صلاحية الوصول إلى هذا المقرر.")
        return
    courses = await _all_courses()
    name = folder
    for c in courses:
        if c.get("folder") == folder:
            name = c.get("name") or folder
            break
    state = get_state(phone)
    state["state"] = "ASK_COURSE"
    state["data"]["ask_course_name"] = name
    send_text(phone, f"اكتب سؤالك عن مادة {name}:")


# ============================================================
# Login
# ============================================================

def start_login(phone):
    send_text(phone, "اكتب رقمك الجامعي أو معرف الدكتور:")
    get_state(phone)["state"] = "LOGIN_ASK_ID"


async def handle_login_id(phone, user_id):
    user_id = user_id.strip()
    state = get_state(phone)
    if time.time() - state.get("otp_sent_at", 0) < 60:
        send_text(phone, "انتظر دقيقة قبل طلب رمز جديد.")
        return
    for collection, role in (("students", "student"), ("instructors", "instructor")):
        doc = await asyncio.to_thread(db.collection(collection).document(user_id).get)
        if doc.exists:
            data = doc.to_dict()
            break
    else:
        send_text(phone, "الرقم غير موجود.")
        reset_state(phone)
        return

    if not data.get("email"):
        send_text(phone, "لا يوجد بريد إلكتروني لهذا الحساب.")
        reset_state(phone)
        return

    code = str(secrets.randbelow(900000) + 100000)
    try:
        await asyncio.to_thread(send_otp_email, data["email"], code)
    except Exception:
        reset_state(phone)
        logging.exception("Unable to send OTP email")
        send_text(phone, "تعذر إرسال رمز التحقق إلى البريد الإلكتروني.")
        return

    state = get_state(phone)
    state["otp_sent_at"] = time.time()
    state["data"] = {"code": code, "user_id": user_id, "role": role, "expires": time.time() + 300, "attempts": 0}
    state["state"] = "LOGIN_ASK_OTP"
    send_text(phone, "تم إرسال رمز التحقق إلى بريدك الإلكتروني. اكتبه هنا خلال 5 دقائق:")


async def handle_login_otp(phone, otp):
    state = get_state(phone)
    pending = state.get("data") or {}
    if not pending or time.time() > pending.get("expires", 0):
        send_text(phone, "انتهت جلسة التحقق. ابدأ من جديد.")
        reset_state(phone)
        return
    if otp.strip() != pending.get("code"):
        pending["attempts"] = pending.get("attempts", 0) + 1
        if pending["attempts"] >= 5:
            reset_state(phone)
            send_text(phone, "تم إلغاء التحقق بعد محاولات كثيرة. ابدأ من جديد.")
            return
        send_text(phone, "الرمز غير صحيح، حاول مرة أخرى:")
        return
    collection = "students" if pending["role"] == "student" else "instructors"
    await asyncio.to_thread(
        db.collection(collection).document(pending["user_id"]).update,
        {"chat_id": "wa:" + phone, "last_active": time.time()},
    )
    reset_state(phone)
    send_text(phone, "تم تسجيل الدخول بنجاح ✅")
    state = get_state(phone)
    state["menu_shown_at"] = time.time()
    if pending["role"] == "student":
        from utils.formatting import student_welcome_menu
        send_buttons(phone, student_welcome_menu().strip(), [
            ("wmenu:ask", "❓ سؤال عن الجامعة"),
            ("wmenu:course", "📚 سؤال عن مادة"),
            ("wmenu:my", "📖 موادي"),
        ])
    else:
        from utils.formatting import instructor_welcome_menu
        send_buttons(phone, instructor_welcome_menu().strip(), [
            ("wmenu:courses", "📚 عرض المواد"),
            ("wmenu:add", "➕ إضافة مادة"),
            ("wmenu:del", "🗑️ حذف مادة"),
        ])


def wa_logout(phone):
    key = "wa:" + phone
    for collection, finder in (("students", get_student_by_chat_id), ("instructors", get_instructor_by_chat_id)):
        user_id, user = finder(key)
        if user:
            db.collection(collection).document(user_id).update({"chat_id": None, "last_active": None})
            send_text(phone, "تم تسجيل الخروج بنجاح 👋")
            return
    send_text(phone, "أنت غير مسجل دخول.")


# ============================================================
# Courses / Sheets
# ============================================================

async def _wa_available_courses(phone):
    instructor_id, instructor = await asyncio.to_thread(get_instructor_by_chat_id, "wa:" + phone)
    if instructor_id:
        return instructor.get("courses") or []
    student_id, student = await asyncio.to_thread(get_student_by_chat_id, "wa:" + phone)
    if student:
        assigned_courses = student.get("courses") or []
        if not assigned_courses:
            return []
        all_courses = await _all_courses()
        return [c for c in all_courses if c.get("folder") in assigned_courses]
    if await asyncio.to_thread(wa_is_admin, phone):
        return await _all_courses()
    return []


async def _wa_can_access_folder(phone, folder):
    courses = await _wa_available_courses(phone)
    return any(str(course.get("folder", "")) == folder for course in courses)


async def wa_show_courses(phone):
    courses = await _wa_available_courses(phone)
    if not courses:
        send_text(phone, "لا توجد مقررات.")
        return
    lines = ["المقررات المتاحة:"] + [f"- {c.get('name', '')}" for c in courses[:40]]
    send_text(phone, "\n".join(lines))


async def wa_show_my_courses(phone):
    student_id, student = await asyncio.to_thread(get_student_by_chat_id, "wa:" + phone)
    if not student:
        send_text(phone, "غير مسجل دخول. استخدم أمر /login.")
        return
    assigned_courses = student.get("courses") or []
    if not assigned_courses:
        courses = []
    else:
        all_courses = await _all_courses()
        courses = [c for c in all_courses if c.get("folder") in assigned_courses]
    if not courses:
        send_text(phone, "لا توجد مواد مخصصة لك.")
        return
    state = get_state(phone)
    state["my_courses"] = courses
    items = []
    for c in courses:
        name = c.get("name", "مادة")
        folder = c.get("folder", "")
        items.append((f"mycourse:{folder}", name[:24], folder[:72]))
    send_list(phone, "📚 موادّي:\nاختر المادة لعرض التفاصيل:", items, header="المواد")


async def wa_sheets_for(phone, folder):
    if not await _wa_can_access_folder(phone, folder):
        send_text(phone, "ليس لديك صلاحية الوصول إلى هذا المقرر.")
        return
    files = await asyncio.to_thread(list_course_files_with_sha, folder) or []
    if not files:
        send_text(phone, "لا توجد ملفات لهذه المادة.")
        return
    state = get_state(phone)
    state["pending_files"] = files
    if len(files) == 1:
        state["last_file"] = files[0]
        await asyncio.to_thread(send_file_from_github, phone, files[0])
        return
    items = [(f"file:{i}", f["name"][:24], f["name"][:72]) for i, f in enumerate(files[:100])]
    send_list(phone, "اختر الملف:", items, header="الملفات")


async def wa_my_course_selected(phone, folder):
    if not await _wa_can_access_folder(phone, folder):
        send_text(phone, "ليس لديك صلاحية الوصول إلى هذا المقرر.")
        return
    state = get_state(phone)
    state["selected_course"] = folder
    courses = await _all_courses()
    course_name = "المادة"
    for c in courses:
        if c.get("folder") == folder:
            course_name = c.get("name", "المادة")
            break
    buttons = [
        ("courseopt:syllabus:" + folder, "📋 المقرر"),
        ("courseopt:refs:" + folder, "📖 المراجع"),
        ("courseopt:exams:" + folder, "📝 الامتحانات"),
        ("sheet:" + folder, "📄 الشيتات"),
    ]
    send_buttons(phone, f"📚 {course_name}\n\nاختر:", buttons)


async def wa_course_option(phone, action):
    parts = action.split(":", 1)
    if len(parts) != 2:
        return
    option, folder = parts
    if not await _wa_can_access_folder(phone, folder):
        send_text(phone, "ليس لديك صلاحية الوصول إلى هذا المقرر.")
        return
    files = await asyncio.to_thread(list_course_files_with_sha, folder) or []
    if not files:
        send_text(phone, "لا توجد ملفات لهذه المادة.")
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
    if not filtered_files:
        filtered_files = files
    state = get_state(phone)
    state["pending_files"] = filtered_files
    if len(filtered_files) == 1:
        state["last_file"] = filtered_files[0]
        await asyncio.to_thread(send_file_from_github, phone, filtered_files[0])
        return
    items = [(f"file:{i}", f["name"][:24], f["name"][:72]) for i, f in enumerate(filtered_files[:100])]
    send_list(phone, "اختر الملف:", items, header="الملفات")


async def wa_summarize(phone):
    state = get_state(phone)
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
        result = await call_gemini_with_retry(
            client.models.generate_content, model=MODEL_NAME,
            contents=(
                "لخص النص التالي في نقاط واضحة ومرتبة. "
                "مهم جداً: اكتشف لغة النص الأصلي واكتب الملخص بنفس تلك اللغة تماماً "
                "(لو النص إنجليزي اكتب الملخص بالإنجليزي، ولو عربي اكتب الملخص بالعربي).\n\n"
                f"النص:\n{text[:6000]}"
            ),
        )
        send_text(phone, f"ملخص {file['name']}:\n\n{result.text[:4000]}")
    except Exception:
        logging.exception("Summarise failed")
        send_text(phone, "تعذر تلخيص الملف الآن.")


# ============================================================
# Content: Add
# ============================================================

def wa_add_content_start(phone, is_admin):
    state = get_state(phone)
    state["data"]["content_is_admin"] = bool(is_admin)
    send_buttons(phone, "اختر نوع المادة:", [("addmenu:existing", "مادة موجودة"), ("addmenu:new", "مادة جديدة")])
    state["state"] = "ADD_MENU"


async def wa_add_menu_choice(phone, action):
    state = get_state(phone)
    if action == "addmenu:new":
        send_text(phone, "اكتب اسم المادة الجديدة:")
        state["state"] = "ADD_NEW_NAME"
        return
    courses = await _wa_available_courses(phone)
    if not courses:
        send_text(phone, "لا توجد مواد متاحة. اختر مادة جديدة.")
        state["state"] = "ADD_NEW_NAME"
        return
    items = [(f"addcourse:{c.get('folder', '')}", (c.get("name") or "مادة")[:24], (c.get("folder") or "")[:72]) for c in courses[:100]]
    state["state"] = "ADD_SELECT_COURSE"
    send_list(phone, "اختر المادة:", items, header="إضافة محتوى")


async def wa_add_new_name(phone, name):
    state = get_state(phone)
    folder = slugify_course_name(name)
    state["data"].update(add_course_folder=folder, add_new_course_name=name, add_is_new_course=True)
    send_buttons(phone, "هل تريد إرسال ملف الآن؟", [("addnewfile:yes", "إرسال ملف"), ("addnewfile:no", "إنشاء بدون ملف")])
    state["state"] = "ADD_NEW_CONFIRM"


async def wa_add_new_confirm(phone, action):
    state = get_state(phone)
    if action == "addnewfile:yes":
        send_text(phone, "أرسل الملف الآن:")
        state["state"] = "ADD_WAIT_FILE"
        return
    await wa_create_course(phone, state)
    send_text(phone, "تم إنشاء المادة.")
    reset_state(phone)


async def wa_create_course(phone, state):
    entry = {"name": state["data"]["add_new_course_name"], "folder": state["data"]["add_course_folder"]}
    instructor_id, instructor = await asyncio.to_thread(get_instructor_by_chat_id, "wa:" + phone)
    creator = instructor.get("name") if instructor else "أدمن"
    await asyncio.to_thread(db.collection("courses").document(entry["folder"]).set, {**entry, "created_by": creator})
    if instructor_id and not state["data"].get("content_is_admin"):
        await asyncio.to_thread(
            db.collection("instructors").document(instructor_id).update,
            {"courses": firestore.ArrayUnion([entry])},
        )


async def wa_add_course_selected(phone, action):
    state = get_state(phone)
    state["data"].update(add_course_folder=action.removeprefix("addcourse:"), add_is_new_course=False)
    send_text(phone, "أرسل الملف الآن:")
    state["state"] = "ADD_WAIT_FILE"


async def wa_add_receive_file(phone, filename, media_id):
    state = get_state(phone)
    folder = state["data"].get("add_course_folder")
    if not folder:
        send_text(phone, "لم تُحدد مادة. ابدأ من جديد بكتابة 'أضف شيت'.")
        reset_state(phone)
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
        reset_state(phone)


# ============================================================
# Content: Delete
# ============================================================

async def wa_delete_start(phone):
    state = get_state(phone)
    send_buttons(phone, "ماذا تريد أن تحذف؟", [("delmenu:single", "حذف شيت/ملف"), ("delmenu:whole", "حذف مادة كاملة")])
    state["state"] = "DEL_MENU"


async def wa_del_menu(phone, action):
    state = get_state(phone)
    courses = await _wa_available_courses(phone)
    if not courses:
        send_text(phone, "لا توجد مواد.")
        reset_state(phone)
        return
    prefix = "delwhole" if action == "delmenu:whole" else "delcourse"
    items = [(f"{prefix}:{c.get('folder', '')}", (c.get("name") or "مادة")[:24], (c.get("folder") or "")[:72]) for c in courses[:100]]
    state["state"] = "DEL_SELECT_COURSE"
    send_list(phone, "اختر المادة:", items, header="الحذف")


async def wa_del_select_course(phone, action):
    state = get_state(phone)
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
        reset_state(phone)
        return
    state["pending_files"] = files
    items = [(f"delfile:{i}", f["name"][:24], f["name"][:72]) for i, f in enumerate(files[:100])]
    state["state"] = "DEL_SELECT_FILE"
    send_list(phone, "اختر الملف للحذف:", items, header="الملفات")


async def wa_del_select_file(phone, action):
    state = get_state(phone)
    try:
        index = int(action.split(":", 1)[1])
        file = state["pending_files"][index]
    except (ValueError, IndexError):
        send_text(phone, "قائمة منتهية الصلاحية. ابدأ من جديد.")
        reset_state(phone)
        return
    send_buttons(phone, f"حذف {file['name']}؟",
                 [("delfileconfirm:yes", "نعم احذف"), ("delfileconfirm:no", "إلغاء")])
    state["data"]["del_file_index"] = index
    state["state"] = "DEL_FILE_CONFIRM"


async def wa_del_file_confirm(phone, action):
    state = get_state(phone)
    if action == "delfileconfirm:no":
        send_text(phone, "تم الإلغاء.")
        reset_state(phone)
        return
    try:
        file = state["pending_files"][state["data"]["del_file_index"]]
        ok = await asyncio.to_thread(github_delete_file, file["path"], file["sha"], f"delete {file['name']}")
        send_text(phone, "تم الحذف ✅" if ok else "تعذر الحذف.")
    except Exception:
        logging.exception("Delete file failed")
        send_text(phone, "تعذر الحذف.")
    finally:
        reset_state(phone)


async def wa_del_whole_confirm(phone, action):
    state = get_state(phone)
    if action == "delwholeconfirm:no":
        send_text(phone, "تم الإلغاء.")
        reset_state(phone)
        return
    folder = state["data"].get("delete_whole_folder")
    if not folder:
        reset_state(phone)
        return
    files = await asyncio.to_thread(list_course_files_with_sha, folder)
    if files is None:
        # خطأ في الاتصال بخزن الملفات — لا نحذف مسجّل المادة حتى لا نفقد البيانات.
        send_text(phone, "تعذر الوصول إلى خزن ملفات المادة؛ لم يتم الحذف.")
        reset_state(phone)
        return
    results = []
    for f in files:
        try:
            results.append(
                await asyncio.to_thread(
                    github_delete_file, f["path"], f["sha"], f"delete {f['name']}"
                )
            )
        except Exception:
            logging.exception("Delete file failed for %s", f.get("path"))
            results.append(False)
    ok = all(results)
    if ok:
        await asyncio.to_thread(db.collection("courses").document(folder).delete)
        send_text(phone, "تم حذف المادة وكل الشيتات ✅")
    else:
        send_text(phone, "تعذر حذف بعض الملفات؛ لم تُحذف المادة من قاعدة البيانات.")
    reset_state(phone)


# ============================================================
# Upload processing
# ============================================================

async def wa_process_upload(phone, action):
    state = get_state(phone)
    up = state.get("upload_file")
    if not up:
        saved = get_pending_upload(phone)
        if saved:
            up = saved
        else:
            send_text(phone, "لم أجد الملف. أرسله مرة أخرى.")
            reset_state(phone)
            return
    send_text(phone, "جاري المعالجة…")
    try:
        file_data = up.get("data")
        mime = up.get("mime") or _guess_mime(up.get("name") or "")
        if not file_data:
            send_text(phone, "تعذر تحميل الملف. أرسلو مرة أخرى.")
            return
        base_action = action.removesuffix("_pdf")
        prompt = (
            "اكتشف لغة محتوى هذا الملف ثم ترجمه إلى اللغة المقابلة: إن كان بالعربية ترجمه إلى الإنجليزية، وإن كان بالإنجليزية ترجمه إلى العربية، مع الحفاظ على المعنى والمصطلحات."
            if base_action == "translate"
            else "لخص محتوى هذا الملف في نقاط واضحة ومرتبة. اكتب الملخص بنفس لغة الملف الأصلية."
        )
        part = types.Part.from_bytes(data=file_data, mime_type=mime)
        response = await call_gemini_with_retry(client.models.generate_content, model=MODEL_NAME, contents=[prompt, part])
        result_text = (response.text or "").strip()[:4000]
        if action.endswith("_pdf"):
            try:
                from utils.pdf_utils import text_to_pdf_bytes
                title = "ترجمة الملف" if base_action == "translate" else "ملخص الملف"
                pdf_buf = await asyncio.to_thread(text_to_pdf_bytes, result_text, title)
                pdf_bytes = pdf_buf.read() if hasattr(pdf_buf, "read") else pdf_buf
                media_id = await asyncio.to_thread(upload_media, pdf_bytes, "application/pdf", f"{title}.pdf")
                if media_id:
                    from whatsapp.api import send_document
                    send_document(phone, media_id, f"{title}.pdf")
                else:
                    send_text(phone, result_text)
            except Exception:
                logging.exception("PDF generation failed")
                send_text(phone, result_text)
        else:
            send_text(phone, result_text)
    except Exception:
        logging.exception("Upload processing failed")
        send_text(phone, "تعذرت معالجة الملف.")
    finally:
        clear_pending_upload(phone)
        reset_state(phone)


# ============================================================
# Voice
# ============================================================

async def handle_voice(phone, media_id):
    send_text(phone, "جاري معالجة الرسالة الصوتية…")
    try:
        data, mime = await asyncio.to_thread(download_media, media_id)
        if not data:
            send_text(phone, "تعذر تحميل الرسالة الصوتية.")
            return
        part = types.Part.from_bytes(data=data, mime_type=mime or "audio/ogg")
        response = await call_gemini_with_retry(
            client.models.generate_content, model=MODEL_NAME,
            contents=["استخرج النص المنطوق فقط.", part],
        )
        text = (response.text or "").strip()
        if text:
            await route_text(phone, text)
    except Exception:
        logging.exception("Voice processing failed")
        send_text(phone, "تعذرت معالجة الرسالة الصوتية.")


# ============================================================
# Routing
# ============================================================

async def handle_callback(phone, payload):
    if payload.startswith("waadm:"):
        if await asyncio.to_thread(wa_admin_callback, phone, payload):
            return
    if payload == "login":
        start_login(phone)
        return
    if payload == "guest":
        wa_show_guest_menu(phone)
        return
    if payload.startswith("menu:"):
        await wa_menu_action(phone, payload.removeprefix("menu:"))
        return
    if payload in ("admin:add", "admin:delete"):
        instructor_id, _ = await asyncio.to_thread(get_instructor_by_chat_id, "wa:" + phone)
        is_admin = await asyncio.to_thread(wa_is_admin, phone)
        if not (instructor_id or is_admin):
            send_text(phone, "هذه الخدمة لأعضاء هيئة التدريس أو الأدمن فقط.")
            return
        if payload == "admin:add":
            wa_add_content_start(phone, bool(is_admin and not instructor_id))
        else:
            await wa_delete_start(phone)
        return
    if payload.startswith("wmenu:"):
        await wa_welcome_menu_action(phone, payload.removeprefix("wmenu:"))
        return
    if payload.startswith("askcourse:"):
        await wa_ask_course_selected(phone, payload.removeprefix("askcourse:"))
        return
    if payload.startswith("sheet:"):
        await wa_sheets_for(phone, payload.removeprefix("sheet:"))
        return
    if payload.startswith("mycourse:"):
        await wa_my_course_selected(phone, payload.removeprefix("mycourse:"))
        return
    if payload.startswith("courseopt:"):
        await wa_course_option(phone, payload.removeprefix("courseopt:"))
        return
    if payload.startswith("file:"):
        state = get_state(phone)
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


async def route_text(phone, text, course_context=None):
    lang_cmd = parse_language_toggle(text)
    if lang_cmd:
        if lang_cmd == "show":
            send_text(phone, "اختر اللغة بكتابة English أو عربي\nChoose a language: type 'English' or 'عربي'")
        elif lang_cmd == "en":
            set_chat_language("wa:" + phone, "en")
            send_text(phone, "Done! I will now reply in English. Type 'عربي' anytime to switch back.")
        else:
            set_chat_language("wa:" + phone, "ar")
            send_text(phone, "تم! الآن سأرد عليك بالعربية. اكتب English في أي وقت للتبديل.")
        return

    _, student = await asyncio.to_thread(get_student_by_chat_id, "wa:" + phone)
    instructor_id, instructor = await asyncio.to_thread(get_instructor_by_chat_id, "wa:" + phone)
    is_admin = await asyncio.to_thread(wa_is_admin, phone)

    if text.strip().lower() in ("قائمة", "menu", "مساعدة", "help", "الخدمات"):
        wa_show_main_menu(phone)
        return
    if text.strip() in ("موادّي", "موادي", "my courses", "mycourses"):
        await wa_show_my_courses(phone)
        return

    # قوائم الترحيب المرقّمة (1 / 2 / 3) — تعمل فقط بعد إرسال القائمة فعلياً.
    state = get_state(phone)
    choice = text.strip()
    if choice in ("1", "2", "3") and time.time() - state.get("menu_shown_at", 0) < 3600:
        if instructor_id or (is_admin and not student):
            await wa_welcome_menu_action(phone, {"1": "courses", "2": "add", "3": "del"}[choice])
            return
        if student:
            await wa_welcome_menu_action(phone, {"1": "ask", "2": "course", "3": "my"}[choice])
            return

    if is_admin:
        t = text.strip().lower()
        if any(w in t for w in ("إدارة المحتوى", "لوحة الإدارة", "لوحة الادارة", "الأدمن", "الادمنية", "admin panel", "admin")):
            wa_admin_menu(phone)
            return
        if any(w in t for w in ("إضافة طالب", "اضافة طالب", "add student")):
            from whatsapp.admin_panel import wa_admin_add_prompt
            wa_admin_add_prompt(phone, "students")
            return
        if any(w in t for w in ("إضافة دكتور", "اضافة دكتور", "add instructor", "addinstructor")):
            from whatsapp.admin_panel import wa_admin_add_prompt
            wa_admin_add_prompt(phone, "instructors")
            return
        if any(w in t for w in ("إضافة مشرف", "اضافة مشرف", "add admin")):
            from whatsapp.admin_panel import wa_admin_add_prompt
            wa_admin_add_prompt(phone, "admins")
            return
        if any(w in t for w in ("عرض الطلاب", "قائمة الطلاب", "list students")):
            from whatsapp.admin_panel import wa_admin_list
            wa_admin_list(phone, "students")
            return
        if any(w in t for w in ("عرض الأساتذة", "عرض الاساتذة", "قائمة الأساتذة", "list instructors")):
            from whatsapp.admin_panel import wa_admin_list
            wa_admin_list(phone, "instructors")
            return
        if any(w in t for w in ("حذف طالب", "delete student")):
            from whatsapp.admin_panel import wa_admin_del_list
            wa_admin_del_list(phone, "students")
            return
        if any(w in t for w in ("حذف دكتور", "delete instructor")):
            from whatsapp.admin_panel import wa_admin_del_list
            wa_admin_del_list(phone, "instructors")
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
        courses = await _wa_available_courses(phone)
        items = [(f"sheet:{c.get('folder', '')}", (c.get("name") or "مادة")[:24], (c.get("folder") or "")[:72]) for c in courses[:100]]
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

    language = get_effective_language("wa:" + phone, text)
    prompt = text if not course_context else f"سؤال الطالب عن مادة «{course_context}»:\n{text}"
    answer = await generate_answer(prompt, "wa:" + phone, instructor_data=instructor, language=language)
    send_text(phone, answer)


# ============================================================
# Process WhatsApp message
# ============================================================

async def process_wa_message(phone, msg):
    state = get_state(phone)
    logging.info("WA process: phone=%s type=%s state=%s", phone, msg.get("type"), state.get("state"))

    if not state.get("welcome_sent") and not was_welcome_sent(phone):
        state["welcome_sent"] = True
        mark_welcome_sent(phone)
        wa_show_welcome(phone)
        return

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
        file_data, file_mime = await asyncio.to_thread(download_media, media_id)
        if not file_data:
            send_text(phone, "تعذر تحميل الملف. أرسلو مرة أخرى.")
            return
        state["upload_file"] = {
            "data": file_data,
            "mime": file_mime or _guess_mime(meta.get("filename") or ""),
            "name": meta.get("filename") or meta.get("caption") or "ملف",
        }
        state["state"] = "UPLOAD_ASK_ACTION"
        save_pending_upload(phone, file_data, meta.get("filename") or meta.get("caption") or "ملف", file_mime or _guess_mime(meta.get("filename") or ""))
        send_list(phone, "استلمت الملف ✅ ماذا تريد أن أفعل به؟", [
            ("uploadact:summarize", "تلخيص كنص", "ملخص نصي بالعربي"),
            ("uploadact:summarize_pdf", "تلخيص كـ PDF", "تحميل ملف PDF"),
            ("uploadact:translate", "ترجمة كنص", "ترجمة تلقائية"),
            ("uploadact:translate_pdf", "ترجمة كـ PDF", "تحميل ملف PDF"),
        ])
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
    if current == "ASK_COURSE":
        course_name = (state.get("data") or {}).get("ask_course_name") or ""
        reset_state(phone)
        await route_text(phone, text, course_context=course_name)
        return
    if current == "ADD_NEW_NAME":
        await wa_add_new_name(phone, text)
        return
    if current == "UPLOAD_ASK_ACTION":
        t = text.lower()
        if any(w in t for w in ("تلخيص pdf", "تلخيص بي دي اف", "ملخص pdf", "summarize pdf", "summary pdf", "summarize as pdf")):
            await wa_process_upload(phone, "summarize_pdf")
        elif any(w in t for w in ("ترجمة pdf", "ترجمة بي دي اف", "ترجمة ملف", "translate pdf", "translate as pdf")):
            await wa_process_upload(phone, "translate_pdf")
        elif any(w in t for w in ("لخص", "لخّص", "تلخيص كنص", "summarize", "summarise", "summary")):
            await wa_process_upload(phone, "summarize")
        elif any(w in t for w in ("ترجمة كنص", "ترجم كنص", "translate")):
            await wa_process_upload(phone, "translate")
        else:
            send_text(phone, "استخدم الأزرار أو اكتب: لخص / ترجم")
        return
    if current in ("ADD_MENU", "ADD_SELECT_COURSE", "ADD_NEW_CONFIRM", "ADD_WAIT_FILE",
                    "DEL_MENU", "DEL_SELECT_COURSE", "DEL_SELECT_FILE", "DEL_FILE_CONFIRM", "DEL_WHOLE_CONFIRM"):
        send_text(phone, "استخدم الأزرار أعلاه للمتابعة.")
        return

    if current and current.startswith("WAADMIN_ADD_"):
        section = current.replace("WAADMIN_ADD_", "").lower()
        wa_admin_add_execute(phone, section, text)
        return

    await route_text(phone, text)
