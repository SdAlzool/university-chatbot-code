"""توليد PDF (عربي RTL) + استخراج النص من PDF."""

import io
import os
import re
import tempfile
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


# ============================================================
# من الملف الأصلي: pdf_utils.py
# ============================================================
# pdf_utils.py


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # جذر المشروع (فيه مجلد fonts)
FONT_DIR = os.path.join(BASE_DIR, "fonts")

# IBM Plex Sans Arabic يغطي العربي + اللاتيني + الترقيم معاً.
# (كان NotoSansArabic خط "مبتذّر" عربي فقط: صفر حروف لاتينية،
#  فأي سطر يخلط عربي + إنجليزي كان يطلع مربعات سوداء.)
REGULAR_FONT = "IBMPlexSansArabic"
BOLD_FONT = "IBMPlexSansArabic-Bold"

REGULAR_FONT_PATH = os.path.join(
    FONT_DIR,
    "IBMPlexSansArabic-Regular.ttf"
)

BOLD_FONT_PATH = os.path.join(
    FONT_DIR,
    "IBMPlexSansArabic-Bold.ttf"
)


# ============================================================
# FONT REGISTRATION
# ============================================================

def _register_fonts():
    """
    Register Arabic fonts if they exist.
    """

    registered_fonts = pdfmetrics.getRegisteredFontNames()

    missing = [
        path for path in (REGULAR_FONT_PATH, BOLD_FONT_PATH)
        if not os.path.exists(path)
    ]
    if missing:
        print(f"[PDF] Missing Arabic font file(s): {', '.join(missing)} — سيُستبدل بخط Helvetica")

    try:
        if (
            REGULAR_FONT not in registered_fonts
            and os.path.exists(REGULAR_FONT_PATH)
        ):
            pdfmetrics.registerFont(
                TTFont(
                    REGULAR_FONT,
                    REGULAR_FONT_PATH
                )
            )

        if (
            BOLD_FONT not in registered_fonts
            and os.path.exists(BOLD_FONT_PATH)
        ):
            pdfmetrics.registerFont(
                TTFont(
                    BOLD_FONT,
                    BOLD_FONT_PATH
                )
            )

    except Exception as e:
        print(f"[PDF] Font registration warning: {e}")


_register_fonts()


def _get_font(font_name=REGULAR_FONT):
    """
    Return the requested font if registered.
    Otherwise fallback to Helvetica.
    """

    registered_fonts = pdfmetrics.getRegisteredFontNames()

    if font_name in registered_fonts:
        return font_name

    return "Helvetica"


# ============================================================
# ARABIC RTL SUPPORT
# ============================================================

def _prepare_rtl(text):
    """
    Improve Arabic RTL rendering when arabic-reshaper
    and python-bidi are installed.

    The PDF still works without them.
    """

    if not text:
        return ""

    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        reshaped = arabic_reshaper.reshape(text)

        return get_display(reshaped, base_dir="R")

    except Exception as e:
        # نسجل السبب بدل ما نصمت — كانت الأخطاء تخفي نفسها
        # وتسبب نص عربي غير مُشكّل.
        print(f"[PDF] RTL reshape failed: {type(e).__name__}: {e}")
        return text


def _has_arabic(text):
    return bool(re.search(r"[\u0600-\u06ff]", text or ""))


# ============================================================
# GLYPH COVERAGE / SANITIZING
# ============================================================

