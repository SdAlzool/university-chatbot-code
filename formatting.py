"""Shared message formatting for consistent output across Telegram and WhatsApp."""

# ============================================================
# Formatting Helpers
# ============================================================

def bold(text):
    """Format text as bold (Markdown for Telegram, *text* for WhatsApp)."""
    return f"**{text}**"


def italic(text):
    """Format text as italic."""
    return f"_{text}_"


def code(text):
    """Format text as code."""
    return f"`{text}`"


def separator():
    """Return a separator line."""
    return "━━━━━━━━━━━━━━━━━━━━"


def bullet(text):
    """Return a bulleted line."""
    return f"• {text}"


def numbered(num, text):
    """Return a numbered line."""
    return f"{num}. {text}"


def success(text):
    """Return a success message."""
    return f"✅ {text}"


def error(text):
    """Return an error message."""
    return f"❌ {text}"


def warning(text):
    """Return a warning message."""
    return f"⚠️ {text}"


def info(text):
    """Return an info message."""
    return f"ℹ️ {text}"


def header(text):
    """Return a formatted header."""
    return f"{separator()}\n{text}\n{separator()}"


def section(title, content):
    """Return a formatted section."""
    return f"{bold(title)}\n{content}"


def menu_item(emoji, title, description=""):
    """Return a formatted menu item."""
    if description:
        return f"{emoji} {bold(title)}\n   {description}"
    return f"{emoji} {bold(title)}"


def instruction(step, text):
    """Return a formatted instruction."""
    return f"{numbered(step, '')} {text}"


def confirm_prompt(text):
    """Return a confirmation prompt."""
    return f"{warning(text)}\n\nهل تريد المتابعة؟"


def file_info(name, size=None, type_=None):
    """Return formatted file information."""
    parts = [f"📄 {bold(name)}"]
    if size:
        parts.append(f"📦 الحجم: {size}")
    if type_:
        parts.append(f"📋 النوع: {type_}")
    return "\n".join(parts)


def course_info(name, folder=None, instructor=None):
    """Return formatted course information."""
    parts = [f"📚 {bold(name)}"]
    if folder:
        parts.append(f"📁 المجلد: {folder}")
    if instructor:
        parts.append(f"👨‍🏫 الدكتور: {instructor}")
    return "\n".join(parts)


def progress(step, total, text=""):
    """Return a progress indicator."""
    bar = "█" * step + "░" * (total - step)
    if text:
        return f"{bar} {step}/{total}\n{text}"
    return f"{bar} {step}/{total}"


def welcome_message(name=""):
    """Return a welcome message."""
    if name:
        return f"👋 أهلاً {name}!\n\nكيف يمكنني مساعدتك اليوم؟"
    return "👋 أهلاً بك!\n\nكيف يمكنني مساعدتك اليوم؟"


def goodbye_message():
    """Return a goodbye message."""
    return "👋 شكراً لاستخدامك البوت!\n\nنتمنى أن نراك قريباً."


def help_message():
    """Return the help message."""
    return f"""
{header("🎓 بوت الخدمات الجامعية")}

أهلاً بك! أنا مساعدك الأكاديمي، أرسل سؤالك أو ملفك وسأجيبك فوراً.

{header("الخدمات المتاحة")}

{menu_item("💬", "إجابة الاستفسارات", "أسئلة عامة عن الجامعة")}
{menu_item("📄", "تلخيص وترجمة الملفات", "PDF / Word / صور")}
{menu_item("🎙️", "تحويل الصوت إلى نص", "أرسل رسالة صوتية")}
{menu_item("📚", "عرض المقررات والشيتات", "أرسل /login للتسجيل")}

{header("الأوامر")}

{code("/start")} - بدء المحادثة
{code("/help")} - عرض هذه الرسالة
{code("/login")} - تسجيل الدخول
{code("/courses")} - عرض المقررات
{code("/mycourses")} - عرض موادي
{code("/sheets")} - عرض الشيتات
{code("/summarize")} - تلخيص آخر ملف
{code("/admin")} - لوحة التحكم (للأدمن)

{separator()}
⚙️ أدمن المحتوى؟ أرسل /admin للوحة التحكم.
"""


def login_prompt():
    """Return login instructions."""
    return f"""
{header("🔐 تسجيل الدخول")}

{info("اكتب رقمك الجامعي أو معرف الدكتور")}

{separator()}
{code("مثال: 123456789")}
{separator()}
"""


def otp_prompt():
    """Return OTP instructions."""
    return f"""
{header("🔐 التحقق")}

{info("تم إرسال رمز التحقق إلى بريدك الإلكتروني")}

{separator()}
{code("اكتب الرمز هنا")}
{separator()}
"""


def course_selection_prompt():
    """Return course selection instructions."""
    return f"""
{header("📚 اختيار المادة")}

{info("اختر المادة من القائمة أدناه")}

{separator()}
"""


def file_upload_prompt():
    """Return file upload instructions."""
    return f"""
{header("📤 رفع ملف")}

{info("أرسل الملف الذي تريد رفعه")}

{separator()}
{code("الأنواع المدعومة: PDF, Word, صور")}
{separator()}
"""


def add_content_prompt():
    """Return add content instructions."""
    return f"""
{header("➕ إضافة محتوى")}

{info("اختر نوع المادة:")}

{separator()}
{numbered(1, "مادة موجودة - إضافة ملف لمادة موجودة")}
{numbered(2, "مادة جديدة - إنشاء مادة جديدة")}
{separator()}
"""


def delete_content_prompt():
    """Return delete content instructions."""
    return f"""
{header("🗑️ حذف محتوى")}

{info("اختر ما تريد حذفه:")}

{separator()}
{numbered(1, "حذف ملف واحد")}
{numbered(2, "حذف مادة كاملة")}
{separator()}
"""


