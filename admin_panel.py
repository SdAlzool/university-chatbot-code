"""Interactive Admin Panel — Telegram (Inline Keyboards + Sub-menus)."""

import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from config import db
from handlers.admin import (
    is_bootstrap_admin, is_stored_admin, user_is_admin,
    add_admin_by_id, remove_admin_by_id,
    add_person_by_text, delete_person_by_text, edit_person_by_text,
)

# ============================================================
# Statistics
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


# ============================================================
# Keyboards
# ============================================================

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
            InlineKeyboardButton(f"✏️ تعديل", callback_data=f"ap:edit:{section}"),
            InlineKeyboardButton(f"🗑️ حذف", callback_data=f"ap:del:{section}"),
        ],
        [InlineKeyboardButton("🔙 رجوع للوحة الرئيسية", callback_data="ap:home")],
    ])


def _confirm_delete_kb(section, person_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ نعم احذف", callback_data=f"ap:confirm_del:{section}:{person_id}"),
            InlineKeyboardButton("❌ إلغاء", callback_data=f"ap:sec:{section}"),
        ],
    ])


# ============================================================
# Main entry: /admin command
# ============================================================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: /admin — show dashboard with stats."""
    if not user_is_admin(update):
        await update.message.reply_text("⛔ ليس لديك صلاحية الوصول لهذه اللوحة.")
        return

    students, instructors, admins, courses = _get_stats()
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


# ============================================================
# Callback Router
# ============================================================

async def _admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all ap:* callbacks."""
    query = update.callback_query
    await query.answer()

    if not user_is_admin(update):
        await query.edit_message_text("⛔ ليس لديك صلاحية.")
        return

    data = query.data
    parts = data.split(":")

    # ap:home
    if data == "ap:home":
        await _show_home(query)
        return

    # ap:sec:<section>  →  show sector menu
    if len(parts) == 3 and parts[1] == "sec":
        section = parts[2]
        labels = {"students": "الطلاب", "instructors": "الأساتذة", "admins": "الأدمنية", "courses": "المواد"}
        label = labels.get(section, section)
        await query.edit_message_text(
            f"📂 قسم {label}\n\nاختر الإجراء المطلوب:",
            reply_markup=_sector_kb(section),
        )
        return

    # ap:list:<section>  →  list people
    if len(parts) == 3 and parts[1] == "list":
        await _handle_list(query, parts[2])
        return

    # ap:add:<section>  →  prompt for add
    if len(parts) == 3 and parts[1] == "add":
        await _handle_add_prompt(query, parts[2])
        return

    # ap:edit:<section>  →  prompt for edit
    if len(parts) == 3 and parts[1] == "edit":
        await _handle_edit_prompt(query, parts[2])
        return

    # ap:del:<section>  →  list for deletion
    if len(parts) == 3 and parts[1] == "del":
        await _handle_del_list(query, parts[2])
        return

    # ap:confirm_del:<section>:<id>  →  confirm and delete
    if len(parts) == 4 and parts[1] == "confirm_del":
        await _handle_confirm_del(query, parts[2], parts[3])
        return

    # ap:view:<section>:<id>  →  view person details
    if len(parts) == 4 and parts[1] == "view":
        await _handle_view_person(query, parts[2], parts[3])
        return


# ============================================================
# Handlers
# ============================================================

async def _show_home(query):
    students, instructors, admins, courses = _get_stats()
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
    """List all documents in a collection."""
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
        docs = list(db.collection(coll).stream())
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
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 رجوع", callback_data=f"ap:sec:{section}")],
    ])
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")


async def _handle_add_prompt(query, section):
    """Show instructions for adding a person via text."""
    prompts = {
        "students": (
            "➕ **إضافة طالب**\n\n"
            "أرسل الرسالة بالتنسيق التالي:\n"
            "`123456789 email@example.com اسم الطالب`"
        ),
        "instructors": (
            "➕ **إضافة دكتور**\n\n"
            "أرسل الرسالة بالتنسيق التالي:\n"
            "`987654321 email@example.com اسم الدكتور`"
        ),
        "admins": (
            "➕ **إضافة مشرف**\n\n"
            "أرسل معرف المستخدم (Telegram ID أو رقم الواتساب):\n"
            "`123456789`"
        ),
        "courses": (
            "➕ **إضافة مادة**\n\n"
            "أرسل اسم المادة وسيتم إنشاؤها تلقائياً."
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
    """Show instructions for editing via text."""
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
    """List people with delete buttons."""
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
        docs = list(db.collection(coll).stream())
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
    """Delete a person after confirmation."""
    collection_map = {
        "students": "students",
        "instructors": "instructors",
        "admins": "admins",
    }
    if section not in collection_map:
        return

    coll = collection_map[section]

    # Prevent deleting bootstrap admins
    if section == "admins" and is_bootstrap_admin(int(person_id) if person_id.isdigit() else 0):
        await query.edit_message_text(
            "⛔ لا يمكن حذف المشرف الأساسي.",
            reply_markup=_sector_kb(section),
        )
        return

    try:
        db.collection(coll).document(person_id).delete()
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
    """View a single person's details."""
    collection_map = {
        "students": ("students", "الطالب"),
        "instructors": ("instructors", "الدكتور"),
        "admins": ("admins", "المشرف"),
    }
    if section not in collection_map:
        return

    coll, label = collection_map[section]
    try:
        doc = db.collection(coll).document(person_id).get()
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

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗑️ حذف", callback_data=f"ap:confirm_del:{section}:{person_id}"),
            InlineKeyboardButton("🔙 رجوع", callback_data=f"ap:sec:{section}"),
        ],
    ])
    await query.edit_message_text("\n".join(lines), reply_markup=kb, parse_mode="Markdown")


# ============================================================
# Text message handler (for add/edit via text)
# ============================================================

async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle text messages from admins when in 'add' or 'edit' mode.
    This is registered as a MessageHandler in main.py.
    """
    if not user_is_admin(update):
        return False  # not handled

    text = update.message.text.strip()

    # Try NLP-based admin command first
    from handlers.general import _handle_admin_command
    if await _handle_admin_command(update, context, text):
        return True  # handled

    return False  # not handled


# ============================================================
# Registration
# ============================================================

def register_admin_panel(handlers_list):
    """
    Call this from main.py to register all admin panel handlers.
    handlers_list: list of (handler_type, handler_args) tuples
    """
    pass


# Export the callback handler for manual registration
admin_callback_handler = CallbackQueryHandler(_admin_callback, pattern=r"^ap:")