# محارف شائعة في مخرجات Gemini غير متوفرة في الخط ->
# نستبدلها ببديل متوفر بدل ما تطلع مربع أسود.
# ملاحظة: الإيموجي فوق U+FFFF مفتاحه \U (8 خانات) وليس \u (4 خانات).
_CHAR_MAP = {
    # اقتباسات
    "\u275d": "\u00ab",    # ❝  -> «
    "\u275e": "\u00bb",    # ❞  -> »
    # علامات صح/خطأ
    "\u2705": "\u2713",    # ✅  -> ✓
    "\u274c": "\u00d7",    # ❌  -> ×
    "\u274e": "\u00d7",    # ❎
    "\u2714": "\u2713",    # ✔  -> ✓
    "\u2718": "\u00d7",    # ✘  -> ×
    "\u2716": "\u00d7",    # ✖
    "\u2611": "\u2713",    # ☑
    # تنبيهات وسهام
    "\u26a0": "!",         # ⚠  -> !
    "\u27a1": "\u2192",    # ➡  -> →
    "\u2b05": "\u2190",    # ⬅
    "\u2757": "!",         # ❗
    "\u2753": "?",         # ❓
    "\u203c": "!!",        # ‼
    "\u2049": "!",         # ⁉
    "\u2139": "i",         # ℹ
    # رموز عامة
    "\u2026": "...",       # …
    "\u2122": "TM",        # ™
    "\u00ae": "(R)",       # ®
    "\u00a9": "(C)",       # ©
    # نقاط زخرفية
    "\u25aa": "\u2022",    # ▪
    "\u25e6": "\u2022",    # ◦
    "\u25cf": "\u2022",    # ●
    "\u25cb": "\u2022",    # ○
    "\u2726": "\u2022",    # ✦
    "\u2727": "\u2022",    # ✧
    "\u2605": "\u2022",    # ★
    "\u2606": "\u2022",    # ☆
    "\u2b50": "\u2022",    # ⭐
    "\u2764": "\u2022",    # ❤
    # رياضيات ومنطق (مهمة جداً لمواد نظرية الحوسبة)
    "\u21d2": " => ",      # ⇒
    "\u21d0": " <= ",      # ⇐
    "\u21d4": " <=> ",     # ⇔
    "\u2208": " in ",      # ∈
    "\u2209": " not in ",  # ∉
    "\u2286": " sub ",     # ⊆
    "\u2287": " sup ",     # ⊇
    "\u222a": " U ",       # ∪
    "\u2229": " N ",       # ∩
    "\u2205": " {} ",      # ∅
    "\u2200": " for all ", # ∀
    "\u2203": " exists ",  # ∃
    "\u2227": " AND ",     # ∧
    "\u2228": " OR ",      # ∨
    "\u2202": " d/dx ",    # ∂
    "\u221b": " cuberoot ",# ∛
    # إيموجي شائعة في مخرجات Gemini
    "\U0001f4cc": "\u2022",  # 📌
    "\U0001f3af": "\u2022",  # 🎯
    "\U0001f4a1": "\u2022",  # 💡
    "\U0001f534": "\u2022",  # 🔴
    "\U0001f7e2": "\u2022",  # 🟢
    "\U0001f7e1": "\u2022",  # 🟡
    "\U0001f4d6": "\u2022",  # 📖
    "\U0001f4dd": "\u2022",  # 📝
    "\U0001f512": "\u2022",  # 🔒
    "\U0001f511": "\u2022",  # 🔑
    "\U0001f680": "\u2022",  # 🚀
    "\U0001f4e6": "\u2022",  # 📦
    "\U0001f4ca": "\u2022",  # 📊
    "\U0001f535": "\u2022",  # 🔵
    "\U0001f7e3": "\u2022",  # 🟣
    "\U0001f7e0": "\u2022",  # 🟠
    "\U0001f947": "\u2022",  # 🥇
    "\U0001f4aa": "\u2022",  # 💪
    "\U0001f642": "\u2022",  # 🙂
    "\U0001f60a": "\u2022",  # 😊
    "\U0001f622": "\u2022",  # 😢
    "\U0001f621": "\u2022",  # 😡
    "\U0001f914": "\u2022",  # 🤔
    "\U0001f44d": "\u2022",  # 👍
    "\U0001f44e": "\u2022",  # 👎
    "\U0001f446": "\u2022",  # 👆
    "\U0001f447": "\u2022",  # 👇
    "\U0001f525": "\u2022",  # 🔥
    "\U0001f31f": "\u2022",  # 🌟
    "\U0001f4cd": "\u2022",  # 📍
    "\U0001f4c5": "\u2022",  # 📅
    "\U0001f4c6": "\u2022",  # 📆
    "\U0001f4b0": "\u2022",  # 💰
    "\U0001f9e0": "\u2022",  # 🧠
    "\U0001f4bb": "\u2022",  # 💻
    "\U0001f4f1": "\u2022",  # 📱
    "\U0001f4e2": "\u2022",  # 📢
    "\u2795": "\u00d7",     # ➕
    "\u2796": "\u00d7",     # ➖
    "\u274a": "\u2713",     # ❊
    "\u2709": "\u2022",     # ✉
    "\u2706": "\u2022",     # ✆
    "\u2708": "\u2022",     # ✈
    "\u2600": "\u2022",     # ☀
    "\u2601": "\u2022",     # ☁
    "\u2614": "\u2022",     # ☔
    "\u26a1": "!",          # ⚡
    "\u2603": "\u2022",     # ☃
}

