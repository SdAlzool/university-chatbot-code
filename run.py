"""تشغيل البوت — واتساب + تيليجرام من مكان واحد (محلي و Render)."""

import logging
import threading
import time
import os

# Render URL for keep-alive
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://university-chatbot-code-1.onrender.com/")


def _run_thread(target, name):
    try:
        target()
    except Exception:
        logging.exception("%s thread crashed", name)


def keep_alive():
    """Keep the server awake by pinging every 5 minutes."""
    import requests
    
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

    # Start keep-alive thread (only on Render)
    if os.getenv("RENDER"):
        keep_alive_thread = threading.Thread(
            target=keep_alive,
            name="keep-alive",
            daemon=True,
        )
        keep_alive_thread.start()
        logging.info("🔄 Keep-alive thread started (every 5 min)")
    else:
        logging.info("🏠 Running locally - keep-alive disabled")

    # Preload knowledge base
    try:
        from database import get_knowledge_base_text
        kb = get_knowledge_base_text()
        logging.info("KB loaded: %s chars", len(kb))
    except Exception as e:
        logging.warning("KB preload failed: %s", e)

    from whatsapp_bot import main as run_whatsapp
    from main import main as run_telegram

    # WhatsApp webhook
    whatsapp_thread = threading.Thread(
        target=_run_thread,
        args=(run_whatsapp, "whatsapp"),
        name="whatsapp",
        daemon=False,
    )
    whatsapp_thread.start()

    # Telegram runs in the main thread
    try:
        run_telegram()
    except Exception:
        logging.exception("telegram crashed")


if __name__ == "__main__":
    main()