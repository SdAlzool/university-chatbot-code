"""تيليجرام: صلاحيات الأدمن + إدارة الطلاب/الدكاترة + لوحة التحكم."""

import asyncio
import logging
import re

from firebase_admin import firestore
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import ADMIN_TELEGRAM_IDS, ADMIN_WHATSAPP_NUMBERS
from services.firebase_db import db
from services.github_tools import list_repository_folders


# ============================================================
# من الملف الأصلي: handlers/admin.py
# ============================================================


def is_bootstrap_admin(user_id):
    return user_id in ADMIN_TELEGRAM_IDS


def is_stored_admin(user_id):
    return db.collection("admins").document(str(user_id)).get().exists


async def user_is_admin(update: Update):
    user = update.effective_user
    if not user:
        message = update.effective_message
        if message and message.from_user:
            user = message.from_user
    if not user:
        return False
    if is_bootstrap_admin(user.id):
        return True
    if str(user.id) in ADMIN_WHATSAPP_NUMBERS:
        return True
    return await asyncio.to_thread(is_stored_admin, user.id)


async def require_admin(update: Update):
    if await user_is_admin(update):
        return True
    message = update.effective_message
    if message:
        await message.reply_text("ليس لديك صلاحية إدارة المشروع.")
    return False


async def show_my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        f"Telegram User ID الخاص بك: {update.effective_user.id}"
    )


async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    counts = await asyncio.gather(
        asyncio.to_thread(lambda: len(list(db.collection("students").stream()))),
        asyncio.to_thread(lambda: len(list(db.collection("instructors").stream()))),
        asyncio.to_thread(lambda: len(list(db.collection("courses").stream()))),
        asyncio.to_thread(lambda: len(list(db.collection("admins").stream()))),
        asyncio.to_thread(list_repository_folders),
    )
    bootstrap_count = len(ADMIN_TELEGRAM_IDS)
    github_course_count = "غير متاح" if counts[4] is None else str(len(counts[4]))
    await update.effective_message.reply_text(
        "لوحة إدارة المشروع\n\n"
        f"الطلاب: {counts[0]}\n"
        f"أعضاء هيئة التدريس: {counts[1]}\n"
        f"المقررات في Firestore: {counts[2]}\n"
        f"مجلدات المقررات في GitHub: {github_course_count}\n"
        f"المشرفون المضافون: {counts[3]}\n"
        f"المشرفون الأساسيون (.env): {bootstrap_count}\n\n"
        "─── أوامر عرض ───\n"
        "/students - عرض جميع الطلاب\n"
        "/instructors - عرض جميع الأساتذة\n"
        "/admins - عرض جميع المشرفين\n\n"
        "─── إضافة ───\n"
        "/addstudent <id> <email> <name> - إضافة طالب\n"
        "مثال: /addstudent 123456789 ali@uni.edu.sd علي أحمد\n\n"
        "/addinstructor <id> <email> <name> - إضافة أستاذ\n"
        "مثال: /addinstructor 987654321 omar@uni.edu.sd عمر محمد\n\n"
        "/addadmin <Telegram_User_ID> - إضافة مشرف\n"
        "مثال: /addadmin 123456789\n\n"
        "─── تعديل ───\n"
        "/editstudent <id> <field> <value> - تعديل بيانات طالب\n"
        "مثال: /editstudent 123456789 name علي الجديد\n\n"
        "/editinstructor <id> <field> <value> - تعديل بيانات أستاذ\n"
        "مثال: /editinstructor 987654321 email new@uni.edu.sd\n\n"
        "─── حذف ───\n"
        "/deletestudent <id> - حذف طالب\n"
        "مثال: /deletestudent 123456789\n\n"
        "/deleteinstructor <id> - حذف أستاذ\n"
        "مثال: /deleteinstructor 987654321\n\n"
        "/removeadmin <Telegram_User_ID> - إزالة مشرف\n"
        "مثال: /removeadmin 123456789"
    )


