"""WhatsApp API layer — send messages, media handling."""

import logging
import requests
from config import WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_API_VERSION
from github_utils import download_file_bytes

WA_BASE = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"
WA_MSG_URL = f"{WA_BASE}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
WA_HEADERS = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

_inbound_phone_id = None


def _base():
    return f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"


def _active_phone_id():
    return _inbound_phone_id or WHATSAPP_PHONE_NUMBER_ID


def _msg_url():
    return f"{_base()}/{_active_phone_id()}/messages"


def _media_url():
    return f"{_base()}/{_active_phone_id()}/media"


def set_inbound_phone_id(phone_id):
    global _inbound_phone_id
    _inbound_phone_id = phone_id


def wa_send(payload):
    try:
        response = requests.post(_msg_url(), headers=WA_HEADERS, json=payload, timeout=30)
        if response.status_code not in (200, 201):
            logging.error("WhatsApp send failed (%s): %s", response.status_code, response.text[:500])
        else:
            logging.info("WhatsApp send OK (%s) to=%s", response.status_code, payload.get("to"))
        return response
    except Exception:
        logging.exception("WhatsApp send error")
        return None


def send_text(to, body):
    text = str(body)[:4000]
    logging.info("WA send_text to=%s len=%d", to, len(text))
    return wa_send({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text, "preview_url": False},
    })


def send_buttons(to, body, buttons):
    rows = [{"type": "reply", "reply": {"id": b_id, "title": b_title[:20]}} for b_id, b_title in buttons[:3]]
    if not rows:
        return None
    return wa_send({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": str(body)[:1024]},
            "action": {"buttons": rows},
        },
    })


def send_list(to, body, items, header="", button_text="اختر"):
    rows = [{"id": r_id[:256], "title": r_title[:24], "description": (r_desc or "")[:72]} for r_id, r_title, r_desc in items]
    if not rows:
        return None
    sections = [{"title": f"الخيارات ({i // 10 + 1})", "rows": rows[i:i + 10]} for i in range(0, len(rows), 10)]
    return wa_send({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": str(header)[:60]},
            "body": {"text": str(body)[:1024]},
            "action": {"button": str(button_text)[:20], "sections": sections},
        },
    })


# ============================================================
# Media
# ============================================================

def upload_media(data, mime, filename):
    try:
        response = requests.post(
            _media_url(), headers=WA_HEADERS,
            files={"file": (filename, data, mime)},
            data={"messaging_product": "whatsapp", "type": mime},
            timeout=120,
        )
        if response.status_code != 200:
            logging.error("Media upload failed (%s): %s", response.status_code, response.text[:500])
            return None
        return (response.json() or {}).get("id")
    except Exception:
        logging.exception("Media upload error")
        return None


def get_media_info(media_id):
    try:
        response = requests.get(f"{WA_BASE}/{media_id}", headers=WA_HEADERS, timeout=30)
        return response.json() if response.status_code == 200 else None
    except Exception:
        logging.exception("Media info error")
        return None


def download_media(media_id):
    info = get_media_info(media_id)
    if not info or not info.get("url"):
        return None, None
    try:
        response = requests.get(info["url"], headers=WA_HEADERS, timeout=120)
        if response.status_code != 200:
            return None, info.get("mime_type")
        return response.content, info.get("mime_type")
    except Exception:
        logging.exception("Media download error")
        return None, None


def send_document(to, media_id, filename):
    return wa_send({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "document",
        "document": {"id": media_id, "filename": filename[:240]},
    })


def _guess_mime(filename):
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    return {
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "ppt": "application/vnd.ms-powerpoint",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "zip": "application/zip",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "mp3": "audio/mpeg",
    }.get(ext, "application/octet-stream")


def send_file_from_github(to, file):
    try:
        data = download_file_bytes(file["path"])
        if not data:
            send_text(to, "تعذر تحميل الملف من المستودع.")
            return
        media_id = upload_media(data, _guess_mime(file["name"]), file["name"])
        if not media_id:
            send_text(to, "تعذر رفع الملف إلى واتساب.")
            return
        send_document(to, media_id, file["name"])
    except Exception:
        logging.exception("WhatsApp file send failed")
        send_text(to, "تعذر إرسال الملف الآن.")
