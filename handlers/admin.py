import asyncio
from firebase_admin import firestore
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from config import ADMIN_TELEGRAM_IDS, ADMIN_WHATSAPP_NUMBERS, db
from github_utils import list_repository_folders

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
    """Grant admin access after the caller has already been authorized."""
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
    """Remove a stored admin after the caller has already been authorized."""
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
    """Show students and instructors in two separate Telegram messages."""
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
    if field in {"chat_id", "last_active"} or not field.replace("_", "").isalnum():
        await update.effective_message.reply_text("لا يمكن تعديل هذا الحقل من لوحة الأدمن.")
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
    await update.effective_message.reply_text(
        f"الصيغة: عدّل {label} <المعرف> <اسم الحقل> <القيمة>\n"
        f"مثال: عدّل {label} {person_id} name الاسم الجديد\n"
        f"الحقول المسموحة: name, email"
    )


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