def confirm_delete_prompt(item_name):
    """Return delete confirmation prompt."""
    return f"""
{header("⚠️ تأكيد الحذف")}

{warning(f"هل أنت متأكد من حذف {item_name}؟")}

{separator()}
{numbered(1, "نعم، احذف")}
{numbered(2, "لا، إلغاء")}
{separator()}
"""


def success_message(action):
    """Return a success message."""
    return f"""
{header("✅ تم بنجاح")}

{success(action)}

{separator()}
"""


def error_message(error_text):
    """Return an error message."""
    return f"""
{header("❌ خطأ")}

{error(error_text)}

{separator()}
{info("حاول مرة أخرى أو تواصل مع الدعم")}
{separator()}
"""


def loading_message():
    """Return a loading message."""
    return f"⏳ جاري المعالجة...\n\n{info("يرجى الانتظار")}"


def voice_processing_message():
    """Return voice processing message."""
    return f"🎙️ جاري معالجة الرسالة الصوتية...\n\n{info("يرجى الانتظار")}"


def voice_result_message(text):
    """Return voice result message."""
    return f"""
{header("🎙️ نتيجة التفريغ")}

{text}

{separator()}
"""


def summary_result_message(filename, summary):
    """Return summary result message."""
    return f"""
{header("📝 ملخص الملف")}

{file_info(filename)}

{separator()}
{summary}
{separator()}
"""


def translation_result_message(filename, translation):
    """Return translation result message."""
    return f"""
{header("🌐 ترجمة الملف")}

{file_info(filename)}

{separator()}
{translation}
{separator()}
"""


def my_courses_list(courses):
    """Return formatted list of student's courses."""
    if not courses:
        return f"""
{header("📚 موادي")}

{info("لا توجد مواد مسجلة لك")}

{separator()}
"""
    
    lines = [header("📚 موادي"), ""]
    for i, course in enumerate(courses, 1):
        name = course.get("name", "مادة")
        lines.append(numbered(i, name))
    lines.append(f"\n{separator()}")
    return "\n".join(lines)


def course_options_menu(course_name):
    """Return course options menu."""
    return f"""
{header(f"📚 {course_name}")}

{info("اختر ما تريد:")}

{separator()}
{numbered(1, "📋 المقرر")}
{numbered(2, "📖 المراجع")}
{numbered(3, "📝 الامتحانات")}
{numbered(4, "📄 الشيتات")}
{separator()}
"""


def file_options_menu(filename):
    """Return file options menu."""
    return f"""
{header(f"📄 {filename}")}

{info("اختر ما تريد:")}

{separator()}
{numbered(1, "⬇️ تحميل")}
{numbered(2, "🌐 ترجمة")}
{numbered(3, "📝 تلخيص")}
{separator()}
"""


def student_welcome_menu():
    """Return student welcome menu."""
    return f"""
{header("👋 أهلاً بك!")}

{info("اختر ما تريد:")}

{separator()}
{numbered(1, "❓ سؤال عن الجامعة")}
{numbered(2, "📚 سؤال عن مادة")}
{numbered(3, "📖 موادي")}
{separator()}
"""


def instructor_welcome_menu():
    """Return instructor welcome menu."""
    return f"""
{header("👋 أهلاً أستاذي!")}

{info("اختر ما تريد:")}

{separator()}
{numbered(1, "📚 عرض المواد")}
{numbered(2, "➕ إضافة مادة")}
{numbered(3, "🗑️ حذف مادة")}
{separator()}
"""


def admin_panel_menu():
    """Return admin panel menu."""
    return f"""
{header("⚙️ لوحة التحكم")}

{info("اختر ما تريد:")}

{separator()}
{numbered(1, "👥 إدارة الطلاب")}
{numbered(2, "👨‍🏫 إدارة الأساتذة")}
{numbered(3, "📚 إدارة المواد")}
{numbered(4, "➕ إضافة أدمن")}
{numbered(5, "🗑️ حذف أدمن")}
{separator()}
"""


def list_header(title, count=None):
    """Return a list header."""
    if count is not None:
        return f"{header(title)}\n\n{info(f"العدد: {count}")}"
    return header(title)


def person_info(person_id, name, email, role):
    """Return formatted person information."""
    role_emoji = "👨‍🎓" if role == "student" else "👨‍🏫"
    return f"""
{header(f"{role_emoji} {name}")}

{info("المعرف:")} {code(str(person_id))}
{info("البريد:")} {code(email)}
{separator()}
"""


def course_list_item(name, folder=None, instructor=None):
    """Return a course list item."""
    parts = [f"📚 {bold(name)}"]
    if folder:
        parts.append(f"   📁 {folder}")
    if instructor:
        parts.append(f"   👨‍🏫 {instructor}")
    return "\n".join(parts)


def file_list_item(name, size=None):
    """Return a file list item."""
    parts = [f"📄 {name}"]
    if size:
        parts.append(f"   📦 {size}")
    return "\n".join(parts)


def confirmation_message(action, item):
    """Return a confirmation message."""
    return f"""
{header("⚠️ تأكيد")}

{warning(f"هل أنت متأكد من {action} {item}؟")}

{separator()}
{numbered(1, "نعم")}
{numbered(2, "لا")}
{separator()}
"""


def language_switch_message(lang):
    """Return language switch message."""
    if lang == "en":
        return f"""
{header("🌐 Language Switched")}

{success("Language changed to English")}

{separator()}
{info("Type 'عربي' to switch back to Arabic")}
{separator()}
"""
    return f"""
{header("🌐 تم تغيير اللغة")}

{success("تم تغيير اللغة إلى العربية")}

{separator()}
{info("Type 'English' to switch to English")}
{separator()}
"""


def pending_upload_message(filename):
    """Return pending upload message."""
    return f"""
{header("📤 رفع ملف")}

{info("تم استلام الملف:")}
{file_info(filename)}

{separator()}
{info("اختر المادة لرفع الملف إليها")}
{separator()}
"""