# محارف صفرية/اتجاه لا يُنظر إليها كنص أبداً.
_INVISIBLE = (
    "\u200b"  # zero width space
    "\u200c"  # zero width non-joiner
    "\u200d"  # zero width joiner
    "\u200e"  # left-to-right mark
    "\u200f"  # right-to-left mark
    "\u061c"  # arabic letter mark
    "\ufeff"  # BOM
    "\ufe0f"  # variation selector-16
    "\ufe0e"
    "\u00ad"  # soft hyphen
)

_coverage_cache = None


def _font_coverage():
    """
    المحارف المتوفرة فعلياً في الخطين المسجّلين (Regular + Bold).

    نأخذ التقاطع حتى يكون النص آمناً في كل الأنماط.
    """

    global _coverage_cache

    if _coverage_cache is not None:
        return _coverage_cache

    sets = []

    for font_name in (REGULAR_FONT, BOLD_FONT):
        try:
            face = pdfmetrics.getFont(font_name).face
        except Exception:
            continue

        char_to_glyph = getattr(face, "charToGlyph", None)
        if char_to_glyph:
            sets.append(set(char_to_glyph.keys()))

    if not sets:
        _coverage_cache = set()
        return _coverage_cache

    _coverage_cache = set.intersection(*sets)
    return _coverage_cache


def _sanitize_glyphs(text):
    """
    يحذف/يستبدل أي حرف غير متوفر في الخط.

    بدون هذا تظهر مربعات سوداء (tofu) لأي رمز أو إيموجي
    يكتبه Gemini ولا يحتوي عليه الخط.
    """

    if not text:
        return text

    coverage = _font_coverage()
    if not coverage:
        return text

    out = []

    for ch in text:
        code = ord(ch)

        if code in coverage:
            out.append(ch)
            continue

        replacement = _CHAR_MAP.get(ch)

        if replacement and all(ord(c) in coverage for c in replacement):
            out.append(replacement)
            continue

        # لا يوجد بديل -> نحذفه بدل مربع أسود.

    return "".join(out)


# ============================================================
# MARKDOWN CLEANING
# ============================================================

def _clean_markdown(text):
    """
    Remove Markdown syntax while keeping the actual content.
    """

    if not text:
        return ""

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove invisible characters
    for _ch in _INVISIBLE:
        text = text.replace(_ch, "")

    # Keep equations readable when Gemini returns LaTeX markup.
    text = re.sub(r"\\begin\{(?:aligned|align)\}|\\end\{(?:aligned|align)\}", "", text)
    text = re.sub(r"\\(?:text|mathbf|mathrm|operatorname)\{([^{}]*)\}", r"\1", text)
    text = text.replace("$$", "")
    text = text.replace("\\rightarrow", " -> ")
    text = text.replace("\\Rightarrow", " => ")
    text = text.replace("\\mid", " | ")
    text = text.replace("\\quad", " ")
    text = text.replace("\\dots", "...")
    text = re.sub(r"\\([{}])", r"\1", text)

    # Code blocks
    text = re.sub(
        r"```(?:[\w+-]+)?",
        "",
        text
    )

    text = text.replace("```", "")

    # Markdown links
    text = re.sub(
        r"\[([^\]]+)\]\([^)]+\)",
        r"\1",
        text
    )

    # Bold
    text = re.sub(
        r"\*\*(.*?)\*\*",
        r"\1",
        text
    )

    text = re.sub(
        r"__(.*?)__",
        r"\1",
        text
    )

    # Italic
    text = re.sub(
        r"(?<!\*)\*([^*\n]+)\*(?!\*)",
        r"\1",
        text
    )

    text = re.sub(
        r"(?<!_)_([^_\n]+)_(?!_)",
        r"\1",
        text
    )

    # Inline code
    text = re.sub(
        r"`([^`]+)`",
        r"\1",
        text
    )

    # Horizontal lines
    text = re.sub(
        r"^\s*([-*_])(?:\s*\1){2,}\s*$",
        "",
        text,
        flags=re.MULTILINE
    )

    return text.strip()


# ============================================================
# LINE DETECTION
# ============================================================

