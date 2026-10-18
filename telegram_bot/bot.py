"""تيليجرام: تسجيل الـhandlers وتشغيل الـpolling."""

import logging
import warnings

from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# تحذير PTB عن المهام المُنشأة في post_init قبل start — متوقّع ولا يمنع العمل
warnings.filterwarnings(
    "ignore", message="Tasks created via `Application.create_task`"
)

from config import TOKEN
from telegram_bot.admin_panel import (
    _admin_callback,
    add_admin,
    add_course_cmd,
    add_instructor,
    add_student,
    admin_dashboard,
    admin_panel,
    delete_instructor,
    delete_student,
    edit_instructor,
    edit_student,
    handle_person_button,
    handle_person_delete,
    list_admins,
    list_all_people,
    list_instructors,
    list_students,
    remove_admin,
    show_my_id,
)
from telegram_bot.handlers import (
    addcontent_conv,
    deletecontent_start,
    feedback_prompt_loop,
    get_sheet,
    handle_ask_course,
    handle_back_my_courses,
    handle_course_file_action,
    handle_course_option,
    handle_delcourse_button,
    handle_delfile_button,
    handle_delmenu_button,
    handle_delwhole_confirm,
    handle_delwhole_select,
    handle_document,
    handle_feedback_button,
    handle_file_action,
    handle_file_button,
    handle_instructor_callback,
    handle_message,
    handle_my_course_button,
    handle_photo,
    handle_sheet_button,
    handle_student_callback,
    handle_voice,
    handle_welcome_buttons,
    help_command,
    login_conv,
    logout,
    show_courses,
    show_my_courses,
    start,
    summarize_last_file,
)


# ============================================================
# من الملف الأصلي: main.py
# ============================================================


async def _on_error(update, context):
    error = context.error
    logging.error(
        "Unhandled Telegram update error",
        exc_info=(type(error), error, error.__traceback__),
    )

async def _post_init(app):
    """يبدأ مجدول طلبات التقييم المؤجّلة (رسالة منفصلة بعد كل رد ذكاء اصطناعي).

    يجب أن يكون async: PTB تنادي post_init كمعامل قبل run_until_complete،
    فدالة عادية تُنفَّذ برّا الـloop وتسقط create_task بـ "no running event loop".
    """
    app.create_task(feedback_prompt_loop(app))
    logging.info("⏳ Feedback prompt scheduler started (sweep every 60s)")


def main():
    app = Application.builder().token(TOKEN).post_init(_post_init).build()
    app.add_error_handler(_on_error)

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myid", show_my_id))
    app.add_handler(CommandHandler("logout", logout))
    
    # Auth & Management
    app.add_handler(login_conv)
    app.add_handler(addcontent_conv)

    
    # Courses & Sheets
    app.add_handler(CommandHandler("courses", show_courses))
    app.add_handler(CommandHandler("mycourses", show_my_courses))
    app.add_handler(CommandHandler("sheets", get_sheet))
    app.add_handler(CommandHandler("summarize", summarize_last_file))
    app.add_handler(CommandHandler("deletecontent", deletecontent_start))
    
    # Admin Panel
    app.add_handler(CommandHandler("admin", admin_dashboard))
    app.add_handler(CommandHandler("admins", list_admins))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    app.add_handler(CommandHandler("students", list_students))
    app.add_handler(CommandHandler("instructors", list_instructors))
    app.add_handler(CommandHandler("people", list_all_people))
    app.add_handler(CommandHandler("addstudent", add_student))
    app.add_handler(CommandHandler("addinstructor", add_instructor))
    app.add_handler(CommandHandler("addcourse", add_course_cmd))
    app.add_handler(CommandHandler("editstudent", edit_student))
    app.add_handler(CommandHandler("editinstructor", edit_instructor))
    app.add_handler(CommandHandler("deletestudent", delete_student))
    app.add_handler(CommandHandler("deleteinstructor", delete_instructor))

    # Admin Panel (new interactive)
    app.add_handler(CommandHandler("adminpanel", admin_panel))

    # Callback Queries
    app.add_handler(CallbackQueryHandler(handle_welcome_buttons, pattern="^btn_guest_mode$"))
    app.add_handler(CallbackQueryHandler(_admin_callback, pattern=r"^ap:"))
    app.add_handler(CallbackQueryHandler(handle_feedback_button, pattern=r"^fb:"))
    app.add_handler(CallbackQueryHandler(handle_student_callback, pattern="^student:"))
    app.add_handler(CallbackQueryHandler(handle_instructor_callback, pattern="^instructor:"))
    app.add_handler(CallbackQueryHandler(handle_ask_course, pattern="^askcourse:"))
    app.add_handler(CallbackQueryHandler(handle_sheet_button, pattern="^sheet:"))
    app.add_handler(CallbackQueryHandler(handle_file_button, pattern="^filesel:"))
    app.add_handler(CallbackQueryHandler(handle_my_course_button, pattern="^mycourse:"))
    app.add_handler(CallbackQueryHandler(handle_course_option, pattern="^courseopt:"))
    app.add_handler(CallbackQueryHandler(handle_back_my_courses, pattern="^backmycourses$"))
    app.add_handler(CallbackQueryHandler(handle_delmenu_button, pattern="^delmenu:"))
    app.add_handler(CallbackQueryHandler(handle_delwhole_select, pattern="^delwhole:"))
    app.add_handler(CallbackQueryHandler(handle_delwhole_confirm, pattern="^delwholeconfirm:"))
    app.add_handler(CallbackQueryHandler(handle_delcourse_button, pattern="^delcourse:"))
    app.add_handler(CallbackQueryHandler(handle_delfile_button, pattern="^delfile:"))
    app.add_handler(CallbackQueryHandler(handle_person_button, pattern="^person:"))
    app.add_handler(CallbackQueryHandler(handle_person_delete, pattern="^persondel:"))
    app.add_handler(CallbackQueryHandler(handle_file_action, pattern="^fileact:"))
    app.add_handler(CallbackQueryHandler(handle_course_file_action, pattern="^coursefile:"))

    # Messages
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("البوت يعمل بنجاح مع ربط المواد التلقائي للطلاب...")
    
    # Clear webhook via deleteWebhook API
    import requests
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true",
            timeout=10
        )
        print(f"Webhook deleted: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Webhook delete failed: {e}")
    
    # bootstrap_retries=-1: إعادة محاولة getUpdates بلا نهاية عند تعذّر
    # الاتصال وقت الإقلاع (شائع لحظة الـdeploy على Render). القيمة الافتراضية0
    # كانت تستسلم فوراً وتُنهي العملية كلها.
    app.run_polling(timeout=30, bootstrap_retries=-1)

if __name__ == "__main__":
    main()