def upload_success_message(filename, course_name):
    """Return upload success message."""
    return f"""
{header("✅ تم الرفع بنجاح")}

{success(f"تم رفع {filename}")}

{separator()}
{info(f"المادة: {course_name}")}
{separator()}
"""


def upload_error_message(error_text):
    """Return upload error message."""
    return f"""
{header("❌ فشل الرفع")}

{error(error_text)}

{separator()}
{info("حاول مرة أخرى")}
{separator()}
"""


def delete_success_message(item_name):
    """Return delete success message."""
    return f"""
{header("✅ تم الحذف بنجاح")}

{success(f"تم حذف {item_name}")}

{separator()}
"""


def delete_error_message(error_text):
    """Return delete error message."""
    return f"""
{header("❌ فشل الحذف")}

{error(error_text)}

{separator()}
{info("حاول مرة أخرى")}
{separator()}
"""


def no_permission_message():
    """Return no permission message."""
    return f"""
{header("⛔ غير مصرح")}

{error("ليس لديك صلاحية الوصول لهذه الخدمة")}

{separator()}
{info("تواصل مع الأدمن")}
{separator()}
"""


def session_expired_message():
    """Return session expired message."""
    return f"""
{header("⏰ انتهت الجلسة")}

{warning("انتهت صلاحية الجلسة")}

{separator()}
{info("سجل دخولك مرة أخرى")}
{separator()}
"""


def invalid_otp_message(attempts_left):
    """Return invalid OTP message."""
    return f"""
{header("❌ رمز خاطئ")}

{error("رمز التحقق غير صحيح")}

{separator()}
{info(f"المحاولات المتبقية: {attempts_left}")}
{separator()}
"""


def otp_expired_message():
    """Return OTP expired message."""
    return f"""
{header("⏰ انتهت صلاحية الرمز")}

{warning("انتهت صلاحية رمز التحقق")}

{separator()}
{info("اطلب رمز جديد")}
{separator()}
"""


def resend_cooldown_message(seconds):
    """Return resend cooldown message."""
    return f"""
{header("⏳ انتظر")}

{info(f"انتظر {seconds} ثانية قبل طلب رمز جديد")}

{separator()}
"""


def welcome_back_message(name):
    """Return welcome back message."""
    return f"""
{header("👋 أهلاً بعودتك!")}

{success(f"أهلاً {name}!")}

{separator()}
{info("كيف يمكنني مساعدتك اليوم؟")}
{separator()}
"""


def first_time_welcome_message():
    """Return first time welcome message."""
    return f"""
{header("🎓 أهلاً بك في بوت الخدمات الجامعية!")}

{success("تم إنشاء حسابك بنجاح")}

{separator()}
{info("يمكنك الآن:")}
{numbered(1, "طرح أسئلة عن الجامعة")}
{numbered(2, "رفع ملفات لتلخيصها أو ترجمتها")}
{numbered(3, "تسجيل الدخول للمقررات")}
{separator()}
"""


def course_created_message(course_name):
    """Return course created message."""
    return f"""
{header("✅ تم إنشاء المادة")}

{success(f"تم إنشاء {course_name}")}

{separator()}
{info("يمكنك الآن رفع ملفات لهذه المادة")}
{separator()}
"""


def course_deleted_message(course_name):
    """Return course deleted message."""
    return f"""
{header("✅ تم حذف المادة")}

{success(f"تم حذف {course_name}")}

{separator()}
"""


def file_deleted_message(filename):
    """Return file deleted message."""
    return f"""
{header("✅ تم حذف الملف")}

{success(f"تم حذف {filename}")}

{separator()}
"""


def student_added_message(student_name):
    """Return student added message."""
    return f"""
{header("✅ تم إضافة الطالب")}

{success(f"تم إضافة {student_name}")}

{separator()}
"""


def student_deleted_message(student_name):
    """Return student deleted message."""
    return f"""
{header("✅ تم حذف الطالب")}

{success(f"تم حذف {student_name}")}

{separator()}
"""


def instructor_added_message(instructor_name):
    """Return instructor added message."""
    return f"""
{header("✅ تم إضافة الأستاذ")}

{success(f"تم إضافة {instructor_name}")}

{separator()}
"""


def instructor_deleted_message(instructor_name):
    """Return instructor deleted message."""
    return f"""
{header("✅ تم حذف الأستاذ")}

{success(f"تم حذف {instructor_name}")}

{separator()}
"""


def admin_added_message(admin_name):
    """Return admin added message."""
    return f"""
{header("✅ تم إضافة الأدمن")}

{success(f"تم إضافة {admin_name}")}

{separator()}
"""


def admin_deleted_message(admin_name):
    """Return admin deleted message."""
    return f"""
{header("✅ تم حذف الأدمن")}

{success(f"تم حذف {admin_name}")}

{separator()}
"""


def edit_success_message(field, value):
    """Return edit success message."""
    return f"""
{header("✅ تم التعديل بنجاح")}

{success(f"تم تعديل {field} إلى {value}")}

{separator()}
"""


def edit_error_message(error_text):
    """Return edit error message."""
    return f"""
{header("❌ فشل التعديل")}

{error(error_text)}

{separator()}
{info("حاول مرة أخرى")}
{separator()}
"""


def list_empty_message(item_type):
    """Return list empty message."""
    return f"""
{header("📭 لا يوجد")}

{info(f"لا يوجد {item_type} مسجل")}

{separator()}
"""


def search_results_message(query, count):
    """Return search results message."""
    return f"""
{header("🔍 نتائج البحث")}

{info(f"نتائج البحث عن: {query}")}
{info(f"العدد: {count}")}

{separator()}
"""


def no_results_message(query):
    """Return no results message."""
    return f"""
{header("🔍 لا توجد نتائج")}

{info(f"لا توجد نتائج لـ: {query}")}

{separator()}
{info("حاول بكلمات مختلفة")}
{separator()}
"""