def _detect_line_type(line):
    """
    Detect whether a line is:
    - heading1
    - heading2
    - heading3
    - bullet
    - numbered
    - quote
    - paragraph
    - blank
    """

    stripped = line.strip()

    if not stripped:
        return "blank", ""

    # Heading #
    match = re.match(
        r"^#\s+(.+)$",
        stripped
    )

    if match:
        return "heading1", match.group(1).strip()

    # Heading ##
    match = re.match(
        r"^##\s+(.+)$",
        stripped
    )

    if match:
        return "heading2", match.group(1).strip()

    # Heading ### / #### / etc.
    match = re.match(
        r"^#{3,6}\s+(.+)$",
        stripped
    )

    if match:
        return "heading3", match.group(1).strip()

    # Bullet list
    match = re.match(
        r"^(?:[-*•▪◦])\s+(.+)$",
        stripped
    )

    if match:
        return "bullet", match.group(1).strip()

    # Numbered list
    match = re.match(
        r"^(\d+)[.)-]\s+(.+)$",
        stripped
    )

    if match:
        return (
            "numbered",
            (
                match.group(1),
                match.group(2).strip()
            )
        )

    # Quote
    match = re.match(
        r"^>\s*(.+)$",
        stripped
    )

    if match:
        return "quote", match.group(1).strip()

    return "paragraph", stripped


# ============================================================
# TEXT PREPARATION
# ============================================================

def _format_text(text):
    """
    Prepare text safely for ReportLab Paragraph.
    """

    text = _clean_markdown(text)

    # تنقية قبل التشكيل حتى تمرّ البدائل عبر خوارزمية الاتجاه
    # وتُرتب صحيحاً داخل النص العربي.
    text = _sanitize_glyphs(text)

    if _has_arabic(text):
        text = _prepare_rtl(text)

    # escape() لازم يجي AFTER التشكيل: علامة & حيادية في خوارزمية
    # الاتجاه، فلو جأت قبلها تتفكك الـ Entities
    # (&amp; يتحول إلى ;amp&) ويظهر النص الحرف بحرف.
    text = escape(text)

    # تنقية ثانية بعد التشكيل (أمان إضافي لأي شكل عرض ناقص).
    return _sanitize_glyphs(text)


def _style_for_text(styles, style_name, text):
    if _has_arabic(text):
        return styles[style_name]
    style = styles.get(f"{style_name}_english")
    return style or styles[style_name]


# ============================================================
# PDF STYLES
# ============================================================