async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    stored_admins = await asyncio.to_thread(lambda: list(db.collection("admins").stream()))
    lines = ["المشرفون الأساسيون:"]
    lines.extend(f"- {user_id}" for user_id in sorted(ADMIN_TELEGRAM_IDS))
    lines.append("\nالمشرفون المضافون:")
    if stored_admins:
        for admin in stored_admins:
            data = admin.to_dict()
            label = data.get("name") or admin.id
            lines.append(f"- {label} ({admin.id})")
    else:
        lines.append("- لا يوجد")
    await update.effective_message.reply_text("\n".join(lines))


async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.effective_message.reply_text(
            "الصيغة: /addadmin <Telegram_User_ID>\n"
            "مثال: /addadmin 123456789"
        )
        return
    await add_admin_by_id(update, int(context.args[0]))


async def add_admin_by_id(update: Update, admin_id: int):
    actor = update.effective_user
    await asyncio.to_thread(
        db.collection("admins").document(str(admin_id)).set,
        {
            "added_by": actor.id,
            "added_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    await update.effective_message.reply_text(f"تمت إضافة المشرف: {admin_id}")


async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.effective_message.reply_text(
            "الصيغة: /removeadmin <Telegram_User_ID>\n"
            "مثال: /removeadmin 123456789"
        )
        return
    await remove_admin_by_id(update, int(context.args[0]))


async def remove_admin_by_id(update: Update, admin_id: int):
    if is_bootstrap_admin(admin_id):
        await update.effective_message.reply_text(
            "لا يمكن إزالة مشرف أساسي من البوت. أزله من ADMIN_TELEGRAM_IDS في .env ثم أعد تشغيل البوت."
        )
        return
    admin_ref = db.collection("admins").document(str(admin_id))
    exists = await asyncio.to_thread(lambda: admin_ref.get().exists)
    if not exists:
        await update.effective_message.reply_text("هذا المستخدم ليس مشرفًا مضافًا.")
        return
    await asyncio.to_thread(admin_ref.delete)
    await update.effective_message.reply_text(f"تمت إزالة المشرف: {admin_id}")


async def _list_people(update: Update, collection_name: str, title: str):
    if not await require_admin(update):
        return
    documents = await asyncio.to_thread(
        lambda: list(db.collection(collection_name).limit(30).stream())
    )
    if not documents:
        await update.effective_message.reply_text(f"لا يوجد {title} مسجلون.")
        return
    lines = [f"{title} (أول {len(documents)}):"]
    buttons = []
    for document in documents:
        data = document.to_dict()
        name = data.get("name", "بدون اسم")
        lines.append(f"- {document.id}: {name} | {data.get('email', 'بدون بريد')}")
        callback_data = f"person:{collection_name}:{document.id}"
        if len(callback_data) <= 64:
            buttons.append([InlineKeyboardButton(f"👤 {name}", callback_data=callback_data)])
    await update.effective_message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
    )


async def list_students(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _list_people(update, "students", "الطلاب")


async def list_instructors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _list_people(update, "instructors", "الأساتذة")


async def list_all_people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    await _list_people(update, "students", "الطلاب")
    await _list_people(update, "instructors", "الأساتذة")


async def _edit_person(update: Update, context: ContextTypes.DEFAULT_TYPE, collection_name: str, label: str):
    if not await require_admin(update):
        return
    if len(context.args) < 3:
        await update.effective_message.reply_text(
            f"الصيغة: /edit{label} <المعرف> <اسم الحقل> <القيمة>\n"
            f"مثال: /edit{label} 123456789 name الاسم الجديد\n"
            f"الحقول المسموحة: name, email"
        )
        return
    person_id, field = context.args[:2]
    value = " ".join(context.args[2:]).strip()
    if field not in {"name", "email"}:
        await update.effective_message.reply_text("الحقول المسموحة للتعديل هي: name و email فقط.")
        return
    reference = db.collection(collection_name).document(person_id)
    exists = await asyncio.to_thread(lambda: reference.get().exists)
    if not exists:
        await update.effective_message.reply_text(f"هذا {label} غير موجود.")
        return
    await asyncio.to_thread(reference.update, {field: value})
    await update.effective_message.reply_text(f"تم تعديل {field} لـ {label} {person_id}.")


async def edit_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _edit_person(update, context, "students", "student")


async def edit_instructor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _edit_person(update, context, "instructors", "instructor")


async def _add_person(update: Update, context: ContextTypes.DEFAULT_TYPE, collection_name: str, label: str):
    if not await require_admin(update):
        return
    if len(context.args) < 3:
        await update.effective_message.reply_text(
            f"الصيغة: /add{label} <المعرف> <البريد الإلكتروني> <الاسم>\n"
            f"مثال: /add{label} 123456789 name@uni.edu.sd الاسم الكامل"
        )
        return
    person_id, email = context.args[:2]
    name = " ".join(context.args[2:]).strip()
    reference = db.collection(collection_name).document(person_id)
    if await asyncio.to_thread(lambda: reference.get().exists):
        await update.effective_message.reply_text(f"هذا {label} موجود بالفعل. استخدم أمر التعديل بدلًا من ذلك.")
        return
    data = {
        "name": name,
        "email": email,
        "chat_id": None,
        "last_active": None,
        "created_by": update.effective_user.id,
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    if collection_name == "instructors":
        data["courses"] = []
    await asyncio.to_thread(reference.set, data)
    await update.effective_message.reply_text(f"تمت إضافة {label} {name} بنجاح.")


async def add_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _add_person(update, context, "students", "student")


async def add_instructor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _add_person(update, context, "instructors", "instructor")


async def _delete_person(update: Update, context: ContextTypes.DEFAULT_TYPE, collection_name: str, label: str):
    if not await require_admin(update):
        return
    if len(context.args) != 1:
        await update.effective_message.reply_text(
            f"الصيغة: /delete{label} <المعرف>\n"
            f"مثال: /delete{label} 123456789"
        )
        return
    reference = db.collection(collection_name).document(context.args[0])
    exists = await asyncio.to_thread(lambda: reference.get().exists)
    if not exists:
        await update.effective_message.reply_text(f"هذا {label} غير موجود.")
        return
    await asyncio.to_thread(reference.delete)
    await update.effective_message.reply_text(f"تم حذف {label} {context.args[0]}.")


async def delete_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _delete_person(update, context, "students", "student")


async def delete_instructor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _delete_person(update, context, "instructors", "instructor")


async def add_person_by_text(update: Update, collection_name: str, label: str, person_id: str, email: str, name: str):
    if not await require_admin(update):
        return
    reference = db.collection(collection_name).document(person_id)
    if await asyncio.to_thread(lambda: reference.get().exists):
        await update.effective_message.reply_text(f"هذا {label} موجود بالفعل. استخدم أمر التعديل بدلاً من ذلك.")
        return
    data = {
        "name": name,
        "email": email,
        "chat_id": None,
        "last_active": None,
        "created_by": update.effective_user.id,
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    if collection_name == "instructors":
        data["courses"] = []
    await asyncio.to_thread(reference.set, data)
    await update.effective_message.reply_text(f"تمت إضافة {label} {name} بنجاح.")


async def edit_person_by_text(update: Update, collection_name: str, label: str, person_id: str, text: str):
    if not await require_admin(update):
        return
    match = re.search(r"\b(name|email)\s*(?:=|:)\s*(.+)$", text, re.IGNORECASE)
    if match:
        field, value = match.group(1).lower(), match.group(2).strip()
    else:
        parts = text.split(maxsplit=3)
        if len(parts) < 4 or parts[2].lower() not in {"name", "email"}:
            await update.effective_message.reply_text(
                f"الصيغة: عدّل {label} <المعرف> <name|email> <القيمة>\n"
                f"مثال: عدّل {label} {person_id} name الاسم الجديد"
            )
            return
        field, value = parts[2].lower(), parts[3].strip()
    if not value:
        await update.effective_message.reply_text("القيمة الجديدة لا يمكن أن تكون فارغة.")
        return
    reference = db.collection(collection_name).document(person_id)
    if not await asyncio.to_thread(lambda: reference.get().exists):
        await update.effective_message.reply_text(f"هذا {label} غير موجود.")
        return
    await asyncio.to_thread(reference.update, {field: value})
    await update.effective_message.reply_text(f"تم تعديل {field} لـ {label} {person_id}.")


async def delete_person_by_text(update: Update, collection_name: str, label: str, person_id: str):
    if not await require_admin(update):
        return
    reference = db.collection(collection_name).document(person_id)
    if not await asyncio.to_thread(lambda: reference.get().exists):
        await update.effective_message.reply_text(f"هذا {label} غير موجود.")
        return
    await asyncio.to_thread(reference.delete)
    await update.effective_message.reply_text(f"تم حذف {label} {person_id}.")


async def handle_person_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    query = update.callback_query
    await query.answer()
    try:
        _, collection_name, person_id = query.data.split(":", 2)
    except ValueError:
        return
    if collection_name not in {"students", "instructors"}:
        return
    document = await asyncio.to_thread(db.collection(collection_name).document(person_id).get)
    if not document.exists:
        await query.message.reply_text("هذا الحساب لم يعد موجودًا.")
        return
    data = document.to_dict()
    label = "طالب" if collection_name == "students" else "أستاذ"
    confirm_data = f"persondel:{collection_name}:{person_id}:yes"
    cancel_data = f"persondel:{collection_name}:{person_id}:no"
    buttons = [[
        InlineKeyboardButton("🗑 حذف", callback_data=confirm_data),
        InlineKeyboardButton("إلغاء", callback_data=cancel_data),
    ]]
    await query.message.reply_text(
        f"{label}: {data.get('name', 'بدون اسم')}\n"
        f"المعرف: {person_id}\n"
        f"البريد: {data.get('email', 'بدون بريد')}\n\n"
        "هل تريد حذف هذا الحساب نهائيًا؟",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def handle_person_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    query = update.callback_query
    await query.answer()
    try:
        _, collection_name, person_id, choice = query.data.split(":", 3)
    except ValueError:
        return
    if choice == "no":
        await query.message.reply_text("تم إلغاء الحذف.")
        return
    if collection_name not in {"students", "instructors"}:
        return
    reference = db.collection(collection_name).document(person_id)
    if not await asyncio.to_thread(lambda: reference.get().exists):
        await query.message.reply_text("هذا الحساب غير موجود.")
        return
    await asyncio.to_thread(reference.delete)
    await query.message.reply_text("تم حذف الحساب بنجاح.")


# ============================================================
# من الملف الأصلي: handlers/admin_panel.py
# ============================================================


def _get_stats():
    try:
        students = len(list(db.collection("students").stream()))
    except Exception:
        students = 0
    try:
        instructors = len(list(db.collection("instructors").stream()))
    except Exception:
        instructors = 0
    try:
        admins = len(list(db.collection("admins").stream()))
    except Exception:
        admins = 0
    try:
        courses = len(list(db.collection("courses").stream()))
    except Exception:
        courses = 0
    return students, instructors, admins, courses


def _main_menu_kb(students, instructors, admins, courses):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"👥 إدارة الطلاب ({students})", callback_data="ap:sec:students")],
        [InlineKeyboardButton(f"👨‍🏫 إدارة الأساتذة ({instructors})", callback_data="ap:sec:instructors")],
        [InlineKeyboardButton(f"🛡️ إدارة الأدمنية ({admins})", callback_data="ap:sec:admins")],
        [InlineKeyboardButton(f"📚 إدارة المواد ({courses})", callback_data="ap:sec:courses")],
    ])


def _sector_kb(section):
    labels = {
        "students": "الطلاب",
        "instructors": "الأساتذة",
        "admins": "الأدمنية",
        "courses": "المواد",
    }
    label = labels.get(section, section)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"📋 عرض {label}", callback_data=f"ap:list:{section}"),
            InlineKeyboardButton(f"➕ إضافة {label[:-1] if label.endswith('ة') else label}", callback_data=f"ap:add:{section}"),
        ],
        [
            InlineKeyboardButton("✏️ تعديل", callback_data=f"ap:edit:{section}"),
            InlineKeyboardButton("🗑️ حذف", callback_data=f"ap:del:{section}"),
        ],
        [InlineKeyboardButton("🔙 رجوع للوحة الرئيسية", callback_data="ap:home")],
    ])


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await user_is_admin(update):
        await update.message.reply_text("⛔ ليس لديك صلاحية الوصول لهذه اللوحة.")
        return
    students, instructors, admins, courses = await asyncio.to_thread(_get_stats)
    text = (
        "🛡️ **لوحة إدارة النظام**\n\n"
        f"👥 الطلاب: {students}\n"
        f"👨‍🏫 الأساتذة: {instructors}\n"
        f"🛡️ المشرفين: {admins}\n"
        f"📚 المواد: {courses}\n\n"
        "اختر القسم المطلوب:"
    )
    await update.message.reply_text(
        text,
        reply_markup=_main_menu_kb(students, instructors, admins, courses),
        parse_mode="Markdown",
    )