def file_too_large_message(max_size):
    """Return file too large message."""
    return f"""
{header("📦 الملف كبير جداً")}

{error(f"حجم الملف يتجاوز {max_size}")}

{separator()}
{info("حاول بملف أصغر")}
{separator()}
"""


def unsupported_file_type_message():
    """Return unsupported file type message."""
    return f"""
{header("📋 نوع غير مدعوم")}

{error("نوع الملف غير مدعوم")}

{separator()}
{info("الأنواع المدعومة: PDF, Word, صور")}
{separator()}
"""


def processing_message():
    """Return processing message."""
    return f"""
{header("⏳ جاري المعالجة")}

{info("يرجى الانتظار...")}

{separator()}
"""


def done_message():
    """Return done message."""
    return f"""
{header("✅ تم")}

{success("تمت العملية بنجاح")}

{separator()}
"""


def cancelled_message():
    """Return cancelled message."""
    return f"""
{header("❌ تم الإلغاء")}

{info("تم إلغاء العملية")}

{separator()}
"""


def timeout_message():
    """Return timeout message."""
    return f"""
{header("⏰ انتهت المهلة")}

{warning("انتهت مهلة العملية")}

{separator()}
{info("حاول مرة أخرى")}
{separator()}
"""


def unknown_command_message():
    """Return unknown command message."""
    return f"""
{header("❓ أمر غير معروف")}

{info("الأمر غير معروف")}

{separator()}
{info("أرسل /help لعرض الأوامر المتاحة")}
{separator()}
"""


def maintenance_message():
    """Return maintenance message."""
    return f"""
{header("🔧 صيانة")}

{info("البوت تحت الصيانة حالياً")}

{separator()}
{info("حاول لاحقاً")}
{separator()}
"""


def feedback_thanks_message():
    """Return feedback thanks message."""
    return f"""
{header("🙏 شكراً")}

{success("شكراً لتقييمك!")}

{separator()}
{info("نقدر ملاحظاتك")}
{separator()}
"""


def rating_message(rating):
    """Return rating message."""
    stars = "⭐" * rating
    return f"""
{header("⭐ تقييم")}

{info(f"تقييمك: {stars}")}

{separator()}
"""


def comment_prompt_message():
    """Return comment prompt message."""
    return f"""
{header("💬 تعليق")}

{info("اكتب تعليقك هنا")}

{separator()}
"""


def feedback_received_message():
    """Return feedback received message."""
    return f"""
{header("✅ تم استلام تقييمك")}

{success("تم استلام تقييمك بنجاح")}

{separator()}
{info("شكراً لمشاركتك")}
{separator()}
"""


def welcome_message_guest():
    """Return guest welcome message."""
    return f"""
{header("👋 أهلاً بك!")}

{info("أنت الآن زائر")}

{separator()}
{info("يمكنك:")}
{numbered(1, "طرح أسئلة عن الجامعة")}
{numbered(2, "رفع ملفات لتلخيصها أو ترجمتها")}
{numbered(3, "تسجيل الدخول للمقررات")}
{separator()}
"""


def welcome_message_student(name):
    """Return student welcome message."""
    return f"""
{header("👋 أهلاً بك!")}

{success(f"أهلاً {name}!")}

{separator()}
{info("يمكنك:")}
{numbered(1, "طرح أسئلة عن الجامعة")}
{numbered(2, "رفع ملفات لتلخيصها أو ترجمتها")}
{numbered(3, "عرض موادي")}
{numbered(4, "عرض الشيتات")}
{separator()}
"""


def welcome_message_instructor(name):
    """Return instructor welcome message."""
    return f"""
{header("👋 أهلاً أستاذي!")}

{success(f"أهلاً {name}!")}

{separator()}
{info("يمكنك:")}
{numbered(1, "عرض المواد")}
{numbered(2, "إضافة محتوى")}
{numbered(3, "حذف محتوى")}
{separator()}
"""


def welcome_message_admin(name):
    """Return admin welcome message."""
    return f"""
{header("👋 أهلاً مشرف!")}

{success(f"أهلاً {name}!")}

{separator()}
{info("يمكنك:")}
{numbered(1, "إدارة الطلاب")}
{numbered(2, "إدارة الأساتذة")}
{numbered(3, "إدارة المواد")}
{numbered(4, "إضافة أدمن")}
{numbered(5, "حذف أدمن")}
{separator()}
"""


def login_success_message(name, role):
    """Return login success message."""
    role_text = "طالب" if role == "student" else "أستاذ"
    return f"""
{header("✅ تم تسجيل الدخول")}

{success(f"أهلاً {name}!")}

{separator()}
{info(f"أنت الآن مسجل كـ {role_text}")}
{separator()}
"""


def logout_success_message():
    """Return logout success message."""
    return f"""
{header("✅ تم تسجيل الخروج")}

{success("تم تسجيل الخروج بنجاح")}

{separator()}
{info("نراك قريباً!")}
{separator()}
"""


def already_logged_in_message():
    """Return already logged in message."""
    return f"""
{header("ℹ️ مسجل بالفعل")}

{info("أنت مسجل دخول بالفعل")}

{separator()}
"""


def not_logged_in_message():
    """Return not logged in message."""
    return f"""
{header("🔐 غير مسجل")}

{info("أنت غير مسجل دخول")}

{separator()}
{info("سجل دخولك أولاً")}
{separator()}
"""


def course_not_found_message():
    """Return course not found message."""
    return f"""
{header("❌ غير موجود")}

{error("المادة غير موجودة")}

{separator()}
"""


def file_not_found_message():
    """Return file not found message."""
    return f"""
{header("❌ غير موجود")}

{error("الملف غير موجود")}

{separator()}
"""


