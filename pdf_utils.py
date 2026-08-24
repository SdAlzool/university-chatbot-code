"""توليد ملف PDF من نص."""
import io
import os
import re

_DIR = os.path.dirname(os.path.abspath(__file__))


def _has_arabic_reshaper():
    try:
        import arabic_reshaper
        return True
    except ImportError:
        return False

HAS_ARABIC = _has_arabic_reshaper()

if HAS_ARABIC:
    import arabic_reshaper
    from bidi.algorithm import get_display

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT_CANDIDATES = [
    os.path.join(_DIR, "fonts", "NotoSansArabic-Regular.ttf"),
    os.path.join(_DIR, "fonts", "NotoSansArabic-Bold.ttf"),
    r"C:\Windows\Fonts\tahoma.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
]

PAGE_W, PAGE_H = A4
MARGIN = 40
BODY_SIZE = 11
LINE_HEIGHT = 16


def _strip_md(text):
    text = re.sub(r"^\s*```(?:\w+)?\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "• ", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text.strip()


def _load_font():
    path = next((p for p in FONT_CANDIDATES if os.path.exists(p)), None)
    if not path:
        return "Helvetica"
    name = f"F{abs(hash(path))}"
    try:
        pdfmetrics.registerFont(TTFont(name, path))
        return name
    except Exception:
        return "Helvetica"


def _reshape(text):
    has_arabic = any("\u0600" <= char <= "\u06ff" for char in text)
    if HAS_ARABIC and has_arabic:
        try:
            # Force RTL paragraph direction so list numbers and punctuation keep their role.
            return get_display(arabic_reshaper.reshape(text), base_dir="R")
        except Exception:
            return text
    return text


def _wrap(text, font_name, font_size, max_width):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    lines = []
    for raw in text.split("\n"):
        raw = raw.strip()
        if not raw:
            lines.append("")
            continue
        current = ""
        for word in raw.split(" "):
            candidate = (current + " " + word).strip() if current else word
            if not current:
                current = word
            else:
                try:
                    w = stringWidth(_reshape(candidate), font_name, font_size)
                except Exception:
                    w = len(candidate) * 6
                if w <= max_width:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
        if current:
            lines.append(current)
    return lines


def text_to_pdf_bytes(text, title="Result"):
    text = _strip_md(text or "")
    title = _strip_md(title or "Result")
    font_name = _load_font()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(title)
    max_width = PAGE_W - 2 * MARGIN

    c.setFont(font_name, 15)
    c.setFillColorRGB(0.12, 0.26, 0.45)
    try:
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN - 10, _reshape(title))
    except Exception:
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN - 10, title)

    c.setFont(font_name, BODY_SIZE)
    c.setFillColorRGB(0, 0, 0)
    y = PAGE_H - MARGIN - 50
    for line in _wrap(text, font_name, BODY_SIZE, max_width):
        if y < MARGIN:
            c.showPage()
            c.setFont(font_name, BODY_SIZE)
            c.setFillColorRGB(0, 0, 0)
            y = PAGE_H - MARGIN
        try:
            c.drawRightString(PAGE_W - MARGIN, y, _reshape(line))
        except Exception:
            c.drawString(MARGIN, y, line)
        y -= LINE_HEIGHT

    c.save()
    buf.seek(0)
    return buf
