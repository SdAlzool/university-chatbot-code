# pdf_utils.py

"""
PDF generation utilities for University Chatbot.

Supports:
- Arabic RTL text
- English text
- Mixed Arabic / English / numbers
- Headings
- Bullet lists
- Numbered lists
- Markdown-style formatting
- Automatic page splitting
- Arabic fonts
- Returning PDF as bytes for Telegram / WhatsApp
"""

import os
import re
import tempfile
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
)

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")

REGULAR_FONT = "NotoSansArabic"
BOLD_FONT = "NotoSansArabic-Bold"

REGULAR_FONT_PATH = os.path.join(
    FONT_DIR,
    "NotoSansArabic-Regular.ttf"
)

BOLD_FONT_PATH = os.path.join(
    FONT_DIR,
    "NotoSansArabic-Bold.ttf"
)


# ============================================================
# FONT REGISTRATION
# ============================================================

def _register_fonts():
    """
    Register Arabic fonts if they exist.
    """

    registered_fonts = pdfmetrics.getRegisteredFontNames()

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

    except Exception:
        return text


def _has_arabic(text):
    return bool(re.search(r"[\u0600-\u06ff]", text or ""))


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
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")

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

    text = escape(text)
    return _prepare_rtl(text) if _has_arabic(text) else text


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

        fontName=bold_font,

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

        fontName=bold_font,

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

        fontName=bold_font,

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

        fontName=bold_font,

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
            fontName="Helvetica",
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

            bullet_text = _format_text(
                value
            )

            content = (
                "• "
                + bullet_text
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

            body = _format_text(
                body
            )

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

            quote = _format_text(
                value
            )

            content = (
                "❝ "
                + quote
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