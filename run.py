"""تشغيل البوت — واتساب + تيليجرام من مكان واحد (محلي و Render)."""
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# تشغيل السيرفر في Thread منفصل قبل تشغيل البوت
threading.Thread(target=run_dummy_server, daemon=True).start()




def _run_thread(target, name):
    try:
        target()
    except Exception:
        logging.exception("%s thread crashed", name)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Starting all services...")

    # Preload knowledge base (best effort — does not block startup on failure)
    try:
        from database import get_knowledge_base_text
        kb = get_knowledge_base_text()
        logging.info("KB loaded: %s chars", len(kb))
    except Exception as e:
        logging.warning("KB preload failed: %s", e)

    from whatsapp_bot import main as run_whatsapp
    from main import main as run_telegram

    # WhatsApp webhook is the single HTTP server on Render's PORT. It answers
    # health checks (/ , /health, /healthz) and the Meta webhook. It runs in a
    # background thread (plain HTTP server — no signal handlers).
    #
    # Telegram runs in the main thread: python-telegram-bot's asyncio runtime
    # calls add_signal_handler, which only works in the main thread of the main
    # interpreter (fails on Linux/Render otherwise).
    whatsapp_thread = threading.Thread(target=_run_thread, args=(run_whatsapp, "whatsapp"),
                                       name="whatsapp", daemon=False)
    whatsapp_thread.start()
    try:
        run_telegram()
    except Exception:
        logging.exception("telegram thread crashed")


if __name__ == "__main__":
    main()