async def _admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await user_is_admin(update):
        await query.edit_message_text("⛔ ليس لديك صلاحية.")
        return
    data = query.data
    parts = data.split(":")
    if data == "ap:home":
        await _show_home(query)
        return
    if len(parts) == 3 and parts[1] == "sec":
        section = parts[2]
        labels = {"students": "الطلاب", "instructors": "الأساتذة", "admins": "الأدمنية", "courses": "المواد"}
        label = labels.get(section, section)
        await query.edit_message_text(
            f"📂 قسم {label}\n\nاختر الإجراء المطلوب:",
            reply_markup=_sector_kb(section),
        )
        return
    if len(parts) == 3 and parts[1] == "list":
        await _handle_list(query, parts[2])
        return
    if len(parts) == 3 and parts[1] == "add":
        await _handle_add_prompt(query, parts[2])
        return
    if len(parts) == 3 and parts[1] == "edit":
        await _handle_edit_prompt(query, parts[2])
        return
    if len(parts) == 3 and parts[1] == "del":
        await _handle_del_list(query, parts[2])
        return
    if len(parts) == 4 and parts[1] == "confirm_del":
        await _handle_confirm_del(query, parts[2], parts[3])
        return
    if len(parts) == 4 and parts[1] == "view":
        await _handle_view_person(query, parts[2], parts[3])
        return
    if len(parts) == 4 and parts[1] == "editperson":
        await query.edit_message_text(
            f"أرسل الآن: عدّل {parts[2]} {parts[3]} name القيمة الجديدة\n"
            "أو استخدم email بدل name."
        )
        return
    if len(parts) == 3 and parts[1] == "assigncourse":
        await _handle_assign_course(query, parts[2])
        return
    if len(parts) == 4 and parts[1] == "togglecourse":
        await _handle_toggle_course(query, parts[2], parts[3])
        return


