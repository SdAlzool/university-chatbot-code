"""توليد ملف PDF من نص (يدعم التلخيص/الترجمة)."""
import io
import os

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_CANDIDATES = [
    os.path.join(_DIR, "fonts", "NotoSansArabic.ttf"),
    os.path.join(_DIR, "fonts", "NotoSansArabic-Regular.ttf"),
    r"C:\Windows\Fonts\tahoma.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]

PAGE_W, PAGE_H = A4
MARGIN = 40
BODY_SIZE = 11
LINE_HEIGHT = 16


def _load_font():
    path = next((p for p in FONT_CANDIDATES if os.path.exists(p)), None)
    if not path:
        raise RuntimeError("لا يوجد خط عربي متاح في النظام.")
    name = f"ArabicFont{abs(hash(path))}"
    pdfmetrics.registerFont(TTFont(name, path))
    return name


def _reshape(text):
    return get_display(arabic_reshaper.reshape(text))


def _wrap(text, font_name, font_size, max_width):
    lines = []
    for raw in text.split("\n"):
        current = ""
        for word in raw.split(" "):
            candidate = (current + " " + word).strip()
            if not current:
                current = word
            elif stringWidth(_reshape(candidate), font_name, font_size) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return [l for l in lines if l]


def text_to_pdf_bytes(text, title="النتيجة"):
    font_name = _load_font()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(title)
    max_width = PAGE_W - 2 * MARGIN

    c.setFont(font_name, 15)
    c.setFillColorRGB(0.12, 0.26, 0.45)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN - 10, _reshape(title))

    c.setFont(font_name, BODY_SIZE)
    c.setFillColorRGB(0, 0, 0)
    y = PAGE_H - MARGIN - 50
    for line in _wrap(text, font_name, BODY_SIZE, max_width):
        if y < MARGIN:
            c.showPage()
            c.setFont(font_name, BODY_SIZE)
            c.setFillColorRGB(0, 0, 0)
            y = PAGE_H - MARGIN
        c.drawRightString(PAGE_W - MARGIN, y, _reshape(line))
        y -= LINE_HEIGHT

    c.save()
    buf.seek(0)
    return buf
