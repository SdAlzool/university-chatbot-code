from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler
)
from config import TOKEN
from handlers.admin import (
    show_my_id, admin_dashboard, list_admins, add_admin, remove_admin,
    list_students, list_instructors, list_all_people, add_student, add_instructor,
    edit_student, edit_instructor,
    delete_student, delete_instructor, handle_person_button, handle_person_delete,
)
from handlers.auth import (
    login_conv, logout
)
from handlers.courses import (
    show_courses, get_sheet, summarize_last_file,
    handle_sheet_button, handle_file_button
)
from handlers.content_mgmt import (
    addcontent_conv, deletecontent_start, handle_delmenu_button,
    handle_delwhole_select, handle_delwhole_confirm,
    handle_delcourse_button, handle_delfile_button
)
from handlers.general import (
    start, help_command, handle_welcome_buttons, handle_voice, handle_message
)
from handlers.file_tools import (
    handle_document, handle_photo, handle_file_action
)

def main():
    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myid", show_my_id))
    
    # Auth & Management
    app.add_handler(login_conv)
    app.add_handler(addcontent_conv)
    app.add_handler(CommandHandler("logout", logout))
    
    # Courses & Sheets
    app.add_handler(CommandHandler("courses", show_courses))
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
    app.add_handler(CommandHandler("editstudent", edit_student))
    app.add_handler(CommandHandler("editinstructor", edit_instructor))
    app.add_handler(CommandHandler("deletestudent", delete_student))
    app.add_handler(CommandHandler("deleteinstructor", delete_instructor))

    # Callback Queries
    app.add_handler(CallbackQueryHandler(handle_welcome_buttons, pattern="^btn_guest_mode$"))
    app.add_handler(CallbackQueryHandler(handle_sheet_button, pattern="^sheet:"))
    app.add_handler(CallbackQueryHandler(handle_file_button, pattern="^filesel:"))
    app.add_handler(CallbackQueryHandler(handle_delmenu_button, pattern="^delmenu:"))
    app.add_handler(CallbackQueryHandler(handle_delwhole_select, pattern="^delwhole:"))
    app.add_handler(CallbackQueryHandler(handle_delwhole_confirm, pattern="^delwholeconfirm:"))
    app.add_handler(CallbackQueryHandler(handle_delcourse_button, pattern="^delcourse:"))
    app.add_handler(CallbackQueryHandler(handle_delfile_button, pattern="^delfile:"))
    app.add_handler(CallbackQueryHandler(handle_person_button, pattern="^person:"))
    app.add_handler(CallbackQueryHandler(handle_person_delete, pattern="^persondel:"))
    app.add_handler(CallbackQueryHandler(handle_file_action, pattern="^fileact:"))

    # Messages
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("البوت يعمل بنجاح مع ربط المواد التلقائي للطلاب...")
    app.run_polling(timeout=30)

if __name__ == "__main__":
    main()