def _create_styles():

    base_styles = getSampleStyleSheet()

    regular_font = _get_font(
        REGULAR_FONT
    )

    bold_font = _get_font(
        BOLD_FONT
    )

    styles = {}

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    styles["title"] = ParagraphStyle(
        "PDFTitle",

        parent=base_styles["Title"],

        fontName=bold_font,

        fontSize=19,

        leading=27,

        alignment=TA_CENTER,

        textColor=colors.HexColor(
            "#1F2937"
        ),

        spaceAfter=8 * mm,
    )

    # --------------------------------------------------------
    # HEADING 1
    # --------------------------------------------------------

    styles["heading1"] = ParagraphStyle(
        "PDFHeading1",

        parent=base_styles["Heading1"],

        fontName=bold_font,

        fontSize=16,

        leading=23,

        alignment=TA_RIGHT,

        textColor=colors.HexColor(
            "#111827"
        ),

        spaceBefore=6 * mm,

        spaceAfter=3 * mm,
    )

    # --------------------------------------------------------
    # HEADING 2
    # --------------------------------------------------------

    styles["heading2"] = ParagraphStyle(
        "PDFHeading2",

        parent=base_styles["Heading2"],

        fontName=bold_font,

        fontSize=14,

        leading=21,

        alignment=TA_RIGHT,

        textColor=colors.HexColor(
            "#1F2937"
        ),

        spaceBefore=5 * mm,

        spaceAfter=2.5 * mm,
    )

    # --------------------------------------------------------
    # HEADING 3
    # --------------------------------------------------------

    styles["heading3"] = ParagraphStyle(
        "PDFHeading3",

        parent=base_styles["Heading3"],

        fontName=bold_font,

        fontSize=12.5,

        leading=19,

        alignment=TA_RIGHT,

        textColor=colors.HexColor(
            "#374151"
        ),

        spaceBefore=4 * mm,

        spaceAfter=2 * mm,
    )

    # --------------------------------------------------------
    # NORMAL PARAGRAPH
    # --------------------------------------------------------

    styles["body"] = ParagraphStyle(
        "PDFBody",

        parent=base_styles["BodyText"],

        fontName=regular_font,

        fontSize=11,

        leading=20,

        alignment=TA_RIGHT,

        rightIndent=0,

        leftIndent=0,

        firstLineIndent=0,

        spaceAfter=3 * mm,

        wordWrap=None,
    )

    # --------------------------------------------------------
    # BULLET
    # --------------------------------------------------------

    styles["bullet"] = ParagraphStyle(
        "PDFBullet",

        parent=base_styles["BodyText"],

        fontName=regular_font,

        fontSize=11,

        leading=20,

        alignment=TA_RIGHT,

        rightIndent=7 * mm,

        leftIndent=0,

        firstLineIndent=-5 * mm,

        spaceAfter=1.8 * mm,

        wordWrap=None,
    )

    # --------------------------------------------------------
    # NUMBERED
    # --------------------------------------------------------

    styles["numbered"] = ParagraphStyle(
        "PDFNumbered",

        parent=base_styles["BodyText"],

        fontName=regular_font,

        fontSize=11,

        leading=20,

        alignment=TA_RIGHT,

        rightIndent=8 * mm,

        leftIndent=0,

        firstLineIndent=-8 * mm,

        spaceAfter=1.8 * mm,

        wordWrap=None,
    )

    # --------------------------------------------------------
    # QUOTE
    # --------------------------------------------------------

    styles["quote"] = ParagraphStyle(
        "PDFQuote",

        parent=base_styles["BodyText"],

        fontName=regular_font,

        fontSize=10.5,

        leading=19,

        alignment=TA_RIGHT,

        rightIndent=8 * mm,

        leftIndent=4 * mm,

        textColor=colors.HexColor(
            "#4B5563"
        ),

        spaceBefore=2 * mm,

        spaceAfter=3 * mm,

        wordWrap=None,
    )


    for style_name in ("title", "heading1", "heading2", "heading3", "body", "bullet", "numbered", "quote"):
        styles[f"{style_name}_english"] = ParagraphStyle(
            f"PDF{style_name.title()}English",
            parent=styles[style_name],
            # خط الوالد بدل Helvetica: Helvetica لا يحتوي → ✓ ⇒ وغيرها
            # فكانت تظهر مربعات سوداء في السطور الإنجليزية.
            fontName=styles[style_name].fontName,
            alignment=TA_CENTER if style_name == "title" else 0,
            wordWrap=None,
            rightIndent=0,
            leftIndent=0,
            firstLineIndent=0,
        )

    return styles


# ============================================================
# PAGE NUMBER
# ============================================================

def _add_page_number(canvas, doc):

    canvas.saveState()

    font = _get_font(
        REGULAR_FONT
    )

    canvas.setFont(
        font,
        8.5
    )

    page_number = str(
        doc.page
    )

    canvas.drawCentredString(
        A4[0] / 2,
        10 * mm,
        page_number
    )

    canvas.restoreState()


# ============================================================
# CREATE PDF
# ============================================================

