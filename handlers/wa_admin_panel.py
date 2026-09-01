"""Interactive Admin Panel — WhatsApp (List Message + Interactive Buttons)."""

import logging
from whatsapp_api import send_text, send_list, send_buttons
from whatsapp_state import get_state, reset_state
from config import db
from handlers.admin import is_stored_admin


# ============================================================
# Stats
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
# Main Admin Menu (List Message)
# ============================================================

def wa_admin_menu(phone):
    """Send List Message with 4 admin sectors."""
    students, instructors, admins, courses = _get_stats()
    items = [
        ("waadm:sec:students", f"👥 إدارة الطلاب ({students})", "عرض وإضافة وحذف الطلاب"),
        ("waadm:sec:instructors", f"👨‍🏫 إدارة الأساتذة ({instructors})", "عرض وإضافة وحذف الأساتذة"),
        ("waadm:sec:admins", f"🛡️ إدارة الأدمنية ({admins})", "عرض وإضافة وحذف المشرفين"),
        ("waadm:sec:courses", f"📚 إدارة المواد ({courses})", "عرض المواد الدراسية"),
    ]
    send_list(
        phone,
        f"🛡️ لوحة إدارة النظام\n\n"
        f"👥 الطلاب: {students}\n"
        f"👨‍🏫 الأساتذة: {instructors}\n"
        f"🛡️ المشرفين: {admins}\n"
        f"📚 المواد: {courses}\n\n"
        "اختر القسم:",
        items,
        header="🛡️ لوحة الإدارة",
        button_text="اختر قسم",
    )


# ============================================================
# Sector Sub-Menu (Interactive Buttons — max 3)
# ============================================================

def wa_admin_sector(phone, section):
    """Send Interactive Buttons for a sector (max 3 buttons)."""
    labels = {
        "students": "الطلاب",
        "instructors": "الأساتذة",
        "admins": "الأدمنية",
        "courses": "المواد",
    }
    label = labels.get(section, section)

    buttons = [
        (f"waadm:list:{section}", f"📋 عرض {label}"),
        (f"waadm:add:{section}", f"➕ إضافة {label[:-1] if label.endswith('ة') else label}"),
        (f"waadm:more:{section}", "⚙️ خيارات أخرى"),
    ]
    send_buttons(
        phone,
        f"📂 قسم {label}\n\nاختر الإجراء:",
        buttons,
    )


def wa_admin_more_options(phone, section):
    """Second set of buttons for edit/delete."""
    labels = {
        "students": "الطلاب",
        "instructors": "الأساتذة",
        "admins": "الأدمنية",
        "courses": "المواد",
    }
    label = labels.get(section, section)

    buttons = [
        (f"waadm:edit:{section}", f"✏️ تعديل {label}"),
        (f"waadm:del:{section}", f"🗑️ حذف {label}"),
        (f"waadm:sec:{section}", "🔙 رجوع"),
    ]
    send_buttons(
        phone,
        f"⚙️ خيارات إضافية — {label}",
        buttons,
    )


# ============================================================
# List People
# ============================================================

def wa_admin_list(phone, section):
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
        send_text(phone, f"📋 لا يوجد {label} مسجلين.\n\n回到 القائمة الرئيسية.")
        return

    lines = [f"📋 قائمة {label} ({len(docs)}):\n"]
    for doc in docs[:20]:
        data = doc.to_dict() or {}
        name = data.get("name", doc.id)
        lines.append(f"{icon} {doc.id} — {name}")

    send_text(phone, "\n".join(lines))


# ============================================================
# Add Person — Prompt
# ============================================================

def wa_admin_add_prompt(phone, section):
    """Send instructions for adding a person."""
    prompts = {
        "students": (
            "➕ **إضافة طالب**\n\n"
            "أرسل الرقم الجامعي ثم البريد ثم الاسم:\n"
            "`123456789 ali@uni.edu.sd علي`"
        ),
        "instructors": (
            "➕ **إضافة دكتور**\n\n"
            "أرسل معرف الدكتور ثم البريد ثم الاسم:\n"
            "`987654321 omar@uni.edu.sd عمر`"
        ),
        "admins": (
            "➕ **إضافة مشرف**\n\n"
            "أرسل معرف المستخدم:\n"
            "`123456789`"
        ),
        "courses": (
            "➕ **إضافة مادة**\n\n"
            "أرسل اسم المادة:\n"
            "`الرياضيات`"
        ),
    }
    send_text(phone, prompts.get(section, "تنسيق غير معروف"))
    get_state(phone)["state"] = f"WAADMIN_ADD_{section.upper()}"


# ============================================================
# Add Person — Execute
# ============================================================

