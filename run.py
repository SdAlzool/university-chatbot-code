"""تشغيل البوت — واتساب + تيليجرام من مكان واحد (محلي و Render)."""
import logging
import threading


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

    # WhatsApp runs in a background thread (plain HTTP server — no signal handlers).
    # Telegram MUST run in the main thread: python-telegram-bot's asyncio runtime
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