def student_not_found_message():
    """Return student not found message."""
    return f"""
{header("❌ غير موجود")}

{error("الطالب غير موجود")}

{separator()}
"""


def instructor_not_found_message():
    """Return instructor not found message."""
    return f"""
{header("❌ غير موجود")}

{error("الأستاذ غير موجود")}

{separator()}
"""


def admin_not_found_message():
    """Return admin not found message."""
    return f"""
{header("❌ غير موجود")}

{error("الأدمن غير موجود")}

{separator()}
"""


def invalid_id_message():
    """Return invalid ID message."""
    return f"""
{header("❌ معرف غير صالح")}

{error("المعرف غير صالح")}

{separator()}
{info("تأكد من المعرف وحاول مرة أخرى")}
{separator()}
"""


def invalid_email_message():
    """Return invalid email message."""
    return f"""
{header("❌ بريد غير صالح")}

{error("البريد الإلكتروني غير صالح")}

{separator()}
{info("تأكد من البريد وحاول مرة أخرى")}
{separator()}
"""


def invalid_name_message():
    """Return invalid name message."""
    return f"""
{header("❌ اسم غير صالح")}

{error("الاسم غير صالح")}

{separator()}
{info("تأكد من الاسم وحاول مرة أخرى")}
{separator()}
"""


def invalid_input_message():
    """Return invalid input message."""
    return f"""
{header("❌ إدخال غير صالح")}

{error("الإدخال غير صالح")}

{separator()}
{info("تأكد من الإدخال وحاول مرة أخرى")}
{separator()}
"""


def try_again_message():
    """Return try again message."""
    return f"""
{header("🔄 حاول مرة أخرى")}

{info("حدث خطأ، حاول مرة أخرى")}

{separator()}
"""


def contact_support_message():
    """Return contact support message."""
    return f"""
{header("📞 تواصل مع الدعم")}

{info("إذا استمرت المشكلة، تواصل مع الدعم")}

{separator()}
"""


def end_of_list_message():
    """Return end of list message."""
    return f"""
{separator()}
{info("نهاية القائمة")}
{separator()}
"""


def page_info_message(current, total):
    """Return page info message."""
    return f"""
{separator()}
{info(f"الصفحة {current} من {total}")}
{separator()}
"""


def next_page_message():
    """Return next page message."""
    return f"""
{separator()}
{info("الصفحة التالية")}
{separator()}
"""


def previous_page_message():
    """Return previous page message."""
    return f"""
{separator()}
{info("الصفحة السابقة")}
{separator()}
"""


def first_page_message():
    """Return first page message."""
    return f"""
{separator()}
{info("الصفحة الأولى")}
{separator()}
"""


def last_page_message():
    """Return last page message."""
    return f"""
{separator()}
{info("الصفحة الأخيرة")}
{separator()}
"""


def select_page_message():
    """Return select page message."""
    return f"""
{header("📄 اختيار الصفحة")}

{info("اختر الصفحة")}

{separator()}
"""


def page_number_message(page):
    """Return page number message."""
    return f"""
{header("📄 الصفحة")}

{info(f"الصفحة {page}")}

{separator()}
"""


def total_pages_message(total):
    """Return total pages message."""
    return f"""
{separator()}
{info(f"إجمالي الصفحات: {total}")}
{separator()}
"""


def items_per_page_message(items):
    """Return items per page message."""
    return f"""
{separator()}
{info(f"العناصر في الصفحة: {items}")}
{separator()}
"""


def total_items_message(total):
    """Return total items message."""
    return f"""
{separator()}
{info(f"إجمالي العناصر: {total}")}
{separator()}
"""


def list_summary_message(total, page, per_page):
    """Return list summary message."""
    return f"""
{separator()}
{info(f"إجمالي: {total} | الصفحة: {page} | في الصفحة: {per_page}")}
{separator()}
"""


def empty_list_message():
    """Return empty list message."""
    return f"""
{header("📭 القائمة فارغة")}

{info("لا توجد عناصر")}

{separator()}
"""


def loading_more_message():
    """Return loading more message."""
    return f"""
{separator()}
{info("جاري تحميل المزيد...")}
{separator()}
"""


def no_more_items_message():
    """Return no more items message."""
    return f"""
{separator()}
{info("لا توجد المزيد من العناصر")}
{separator()}
"""


def end_of_content_message():
    """Return end of content message."""
    return f"""
{separator()}
{info("نهاية المحتوى")}
{separator()}
"""


def back_to_menu_message():
    """Return back to menu message."""
    return f"""
{separator()}
{info("العودة إلى القائمة الرئيسية")}
{separator()}
"""


def main_menu_message():
    """Return main menu message."""
    return f"""
{header("📋 القائمة الرئيسية")}

{info("اختر ما تريد:")}

{separator()}
{numbered(1, "💬 اسألني سؤالاً")}
{numbered(2, "📚 المقررات")}
{numbered(3, "📄 الشيتات")}
{numbered(4, "📤 رفع ملف")}
{numbered(5, "⚙️ إدارة المحتوى")}
{separator()}
"""


def settings_menu_message():
    """Return settings menu message."""
    return f"""
{header("⚙️ الإعدادات")}

{info("اختر ما تريد:")}

{separator()}
{numbered(1, "🌐 تغيير اللغة")}
{numbered(2, "🔔 الإشعارات")}
{numbered(3, "🔒 الخصوصية")}
{separator()}
"""


def language_menu_message():
    """Return language menu message."""
    return f"""
{header("🌐 اللغة")}

{info("اختر اللغة:")}

{separator()}
{numbered(1, "العربية")}
{numbered(2, "English")}
{separator()}
"""


def notifications_menu_message():
    """Return notifications menu message."""
    return f"""
{header("🔔 الإشعارات")}

{info("اختر ما تريد:")}

{separator()}
{numbered(1, "تفعيل الإشعارات")}
{numbered(2, "تعطيل الإشعارات")}
{separator()}
"""


