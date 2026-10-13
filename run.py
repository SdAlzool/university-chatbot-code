"""نقطة تشغيل Render.

لوحة Render مضبوطة على ``python run.py`` — وهي الأمر القديم الذي كان
مستخدماً قبل إعادة هيكلة المشروع (التي حذفت run.py ونقلت الكود إلى
server.py). هذا الملف مجرد غلاف رفيع يستدعي main() من server.py حتى
لا يفشل النشر إذا بقيت أوامر التشغيل القديمة في لوحة Render.
"""

from server import main

if __name__ == "__main__":
    main()