def create_pdf(
    text,
    output_path,
    title="ملخص"
):
    """
    Create a properly formatted PDF.

    Parameters
    ----------
    text:
        Summary / translation text.

    output_path:
        Where the PDF should be saved.

    title:
        PDF title.
    """

    if not text:
        raise ValueError(
            "لا يوجد نص لإنشاء ملف PDF."
        )

    text = str(text).strip()

    if not text:
        raise ValueError(
            "النص فارغ."
        )

    _register_fonts()

    output_path = os.path.abspath(
        output_path
    )

    output_directory = os.path.dirname(
        output_path
    )

    if output_directory:
        os.makedirs(
            output_directory,
            exist_ok=True
        )

    styles = _create_styles()

    document = SimpleDocTemplate(

        output_path,

        pagesize=A4,

        rightMargin=18 * mm,

        leftMargin=18 * mm,

        topMargin=18 * mm,

        bottomMargin=17 * mm,

        title=title,

        author="University Chatbot",

        allowSplitting=1,
    )

    story = []

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    if title:

        story.append(
            Paragraph(
                _format_text(title),
                _style_for_text(styles, "title", title)
            )
        )

        story.append(
            Spacer(
                1,
                2 * mm
            )
        )

    # --------------------------------------------------------
    # PROCESS TEXT
    # --------------------------------------------------------

    text = text.replace(
        "\r\n",
        "\n"
    )

    text = text.replace(
        "\r",
        "\n"
    )

    lines = text.split("\n")

    for line in lines:

        line_type, value = _detect_line_type(
            line
        )

        # ----------------------------------------------------
        # BLANK LINE
        # ----------------------------------------------------

        if line_type == "blank":

            story.append(
                Spacer(
                    1,
                    2.5 * mm
                )
            )

            continue

        # ----------------------------------------------------
        # HEADING 1
        # ----------------------------------------------------

        if line_type == "heading1":

            story.append(
                Paragraph(
                    _format_text(value),
                    _style_for_text(styles, "heading1", value)
                )
            )

            continue

        # ----------------------------------------------------
        # HEADING 2
        # ----------------------------------------------------

        if line_type == "heading2":

            story.append(
                Paragraph(
                    _format_text(value),
                    _style_for_text(styles, "heading2", value)
                )
            )

            continue

        # ----------------------------------------------------
        # HEADING 3
        # ----------------------------------------------------

        if line_type == "heading3":

            story.append(
                Paragraph(
                    _format_text(value),
                    _style_for_text(styles, "heading3", value)
                )
            )

            continue

        # ----------------------------------------------------
        # BULLET
        # ----------------------------------------------------

        if line_type == "bullet":

            # ننسّق مرة واحدة فقط — استدعاء _format_text مرتين
            # كان يكرّر escape() فتظهر "&amp;" داخل الملف.
            content = (
                "• "
                + value
            )

            story.append(
                Paragraph(
                    _format_text(content),
                    _style_for_text(styles, "bullet", content)
                )
            )

            continue

        # ----------------------------------------------------
        # NUMBERED
        # ----------------------------------------------------

        if line_type == "numbered":

            number, body = value

            # تنسيق واحد فقط (انظر ملاحظة البوليت).
            content = (
                f"{number}. "
                + body
            )

            story.append(
                Paragraph(
                    _format_text(content),
                    _style_for_text(styles, "numbered", content)
                )
            )

            continue

        # ----------------------------------------------------
        # QUOTE
        # ----------------------------------------------------

        if line_type == "quote":

            # ❝ (U+275D) غير متوفر في الخط -> كان يطلع مربع أسود.
            content = (
                "« "
                + value
                + " »"
            )

            story.append(
                Paragraph(
                    _format_text(content),
                    _style_for_text(styles, "quote", content)
                )
            )

            continue

        # ----------------------------------------------------
        # NORMAL PARAGRAPH
        # ----------------------------------------------------

        story.append(
            Paragraph(
                _format_text(value),
                _style_for_text(styles, "body", value)
            )
        )

    # --------------------------------------------------------
    # BUILD
    # --------------------------------------------------------

    document.build(
        story,

        onFirstPage=_add_page_number,

        onLaterPages=_add_page_number,
    )

    return output_path


# ============================================================
# PDF AS BYTES
# ============================================================

def text_to_pdf_bytes(
    text,
    title="ملخص"
):
    """
    Create a PDF and return it as bytes.

    This function is important because handlers/file_tools.py
    imports it directly:

        from pdf_utils import text_to_pdf_bytes

    So do NOT remove or rename this function.
    """

    if not text:
        raise ValueError(
            "لا يوجد نص لإنشاء ملف PDF."
        )

    temporary_file = None

    try:

        # Create temporary PDF path
        file_descriptor, temporary_file = tempfile.mkstemp(
            suffix=".pdf"
        )

        os.close(
            file_descriptor
        )

        # Generate PDF
        create_pdf(
            text=text,

            output_path=temporary_file,

            title=title,
        )

        # Read PDF as bytes
        with open(
            temporary_file,
            "rb"
        ) as pdf_file:

            pdf_bytes = pdf_file.read()

        return pdf_bytes

    finally:

        # Delete temporary file
        if (
            temporary_file
            and os.path.exists(
                temporary_file
            )
        ):

            try:

                os.remove(
                    temporary_file
                )

            except Exception:
                pass


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def generate_pdf(
    text,
    output_path,
    title="ملخص"
):
    """
    Backward-compatible wrapper.
    """

    return create_pdf(
        text=text,

        output_path=output_path,

        title=title,
    )


def text_to_pdf(
    text,
    output_path,
    title="ملخص"
):
    """
    Backward-compatible wrapper.
    """

    return create_pdf(
        text=text,

        output_path=output_path,

        title=title,
    )

# ============================================================
# من الملف الأصلي: utils.py
# ============================================================


def extract_pdf_text(pdf_bytes):
    pdf_file = io.BytesIO(pdf_bytes)
    reader = PdfReader(pdf_file)
    full_text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            full_text += extracted + "\n"
    return full_text