async def _show_home(query):
    students, instructors, admins, courses = await asyncio.to_thread(_get_stats)
    text = (
        "🛡️ **لوحة إدارة النظام**\n\n"
        f"👥 الطلاب: {students}\n"
        f"👨‍🏫 الأساتذة: {instructors}\n"
        f"🛡️ المشرفين: {admins}\n"
        f"📚 المواد: {courses}\n\n"
        "اختر القسم المطلوب:"
    )
    await query.edit_message_text(
        text,
        reply_markup=_main_menu_kb(students, instructors, admins, courses),
        parse_mode="Markdown",
    )


async def _handle_list(query, section):
    collection_map = {
        "students": ("students", "الطالب", "👤"),
        "instructors": ("instructors", "الدكتور", "👨‍🏫"),
        "admins": ("admins", "المشرف", "🛡️"),
        "courses": ("courses", "المادة", "📚"),
    }
    if section not in collection_map:
        return
    coll, label, icon = collection_map[section]
    try:
        docs = await asyncio.to_thread(lambda: list(db.collection(coll).stream()))
    except Exception:
        docs = []
    if not docs:
        await query.edit_message_text(
            f"📋 لا يوجد {label} مسجلين.",
            reply_markup=_sector_kb(section),
        )
        return
    lines = [f"📋 **قائمة {label}** ({len(docs)}):\n"]
    for doc in docs[:30]:
        data = doc.to_dict() or {}
        name = data.get("name", doc.id)
        lines.append(f"{icon} `{doc.id}` — {name}")
    text = "\n".join(lines)
    buttons = []
    for doc in docs[:30]:
        buttons.append([
            InlineKeyboardButton(
                f"👁️ تفاصيل {doc.to_dict().get('name', doc.id)}",
                callback_data=f"ap:view:{section}:{doc.id}",
            )
        ])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"ap:sec:{section}")])
    kb = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")