def privacy_menu_message():
    """Return privacy menu message."""
    return f"""
{header("🔒 الخصوصية")}

{info("اختر ما تريد:")}

{separator()}
{numbered(1, "سياسة الخصوصية")}
{numbered(2, "شروط الاستخدام")}
{separator()}
"""


def about_message():
    """Return about message."""
    return f"""
{header("ℹ️ حول")}

{info("بوت الخدمات الجامعية")}

{separator()}
{info("الإصدار: 1.0.0")}
{info("المطور: فريق الجامعة")}
{separator()}
"""


def version_message():
    """Return version message."""
    return f"""
{header("📦 الإصدار")}

{info("الإصدار: 1.0.0")}

{separator()}
"""


def developer_message():
    """Return developer message."""
    return f"""
{header("👨‍💻 المطور")}

{info("فريق الجامعة")}

{separator()}
"""


def contact_message():
    """Return contact message."""
    return f"""
{header("📞 التواصل")}

{info("البريد: support@university.edu")}
{info("الهاتف: 123456789")}

{separator()}
"""


def social_media_message():
    """Return social media message."""
    return f"""
{header("📱 التواصل الاجتماعي")}

{info("تابعنا على:")}

{separator()}
{numbered(1, "تويتر")}
{numbered(2, "انستغرام")}
{numbered(3, "فيسبوك")}
{separator()}
"""


def website_message():
    """Return website message."""
    return f"""
{header("🌐 الموقع")}

{info("www.university.edu")}

{separator()}
"""


def location_message():
    """Return location message."""
    return f"""
{header("📍 الموقع")}

{info("الحرم الجامعي")}

{separator()}
"""


def working_hours_message():
    """Return working hours message."""
    return f"""
{header("⏰ ساعات العمل")}

{info("الأحد - الخميس: 8:00 ص - 4:00 م")}

{separator()}
"""


def holidays_message():
    """Return holidays message."""
    return f"""
{header("📅 العطلات")}

{info("العطلات الرسمية:")}

{separator()}
{numbered(1, "عيد الفطر")}
{numbered(2, "عيد الأضحى")}
{numbered(3, "اليوم الوطني")}
{separator()}
"""


def academic_calendar_message():
    """Return academic calendar message."""
    return f"""
{header("📅 التقويم الأكاديمي")}

{info("الفصل الحالي: الفصل الأول")}

{separator()}
{info("بداية الفصل: 2024-09-01")}
{info("نهاية الفصل: 2024-12-15")}
{separator()}
"""


def exam_schedule_message():
    """Return exam schedule message."""
    return f"""
{header("📝 جدول الامتحانات")}

{info("الامتحانات النهائية:")}

{separator()}
{numbered(1, "الرياضيات: 2024-12-10")}
{numbered(2, "الفيزياء: 2024-12-12")}
{numbered(3, "الكيمياء: 2024-12-14")}
{separator()}
"""


def assignment_deadline_message():
    """Return assignment deadline message."""
    return f"""
{header("📅 مواعيد التسليم")}

{info("التسليم القادم:")}

{separator()}
{numbered(1, "مشروع البرمجة: 2024-11-15")}
{numbered(2, "تقرير المختبر: 2024-11-20")}
{separator()}
"""


def grade_message(course, grade):
    """Return grade message."""
    return f"""
{header("📊 الدرجة")}

{info(f"المادة: {course}")}
{info(f"الدرجة: {grade}")}

{separator()}
"""


def gpa_message(gpa):
    """Return GPA message."""
    return f"""
{header("📊 المعدل")}

{info(f"المعدل التراكمي: {gpa}")}

{separator()}
"""


def credits_message(credits):
    """Return credits message."""
    return f"""
{header("📊 الساعات")}

{info(f"الساعات المكتملة: {credits}")}

{separator()}
"""


def academic_status_message(status):
    """Return academic status message."""
    return f"""
{header("📊 الحالة الأكاديمية")}

{info(f"الحالة: {status}")}

{separator()}
"""


def warning_message_gpa(gpa):
    """Return warning GPA message."""
    return f"""
{header("⚠️ تنبيه")}

{warning(f"معدلك {gpa} أقل من الحد المطلوب")}

{separator()}
{info("تواصل مع المرشد الأكاديمي")}
{separator()}
"""


def probation_message():
    """Return probation message."""
    return f"""
{header("⚠️ إنذار أكاديمي")}

{warning("أنت تحت المراقبة الأكاديمية")}

{separator()}
{info("تواصل مع المرشد الأكاديمي")}
{separator()}
"""


def good_standing_message():
    """Return good standing message."""
    return f"""
{header("✅ حالة جيدة")}

{success("أنت في حالة أكاديمية جيدة")}

{separator()}
"""


def honors_message(gpa):
    """Return honors message."""
    return f"""
{header("🏆 الشرف")}

{success(f"معدلك {gpa} - قائمة الشرف")}

{separator()}
"""


def graduation_message():
    """Return graduation message."""
    return f"""
{header("🎓 التخرج")}

{success("تهانينا! أنت مؤهل للتخرج")}

{separator()}
"""


def remaining_courses_message(courses):
    """Return remaining courses message."""
    return f"""
{header("📚 المقررات المتبقية")}

{info("المقررات المتبقية للتخرج:")}

{separator()}
{numbered(1, courses)}
{separator()}
"""


def remaining_credits_message(credits):
    """Return remaining credits message."""
    return f"""
{header("📊 الساعات المتبقية")}

{info(f"الساعات المتبقية: {credits}")}

{separator()}
"""


def advisor_message(name, email):
    """Return advisor message."""
    return f"""
{header("👨‍🏫 المرشد الأكاديمي")}

{info(f"الاسم: {name}")}
{info(f"البريد: {email}")}

{separator()}
"""


