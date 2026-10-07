"""تنسيق رسائل البوت (قوائم الترحيب والمساعدة)."""




# ============================================================
# من الملف الأصلي: formatting.py
# ============================================================


def header(text):
    return f"━━━━━━━━━━━━━━━━━━━━\n{text}\n━━━━━━━━━━━━━━━━━━━━"

def bold(text):
    return f"**{text}**"

def success(text):
    return f"✅ {text}"

def error(text):
    return f"❌ {text}"

def info(text):
    return f"ℹ️ {text}"

def numbered(num, text):
    return f"{num}. {text}"

def menu_item(emoji, title, description=""):
    if description:
        return f"{emoji} {title}\n   {description}"
    return f"{emoji} {title}"

def help_message():
    return f"""
{header("🎓 بوت الخدمات الجامعية")}

أهلاً بك! أنا مساعدك الأكاديمي.

{header("الخدمات")}

{menu_item("💬", "إجابة الاستفسارات", "أسئلة عامة عن الجامعة")}
{menu_item("📄", "تلخيص وترجمة الملفات", "PDF / Word / صور")}
{menu_item("🎙️", "تحويل الصوت إلى نص", "أرسل رسالة صوتية")}
{menu_item("📚", "عرض المقررات والشيتات", "أرسل /login للتسجيل")}

{header("الأوامر")}

/start - بدء المحادثة
/help - عرض هذه الرسالة
/login - تسجيل الدخول
/courses - عرض المقررات
/mycourses - عرض موادي
/sheets - عرض الشيتات
/summarize - تلخيص آخر ملف
/admin - لوحة التحكم (للأدمن)
"""

def student_welcome_menu():
    return f"""
{header("👋 أهلاً بك!")}

اختر ما تريد:
━━━━━━━━━━━━━━━━━━━━
{numbered(1, "❓ سؤال عن الجامعة")}
{numbered(2, "📚 سؤال عن مادة")}
{numbered(3, "📖 موادي")}
━━━━━━━━━━━━━━━━━━━━
"""

def instructor_welcome_menu():
    return f"""
{header("👋 أهلاً أستاذي!")}

اختر ما تريد:
━━━━━━━━━━━━━━━━━━━━
{numbered(1, "📚 عرض المواد")}
{numbered(2, "➕ إضافة مادة")}
{numbered(3, "🗑️ حذف مادة")}
━━━━━━━━━━━━━━━━━━━━
"""

def my_courses_list(courses):
    if not courses:
        return header("📚 موادي") + "\n\n" + info("لا توجد مواد مسجلة لك")
    lines = [header("📚 موادي"), ""]
    for i, course in enumerate(courses, 1):
        lines.append(numbered(i, course.get("name", "مادة")))
    return "\n".join(lines)

def add_content_prompt():
    return f"""
{header("➕ إضافة محتوى")}

اختر نوع المادة:
━━━━━━━━━━━━━━━━━━━━
{numbered(1, "مادة موجودة")}
{numbered(2, "مادة جديدة")}
━━━━━━━━━━━━━━━━━━━━
"""

def guest_menu():
    return f"""
{header("👤 مرحباً بك كزائر!")}

يمكنك الآن:
━━━━━━━━━━━━━━━━━━━━
💬 طرح أسئلة عن الجامعة
📄 إرسال ملف لتلخيصه أو ترجمته
🎙️ إرسال رسالة صوتية
━━━━━━━━━━━━━━━━━━━━

للوصول للمقررات والشيتات سجّل الدخول
"""