async def _handle_add_prompt(query, section):
    prompts = {
        "students": (
            "➕ **إضافة طالب**\n\n"
            "أرسل الرسالة بالتنسيق التالي:\n"
            "`أضف طالب 123456789 email@example.com اسم الطالب`"
        ),
        "instructors": (
            "➕ **إضافة دكتور**\n\n"
            "أرسل الرسالة بالتنسيق التالي:\n"
            "`أضف دكتور 987654321 email@example.com اسم الدكتور`"
        ),
        "admins": (
            "➕ **إضافة مشرف**\n\n"
            "أرسل معرف المستخدم (Telegram ID أو رقم الواتساب):\n"
            "`أضف مشرف 123456789`"
        ),
        "courses": (
            "➕ **إضافة مادة**\n\n"
            "أرسل اسم المادة وسيتم إنشاؤها تلقائياً:\n"
            "`إضافة مادة التحليل الرياضي`"
        ),
    }
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 رجوع", callback_data=f"ap:sec:{section}")],
    ])
    await query.edit_message_text(
        prompts.get(section, "تنسيق غير معروف"),
        reply_markup=kb,
        parse_mode="Markdown",
    )


async def _handle_edit_prompt(query, section):
    prompts = {
        "students": (
            "✏️ **تعديل طالب**\n\n"
            "أرسل:\n"
            "`تعديل طالب 123456789 حقل=قيمة`\n\n"
            "الحقول المسموحة: name, email"
        ),
        "instructors": (
            "✏️ **تعديل دكتور**\n\n"
            "أرسل:\n"
            "`تعديل دكتور 987654321 حقل=قيمة`\n\n"
            "الحقول المسموحة: name, email"
        ),
        "admins": "✏️ تعديل الأدمنية — يتم عبر حذف وإعادة إضافة.",
        "courses": "✏️ تعديل المواد — يتم عبر حذف وإعادة إضافة.",
    }
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 رجوع", callback_data=f"ap:sec:{section}")],
    ])
    await query.edit_message_text(
        prompts.get(section, "تنسيق غير معروف"),
        reply_markup=kb,
        parse_mode="Markdown",
    )