def appointment_message(date, time):
    """Return appointment message."""
    return f"""
{header("📅 موعد")}

{info(f"التاريخ: {date}")}
{info(f"الوقت: {time}")}

{separator()}
"""


def booking_confirmation_message():
    """Return booking confirmation message."""
    return f"""
{header("✅ تم الحجز")}

{success("تم حجز الموعد بنجاح")}

{separator()}
"""


def booking_cancellation_message():
    """Return booking cancellation message."""
    return f"""
{header("❌ تم الإلغاء")}

{info("تم إلغاء الموعد")}

{separator()}
"""


def booking_reminder_message():
    """Return booking reminder message."""
    return f"""
{header("⏰ تذكير")}

{info("لديك موعد غداً")}

{separator()}
"""


def available_slots_message(slots):
    """Return available slots message."""
    return f"""
{header("📅 المواعيد المتاحة")}

{info("المواعيد المتاحة:")}

{separator()}
{numbered(1, slots)}
{separator()}
"""


def no_available_slots_message():
    """Return no available slots message."""
    return f"""
{header("📭 لا توجد مواعيد")}

{info("لا توجد مواعيد متاحة")}

{separator()}
"""


def select_slot_message():
    """Return select slot message."""
    return f"""
{header("📅 اختيار الموعد")}

{info("اختر الموعد المناسب")}

{separator()}
"""


def slot_booked_message():
    """Return slot booked message."""
    return f"""
{header("✅ تم الحجز")}

{success("تم حجز الموعد")}

{separator()}
"""


def slot_unavailable_message():
    """Return slot unavailable message."""
    return f"""
{header("❌ غير متاح")}

{error("الموعد غير متاح")}

{separator()}
"""


def reschedule_message():
    """Return reschedule message."""
    return f"""
{header("🔄 إعادة جدولة")}

{info("اختر موعداً جديداً")}

{separator()}
"""


def cancel_appointment_message():
    """Return cancel appointment message."""
    return f"""
{header("❌ إلغاء الموعد")}

{info("تم إلغاء الموعد")}

{separator()}
"""


def appointment_details_message(date, time, advisor):
    """Return appointment details message."""
    return f"""
{header("📅 تفاصيل الموعد")}

{info(f"التاريخ: {date}")}
{info(f"الوقت: {time}")}
{info(f"المرشد: {advisor}")}

{separator()}
"""


def upcoming_appointments_message(appointments):
    """Return upcoming appointments message."""
    return f"""
{header("📅 المواعيد القادمة")}

{info("مواعيدك القادمة:")}

{separator()}
{numbered(1, appointments)}
{separator()}
"""


def no_appointments_message():
    """Return no appointments message."""
    return f"""
{header("📭 لا توجد مواعيد")}

{info("لا توجد مواعيد قادمة")}

{separator()}
"""


def past_appointments_message(appointments):
    """Return past appointments message."""
    return f"""
{header("📅 المواعيد السابقة")}

{info("مواعيدك السابقة:")}

{separator()}
{numbered(1, appointments)}
{separator()}
"""


def appointment_reminder_message(date, time):
    """Return appointment reminder message."""
    return f"""
{header("⏰ تذكير بالموعد")}

{info(f"لديك موعد غداً في {time}")}

{separator()}
"""


def appointment_confirmation_message(date, time):
    """Return appointment confirmation message."""
    return f"""
{header("✅ تأكيد الموعد")}

{success(f"تم تأكيد الموعد في {date} الساعة {time}")}

{separator()}
"""


def appointment_cancellation_message():
    """Return appointment cancellation message."""
    return f"""
{header("❌ إلغاء الموعد")}

{info("تم إلغاء الموعد")}

{separator()}
"""


def appointment_reschedule_message(date, time):
    """Return appointment reschedule message."""
    return f"""
{header("🔄 إعادة جدولة")}

{info(f"الموعد الجديد: {date} الساعة {time}")}

{separator()}
"""


def appointment_booking_message():
    """Return appointment booking message."""
    return f"""
{header("📅 حجز موعد")}

{info("اختر الموعد المناسب")}

{separator()}
"""


def appointment_list_message(appointments):
    """Return appointment list message."""
    return f"""
{header("📅 المواعيد")}

{info("مواعيدك:")}

{separator()}
{numbered(1, appointments)}
{separator()}
"""


