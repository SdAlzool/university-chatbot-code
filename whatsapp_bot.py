"""WhatsApp bot — HTTP server, webhook, and main entry point."""

import asyncio
import json
import logging
import os
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests
from config import WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN, WHATSAPP_API_VERSION, WHATSAPP_PORT
from whatsapp_api import set_inbound_phone_id
from whatsapp_handlers import process_wa_message


def _handle_webhook_payload(payload):
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value") or {}
                metadata = value.get("metadata") or {}
                if metadata.get("phone_number_id"):
                    set_inbound_phone_id(metadata["phone_number_id"])
                for msg in value.get("messages", []):
                    phone = msg.get("from")
                    if not phone:
                        continue
                    logging.info("WA message from %s type=%s", phone, msg.get("type"))
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(process_wa_message(phone, msg))
                        loop.close()
                    except Exception:
                        logging.exception("Failed to process WA message from %s", phone)
    except Exception:
        logging.exception("Webhook processing failed")


class WAHandler(BaseHTTPRequestHandler):
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
                logging.info("WA VERIFY: mode=%s token=%s challenge_len=%d", mode, token[:10] if token else "", len(challenge))
                if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
                    logging.info("WA webhook verified OK! Sending challenge back.")
                    self._send(200, challenge)
                    return
                if mode or token or challenge:
                    logging.warning("WA verification mismatch: got token=%s expected=%s", token, WHATSAPP_VERIFY_TOKEN[:10] if WHATSAPP_VERIFY_TOKEN else "")
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
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(length)
            payload = json.loads(raw_body or b"{}")
        except Exception:
            logging.exception("Invalid webhook payload")
            payload = {}
        logging.info("WA POST %s (entry=%d)", self.path, len(payload.get("entry", [])))
        self._send(200, "OK")
        threading.Thread(target=_handle_webhook_payload, args=(payload,), daemon=True).start()


def _keep_alive():
    while True:
        time.sleep(600)
        try:
            url = os.environ.get("RENDER_EXTERNAL_URL", "http://127.0.0.1:8445")
            requests.get(f"{url}/health", timeout=10)
            logging.info("Keep-alive ping sent")
        except Exception:
            logging.warning("Keep-alive ping failed")


def main():
    missing = [name for name, value in (
        ("WHATSAPP_TOKEN", WHATSAPP_TOKEN),
        ("WHATSAPP_PHONE_NUMBER_ID", WHATSAPP_PHONE_NUMBER_ID),
        ("WHATSAPP_VERIFY_TOKEN", WHATSAPP_VERIFY_TOKEN),
    ) if not value]
    if missing:
        logging.error("ناقص في Environment Variables: %s", ", ".join(missing))
        return

    logging.info("WA Config: PHONE_ID=%s VERIFY_TOKEN=%s API_VERSION=%s",
                 WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN, WHATSAPP_API_VERSION)

    port = int(os.environ.get("PORT", os.environ.get("WHATSAPP_PORT", str(WHATSAPP_PORT or 8445))))

    ThreadingHTTPServer.allow_reuse_address = True
    ThreadingHTTPServer.daemon_threads = True
    server = None

    try:
        server = ThreadingHTTPServer(("0.0.0.0", port), WAHandler)
        logging.info("WhatsApp webhook started on 0.0.0.0:%s", port)
        logging.info("ENV CHECK: WHATSAPP_TOKEN=%s PHONE_ID=%s VERIFY_TOKEN=%s API_VERSION=%s",
                     "SET" if WHATSAPP_TOKEN else "MISSING",
                     "SET" if WHATSAPP_PHONE_NUMBER_ID else "MISSING",
                     "SET" if WHATSAPP_VERIFY_TOKEN else "MISSING",
                     WHATSAPP_API_VERSION or "MISSING")
        if os.environ.get("RENDER"):
            logging.info("Running on Render.")
            external_url = os.environ.get("RENDER_EXTERNAL_URL")
            if external_url:
                logging.info("Render URL: %s", external_url)
        else:
            logging.info("Local WhatsApp webhook port: %s", port)
            logging.info("Local ngrok command: ngrok http %s", port)

        threading.Thread(target=_keep_alive, daemon=True).start()
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


if __name__ == "__main__":
    main()