async def _handle_del_list(query, section):
    collection_map = {
        "students": ("students", "الطالب", "👤"),
        "instructors": ("instructors", "الدكتور", "👨‍🏫"),
        "admins": ("admins", "المشرف", "🛡️"),
    }
    if section not in collection_map:
        await query.edit_message_text(
            "🗑️ حذف المواد يتم عبر حذف الملفات.",
            reply_markup=_sector_kb(section),
        )
        return
    coll, label, icon = collection_map[section]
    try:
        docs = await asyncio.to_thread(lambda: list(db.collection(coll).stream()))
    except Exception:
        docs = []
    if not docs:
        await query.edit_message_text(
            f"📋 لا يوجد {label} لحذفهم.",
            reply_markup=_sector_kb(section),
        )
        return
    buttons = []
    for doc in docs[:8]:
        data = doc.to_dict() or {}
        name = data.get("name", doc.id)
        buttons.append([
            InlineKeyboardButton(
                f"🗑️ {icon} {name} ({doc.id})",
                callback_data=f"ap:confirm_del:{section}:{doc.id}",
            )
        ])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"ap:sec:{section}")])
    await query.edit_message_text(
        f"🗑️ اختر {label} للحذف:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def _handle_confirm_del(query, section, person_id):
    collection_map = {
        "students": "students",
        "instructors": "instructors",
        "admins": "admins",
    }
    if section not in collection_map:
        return
    coll = collection_map[section]
    if section == "admins" and is_bootstrap_admin(int(person_id) if person_id.isdigit() else 0):
        await query.edit_message_text(
            "⛔ لا يمكن حذف المشرف الأساسي.",
            reply_markup=_sector_kb(section),
        )
        return
    try:
        await asyncio.to_thread(db.collection(coll).document(person_id).delete)
        await query.edit_message_text(
            f"✅ تم حذف المستند `{person_id}` من {coll}.",
            reply_markup=_sector_kb(section),
            parse_mode="Markdown",
        )
    except Exception as e:
        logging.exception("Delete failed")
        await query.edit_message_text(
            f"❌ فشل الحذف: {e}",
            reply_markup=_sector_kb(section),
        )


async def _handle_view_person(query, section, person_id):
    collection_map = {
        "students": ("students", "الطالب"),
        "instructors": ("instructors", "الدكتور"),
        "admins": ("admins", "المشرف"),
    }
    if section not in collection_map:
        return
    coll, label = collection_map[section]
    try:
        doc = await asyncio.to_thread(db.collection(coll).document(person_id).get)
    except Exception:
        doc = None
    if not doc or not doc.exists:
        await query.edit_message_text(
            f"❌ المستند `{person_id}` غير موجود.",
            reply_markup=_sector_kb(section),
            parse_mode="Markdown",
        )
        return
    data = doc.to_dict() or {}
    lines = [f"👤 **بيانات {label}**\n"]
    for k, v in data.items():
        lines.append(f"• **{k}**: `{v}`")
    buttons = [
        [
            InlineKeyboardButton("✏️ تعديل بالرسالة", callback_data=f"ap:editperson:{section}:{person_id}"),
            InlineKeyboardButton("🗑️ حذف", callback_data=f"ap:confirm_del:{section}:{person_id}"),
        ],
    ]
    if section == "students":
        buttons.append([
            InlineKeyboardButton("📚 تعيين مواد", callback_data=f"ap:assigncourse:{person_id}"),
        ])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"ap:sec:{section}")])
    kb = InlineKeyboardMarkup(buttons)
    await query.edit_message_text("\n".join(lines), reply_markup=kb, parse_mode="Markdown")