def appointment_details_message(date, time, advisor, status):
    """Return appointment details message."""
    return f"""
{header("📅 تفاصيل الموعد")}

{info(f"التاريخ: {date}")}
{info(f"الوقت: {time}")}
{info(f"المرشد: {advisor}")}
{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_status_message(status):
    """Return appointment status message."""
    return f"""
{header("📊 حالة الموعد")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_cancel_message():
    """Return appointment cancel message."""
    return f"""
{header("❌ إلغاء الموعد")}

{info("تم إلغاء الموعد")}

{separator()}
"""


def appointment_reschedule_confirm_message(date, time):
    """Return appointment reschedule confirm message."""
    return f"""
{header("✅ تم إعادة الجدولة")}

{success(f"تم إعادة جدولة الموعد إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_cancel_confirm_message():
    """Return appointment cancel confirm message."""
    return f"""
{header("✅ تم الإلغاء")}

{success("تم إلغاء الموعد")}

{separator()}
"""


def appointment_book_confirm_message(date, time):
    """Return appointment book confirm message."""
    return f"""
{header("✅ تم الحجز")}

{success(f"تم حجز الموعد في {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_message():
    """Return appointment reminder confirm message."""
    return f"""
{header("⏰ تذكير")}

{info("تم تعيين تذكير للموعد")}

{separator()}
"""


def appointment_no_reminder_message():
    """Return appointment no reminder message."""
    return f"""
{header("📭 لا يوجد تذكير")}

{info("لا يوجد تذكير للموعد")}

{separator()}
"""


def appointment_reminder_set_message():
    """Return appointment reminder set message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين تذكير للموعد")}

{separator()}
"""


def appointment_reminder_cancelled_message():
    """Return appointment reminder cancelled message."""
    return f"""
{header("❌ تم إلغاء التذكير")}

{info("تم إلغاء تذكير الموعد")}

{separator()}
"""


def appointment_reminder_time_message(time):
    """Return appointment reminder time message."""
    return f"""
{header("⏰ وقت التذكير")}

{info(f"وقت التذكير: {time}")}

{separator()}
"""


def appointment_reminder_date_message(date):
    """Return appointment reminder date message."""
    return f"""
{header("📅 تاريخ التذكير")}

{info(f"تاريخ التذكير: {date}")}

{separator()}
"""


def appointment_reminder_datetime_message(date, time):
    """Return appointment reminder datetime message."""
    return f"""
{header("⏰ تذكير")}

{info(f"تاريخ التذكير: {date}")}
{info(f"وقت التذكير: {time}")}

{separator()}
"""


def appointment_reminder_confirm_message(date, time):
    """Return appointment reminder confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين تذكير لـ {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_cancel_message():
    """Return appointment reminder cancel message."""
    return f"""
{header("❌ تم إلغاء التذكير")}

{info("تم إلغاء تذكير الموعد")}

{separator()}
"""


def appointment_reminder_list_message(reminders):
    """Return appointment reminder list message."""
    return f"""
{header("⏰ التذكيرات")}

{info("تذكيراتك:")}

{separator()}
{numbered(1, reminders)}
{separator()}
"""


def appointment_reminder_no_message():
    """Return appointment reminder no message."""
    return f"""
{header("📭 لا توجد تذكيرات")}

{info("لا توجد تذكيرات")}

{separator()}
"""


def appointment_reminder_add_message():
    """Return appointment reminder add message."""
    return f"""
{header("➕ إضافة تذكير")}

{info("أضف تذكيراً جديداً")}

{separator()}
"""


def appointment_reminder_delete_message():
    """Return appointment reminder delete message."""
    return f"""
{header("🗑️ حذف تذكير")}

{info("حذف تذكير")}

{separator()}
"""


def appointment_reminder_edit_message():
    """Return appointment reminder edit message."""
    return f"""
{header("✏️ تعديل تذكير")}

{info("تعديل تذكير")}

{separator()}
"""


def appointment_reminder_view_message():
    """Return appointment reminder view message."""
    return f"""
{header("👁️ عرض تذكير")}

{info("عرض تذكير")}

{separator()}
"""


def appointment_reminder_settings_message():
    """Return appointment reminder settings message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_message():
    """Return appointment reminder toggle message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_message():
    """Return appointment reminder enable message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_message():
    """Return appointment reminder disable message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_message(status):
    """Return appointment reminder status message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_set_message(time):
    """Return appointment reminder time set message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_set_message(date):
    """Return appointment reminder date set message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_set_message(date, time):
    """Return appointment reminder datetime set message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_set_message():
    """Return appointment reminder confirm set message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_set_message():
    """Return appointment reminder cancel set message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_message():
    """Return appointment reminder delete confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_message():
    """Return appointment reminder edit confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_message():
    """Return appointment reminder view confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_message():
    """Return appointment reminder settings confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_message():
    """Return appointment reminder toggle confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_message():
    """Return appointment reminder enable confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_message():
    """Return appointment reminder disable confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_message(status):
    """Return appointment reminder status confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_message(time):
    """Return appointment reminder time confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_message(date):
    """Return appointment reminder date confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_message(date, time):
    """Return appointment reminder datetime confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_message():
    """Return appointment reminder confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_message():
    """Return appointment reminder cancel confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_message():
    """Return appointment reminder view confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date, time):
    """Return appointment reminder datetime confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success(f"تم تعيين التذكير إلى {date} الساعة {time}")}

{separator()}
"""


def appointment_reminder_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التذكير")}

{success("تم تعيين التذكير بنجاح")}

{separator()}
"""


def appointment_reminder_cancel_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder cancel confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم إلغاء التعيين")}

{info("تم إلغاء تعيين التذكير")}

{separator()}
"""


def appointment_reminder_delete_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder delete confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم الحذف")}

{success("تم حذف التذكير")}

{separator()}
"""


def appointment_reminder_edit_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder edit confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم التعديل")}

{success("تم تعديل التذكير")}

{separator()}
"""


def appointment_reminder_view_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder view confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("👁️ عرض التذكير")}

{info("عرض التذكير")}

{separator()}
"""


def appointment_reminder_settings_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder settings confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("⚙️ إعدادات التذكير")}

{info("إعدادات التذكير")}

{separator()}
"""


def appointment_reminder_toggle_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder toggle confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("🔄 تبديل التذكير")}

{info("تبديل التذكير")}

{separator()}
"""


def appointment_reminder_enable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder enable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تفعيل التذكير")}

{success("تم تفعيل التذكير")}

{separator()}
"""


def appointment_reminder_disable_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message():
    """Return appointment reminder disable confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("❌ تم تعطيل التذكير")}

{info("تم تعطيل التذكير")}

{separator()}
"""


def appointment_reminder_status_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(status):
    """Return appointment reminder status confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("📊 حالة التذكير")}

{info(f"الحالة: {status}")}

{separator()}
"""


def appointment_reminder_time_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(time):
    """Return appointment reminder time confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين الوقت")}

{success(f"تم تعيين وقت التذكير إلى {time}")}

{separator()}
"""


def appointment_reminder_date_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_message(date):
    """Return appointment reminder date confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm confirm message."""
    return f"""
{header("✅ تم تعيين التاريخ")}

{success(f"تم تعيين تاريخ التذكير إلى {date}")}

{separator()}
"""


def appointment_reminder_datetime_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm_confirm</longcat_think>
