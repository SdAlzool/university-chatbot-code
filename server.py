"""السيرفر الرئيسي — يشغّل واتساب (webhook) + تيليجرام (polling) + keep-alive.

التشغيل:  python server.py   (محلي و Render)
"""

import hashlib
import hmac
import json
import logging
import os
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

from config import (
    WHATSAPP_API_VERSION,
    WHATSAPP_APP_SECRET,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_PORT,
    WHATSAPP_TOKEN,
    WHATSAPP_VERIFY_TOKEN,
)

# Render URL for keep-alive (يجب أن يأتي من بيئة التشغيل حتى لا ندقّ على رابط خدمة أخرى)
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip()


# ============================================================
# HTTP: health check + WhatsApp webhook
# ============================================================

class WAHandler(BaseHTTPRequestHandler):
    webhook_path = os.environ.get("WHATSAPP_WEBHOOK_PATH", "/webhook")
    max_body_size = 1_048_576

    def log_message(self, format, *args):
        logging.info("WA HTTP: %s", format % args)

    def _send(self, code, body):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
            self.wfile.flush()
        except Exception:
            pass

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            logging.info("WA GET path=%s query=%s", self.path, dict(query))

            if WHATSAPP_VERIFY_TOKEN:
                mode = query.get("hub.mode", [""])[0]
                token = query.get("hub.verify_token", [""])[0]
                challenge = query.get("hub.challenge", [""])[0]
                logging.info("WA VERIFY: mode=%s challenge_len=%d", mode, len(challenge))
                if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
                    logging.info("WA webhook verified OK! Sending challenge back.")
                    self._send(200, challenge)
                    return
                if mode or token or challenge:
                    logging.warning("WA verification mismatch")
                    self._send(403, "Forbidden")
                    return

            if self.path in ("/", "/healthz", "/health"):
                self._send(200, "ok")
                return
            self._send(404, "Not Found")
        except Exception:
            logging.exception("WA GET handler error")
            try:
                self._send(500, "Error")
            except Exception:
                pass

    def do_POST(self):
        from whatsapp.bot import handle_webhook_payload

        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != self.webhook_path:
            self._send(404, "Not Found")
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > self.max_body_size:
                self._send(413, "Payload Too Large")
                return
            raw_body = self.rfile.read(length)
            signature = self.headers.get("X-Hub-Signature-256", "")
            if not WHATSAPP_APP_SECRET:
                self._send(503, "Webhook Not Configured")
                return
            expected = "sha256=" + hmac.new(
                WHATSAPP_APP_SECRET.encode(), raw_body, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                self._send(403, "Forbidden")
                return
            payload = json.loads(raw_body)
        except Exception:
            logging.warning("Invalid webhook payload")
            self._send(400, "Bad Request")
            return
        logging.info("WA POST %s (entry=%d)", self.path, len(payload.get("entry", [])))
        self._send(200, "OK")
        threading.Thread(target=handle_webhook_payload, args=(payload,), daemon=True).start()


def run_whatsapp_server():
    """يشغّل سيرفر الـwebhook (يقفل الـthread لحد ما يتوقف)."""
    missing = [name for name, value in (
        ("WHATSAPP_TOKEN", WHATSAPP_TOKEN),
        ("WHATSAPP_PHONE_NUMBER_ID", WHATSAPP_PHONE_NUMBER_ID),
        ("WHATSAPP_VERIFY_TOKEN", WHATSAPP_VERIFY_TOKEN),
        ("WHATSAPP_APP_SECRET", WHATSAPP_APP_SECRET),
    ) if not value]
    if missing:
        # لا نتوقف: يجب أن يعمل السيرفر حتى ينجح health check على Render.
        # رسائل الواتساب نفسها سترفض بـ 503 حتى تُضبط المتغيّرات.
        logging.error("ناقص في Environment Variables: %s — سيتم تشغيل السيرفر بدون معالجة رسائل الواتساب",
                      ", ".join(missing))

    logging.info("WA Config: PHONE_ID=%s API_VERSION=%s",
                 WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_API_VERSION)

    port = int(os.environ.get("PORT", os.environ.get("WHATSAPP_PORT", str(WHATSAPP_PORT or 8445))))

    ThreadingHTTPServer.allow_reuse_address = True
    ThreadingHTTPServer.daemon_threads = True
    server = None

    try:
        server = ThreadingHTTPServer(("0.0.0.0", port), WAHandler)
        logging.info("WhatsApp webhook started on 0.0.0.0:%s", port)
        logging.info("ENV CHECK: WHATSAPP_TOKEN=%s PHONE_ID=%s VERIFY_TOKEN=%s APP_SECRET=%s API_VERSION=%s",
                     "SET" if WHATSAPP_TOKEN else "MISSING",
                     "SET" if WHATSAPP_PHONE_NUMBER_ID else "MISSING",
                     "SET" if WHATSAPP_VERIFY_TOKEN else "MISSING",
                     "SET" if WHATSAPP_APP_SECRET else "MISSING",
                     WHATSAPP_API_VERSION or "MISSING")
        if os.environ.get("RENDER"):
            logging.info("Running on Render.")
            external_url = os.environ.get("RENDER_EXTERNAL_URL")
            if external_url:
                logging.info("Render URL: %s", external_url)
        else:
            logging.info("Local WhatsApp webhook port: %s", port)
            logging.info("Local ngrok command: ngrok http %s", port)

        server.serve_forever()
    except OSError as e:
        logging.exception("Could not start WhatsApp webhook on port %s: %s", port, e)
        raise
    except KeyboardInterrupt:
        logging.info("إيقاف البوت.")
    finally:
        if server is not None:
            try:
                server.server_close()
            except Exception:
                pass


# ============================================================
# Keep-alive + تشغيل كل الخدمات
# ============================================================

def _run_thread(target, name):
    try:
        target()
    except Exception:
        logging.exception("%s thread crashed", name)


def keep_alive():
    """Keep the server awake by pinging every 5 minutes."""
    while True:
        try:
            time.sleep(300)  # 5 minutes (before 15 min sleep timeout)
            response = requests.get(RENDER_URL, timeout=30)
            if response.status_code == 200:
                logging.info("✅ Keep-alive: Server is awake (status %d)", response.status_code)
            else:
                logging.warning("⚠️ Keep-alive: Unexpected status %d", response.status_code)
        except requests.exceptions.Timeout:
            logging.warning("⚠️ Keep-alive: Request timed out")
        except Exception as e:
            logging.error("❌ Keep-alive failed: %s", e)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )

    logging.info("Starting all services...")
    logging.info("Render URL: %s", RENDER_URL)

    # Start keep-alive thread (only on Render when RENDER_EXTERNAL_URL is known)
    if os.getenv("RENDER") and RENDER_URL:
        threading.Thread(target=keep_alive, name="keep-alive", daemon=True).start()
        logging.info("🔄 Keep-alive thread started (every 5 min)")
    elif os.getenv("RENDER"):
        logging.warning("RENDER_EXTERNAL_URL غير مضبوط — تم تعطيل Keep-alive")
    else:
        logging.info("🏠 Running locally - keep-alive disabled")

    # Preload knowledge base
    try:
        from services.firebase_db import get_knowledge_base_text
        kb = get_knowledge_base_text()
        logging.info("KB loaded: %s chars", len(kb))
    except Exception as e:
        logging.warning("KB preload failed: %s", e)

    # WhatsApp webhook — نبدأه أولاً حتى يبقى سيرفر الـHTTP شغّالاً
    # (مهم على Render حتى لا يفشل health check لو تعذّر تشغيل تيليجرام).
    threading.Thread(
        target=_run_thread,
        args=(run_whatsapp_server, "whatsapp"),
        name="whatsapp",
        daemon=False,
    ).start()

    # Telegram runs in the main thread
    try:
        from telegram_bot.bot import main as run_telegram
        run_telegram()
    except Exception:
        logging.exception("telegram crashed")


if __name__ == "__main__":
    main()