async def _handle_assign_course(query, student_id):
    def _load():
        docs = list(db.collection("courses").stream())
        courses = [doc.to_dict() for doc in docs]
        student_doc = db.collection("students").document(student_id).get()
        return courses, (student_doc.to_dict() if student_doc.exists else {})

    courses, student_data = await asyncio.to_thread(_load)
    if not courses:
        await query.edit_message_text(
            "❌ لا توجد مواد متاحة. أضف مواد أولاً.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=f"ap:view:students:{student_id}")]]),
        )
        return
    assigned_courses = student_data.get("courses") or []
    lines = [f"📚 **مواد الطالب {student_id}**\n"]
    lines.append(f"المواد الحالية: {', '.join(assigned_courses) if assigned_courses else 'لا توجد مواد'}\n")
    lines.append("اختر المادة لتعيينها أو إزالتها:")
    buttons = []
    for course in courses[:20]:
        folder = course.get("folder", "")
        name = course.get("name", folder)
        status = "✅" if folder in assigned_courses else "⬜"
        buttons.append([
            InlineKeyboardButton(
                f"{status} {name}",
                callback_data=f"ap:togglecourse:{student_id}:{folder}",
            )
        ])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"ap:view:students:{student_id}")])
    kb = InlineKeyboardMarkup(buttons)
    await query.edit_message_text("\n".join(lines), reply_markup=kb, parse_mode="Markdown")


async def _handle_toggle_course(query, student_id, course_folder):
    from firebase_admin import firestore

    def _toggle():
        student_doc = db.collection("students").document(student_id).get()
        student_data = student_doc.to_dict() if student_doc.exists else {}
        assigned = student_data.get("courses") or []
        ref = db.collection("students").document(student_id)
        if course_folder in assigned:
            ref.update({"courses": firestore.ArrayRemove([course_folder])})
        else:
            ref.update({"courses": firestore.ArrayUnion([course_folder])})

    await asyncio.to_thread(_toggle)
    await _handle_assign_course(query, student_id)
