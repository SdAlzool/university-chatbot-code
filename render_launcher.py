"""تشغيل بوت تيليجرام + بوت واتساب في عملية واحدة للنشر على Render."""
import logging
import os
import threading
import time
import urllib.request


def _run_thread(target, name):
    try:
        target()
    except Exception:
        logging.exception(f"{name} thread crashed")


def _keep_alive():
    port = os.getenv("WHATSAPP_PORT") or os.getenv("PORT") or "8445"
    url = f"http://localhost:{port}/"
    while True:
        time.sleep(600)
        try:
            urllib.request.urlopen(url, timeout=15)
        except Exception:
            pass


def _prewarm():
    try:
        from database import get_knowledge_base_text
        kb = get_knowledge_base_text()
        logging.info(f"KB preloaded: {len(kb)} chars")
    except Exception as e:
        logging.warning(f"KB preload failed: {e}")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Bot starting up...")
    threading.Thread(target=_keep_alive, daemon=True, name="keepalive").start()
    threading.Thread(target=_prewarm, daemon=True, name="prewarm").start()
    from whatsapp_bot import main as run_whatsapp
    threading.Thread(
        target=_run_thread, args=(run_whatsapp, "whatsapp"),
        daemon=True, name="whatsapp",
    ).start()
    from main import main as run_telegram
    logging.info("All services started.")
    run_telegram()


if __name__ == "__main__":
    main()
