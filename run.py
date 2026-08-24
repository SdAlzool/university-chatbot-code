"""تشغيل البوت محلياً — ويب + واتساب + تيليجرام من مكان واحد."""
import logging
import threading
import os


def _run_thread(target, name):
    try:
        target()
    except Exception:
        logging.exception(f"{name} thread crashed")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Starting all services...")

    # Preload knowledge base
    try:
        from database import get_knowledge_base_text
        kb = get_knowledge_base_text()
        logging.info(f"KB loaded: {len(kb)} chars")
    except Exception as e:
        logging.warning(f"KB preload failed: {e}")

    # Start WhatsApp + Web server in background thread
    from whatsapp_bot import main as run_whatsapp
    threading.Thread(
        target=_run_thread, args=(run_whatsapp, "whatsapp+web"),
        daemon=True, name="whatsapp+web",
    ).start()

    port = os.getenv("WHATSAPP_PORT") or "8445"
    logging.info(f"Web chat: http://localhost:{port}/chat")
    logging.info(f"Web main: http://localhost:{port}/web")

    # Start Telegram in foreground
    from main import main as run_telegram
    logging.info("Telegram bot starting...")
    run_telegram()


if __name__ == "__main__":
    main()