def wa_admin_add_execute(phone, section, text):
    """Execute add person from text input."""
    parts = text.strip().split()
    coll_map = {
        "students": "students",
        "instructors": "instructors",
        "admins": "admins",
        "courses": "courses",
    }
    coll = coll_map.get(section)
    if not coll:
        return

    try:
        if section == "students" and len(parts) >= 2:
            person_id = parts[0]
            email = parts[1]
            name = " ".join(parts[2:]) if len(parts) > 2 else ""
            db.collection(coll).document(person_id).set({
                "email": email, "name": name,
                "created_by": f"wa:{phone}",
            })
            send_text(phone, f"✅ تم إضافة الطالب `{person_id}` بنجاح.")

        elif section == "instructors" and len(parts) >= 2:
            person_id = parts[0]
            email = parts[1]
            name = " ".join(parts[2:]) if len(parts) > 2 else ""
            db.collection(coll).document(person_id).set({
                "email": email, "name": name,
                "created_by": f"wa:{phone}",
            })
            send_text(phone, f"✅ تم إضافة الدكتور `{person_id}` بنجاح.")

        elif section == "admins" and len(parts) >= 1:
            person_id = parts[0]
            db.collection(coll).document(person_id).set({
                "added_by": f"wa:{phone}",
            })
            send_text(phone, f"✅ تم إضافة المشرف `{person_id}` بنجاح.")

        elif section == "courses":
            name = text.strip()
            folder = name.replace(" ", "-").lower()
            db.collection(coll).document(folder).set({
                "name": name, "folder": folder,
                "created_by": f"wa:{phone}",
            })
            send_text(phone, f"✅ تم إضافة المادة `{name}` بنجاح.")

        else:
            send_text(phone, "❌ تنسيق غير صحيح. حاول مرة أخرى.")

    except Exception as e:
        logging.exception("WA admin add failed")
        send_text(phone, f"❌ فشلت الإضافة: {e}")

    reset_state(phone)


# ============================================================
# Delete Person — List with confirmation
# ============================================================

def wa_admin_del_list(phone, section):
    """List people for deletion."""
    collection_map = {
        "students": ("students", "الطالب", "👤"),
        "instructors": ("instructors", "الدكتور", "👨‍🏫"),
        "admins": ("admins", "المشرف", "🛡️"),
    }
    if section not in collection_map:
        send_text(phone, "🗑️ حذف المواد يتم بشكل مختلف.")
        return

    coll, label, icon = collection_map[section]
    try:
        docs = list(db.collection(coll).stream())
    except Exception:
        docs = []

    if not docs:
        send_text(phone, f"📋 لا يوجد {label} لحذفهم.")
        return

    buttons = []
    for doc in docs[:3]:  # WhatsApp max 3 buttons
        data = doc.to_dict() or {}
        name = data.get("name", doc.id)
        buttons.append((f"waadm:confirm_del:{section}:{doc.id}", f"🗑️ {name}"))

    send_buttons(phone, f"🗑️ اختر {label} للحذف:", buttons)


def wa_admin_confirm_del(phone, section, person_id):
    """Delete after confirmation."""
    coll_map = {
        "students": "students",
        "instructors": "instructors",
        "admins": "admins",
    }
    coll = coll_map.get(section)
    if not coll:
        return

    try:
        db.collection(coll).document(person_id).delete()
        send_text(phone, f"✅ تم حذف `{person_id}` بنجاح.")
    except Exception as e:
        logging.exception("WA admin del failed")
        send_text(phone, f"❌ فشل الحذف: {e}")


# ============================================================
# Edit Person — Prompt
# ============================================================

def wa_admin_edit_prompt(phone, section):
    """Show edit instructions."""
    prompts = {
        "students": (
            "✏️ **تعديل طالب**\n\n"
            "أرسل:\n"
            "`تعديل طالب 123456789 name=الاسم الجديد`"
        ),
        "instructors": (
            "✏️ **تعديل دكتور**\n\n"
            "أرسل:\n"
            "`تعديل دكتور 987654321 name=الاسم الجديد`"
        ),
        "admins": "✏️ تعديل الأدمنية — يتم عبر حذف وإعادة إضافة.",
        "courses": "✏️ تعديل المواد — يتم عبر حذف وإعادة إضافة.",
    }
    send_text(phone, prompts.get(section, "تنسيق غير معروف"))


# ============================================================
# Callback Router
# ============================================================

def wa_admin_callback(phone, payload):
    """
    Route waadm:* callbacks.
    Returns True if handled, False otherwise.
    """
    if not payload.startswith("waadm:"):
        return False

    parts = payload.split(":")
    action = parts[1] if len(parts) > 1 else ""

    # waadm:sec:<section>  →  show sector
    if action == "sec" and len(parts) == 3:
        wa_admin_sector(phone, parts[2])
        return True

    # waadm:list:<section>  →  list
    if action == "list" and len(parts) == 3:
        wa_admin_list(phone, parts[2])
        return True

    # waadm:add:<section>  →  prompt add
    if action == "add" and len(parts) == 3:
        wa_admin_add_prompt(phone, parts[2])
        return True

    # waadm:more:<section>  →  more options
    if action == "more" and len(parts) == 3:
        wa_admin_more_options(phone, parts[2])
        return True

    # waadm:edit:<section>  →  edit prompt
    if action == "edit" and len(parts) == 3:
        wa_admin_edit_prompt(phone, parts[2])
        return True

    # waadm:del:<section>  →  del list
    if action == "del" and len(parts) == 3:
        wa_admin_del_list(phone, parts[2])
        return True

    # waadm:confirm_del:<section>:<id>  →  delete
    if action == "confirm_del" and len(parts) == 4:
        wa_admin_confirm_del(phone, parts[2], parts[3])
        return True

    return False
