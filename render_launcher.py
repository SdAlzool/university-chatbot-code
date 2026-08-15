"""تشغيل بوت تيليجرام (تصويت) + بوت واتساب (ويب هوك) في عملية واحدة للنشر على Render."""
import logging
import threading


def _run_thread(target, name):
    try:
        target()
    except Exception:
        logging.exception(f"{name} thread crashed")


def main():
    from whatsapp_bot import main as run_whatsapp
    threading.Thread(
        target=_run_thread, args=(run_whatsapp, "whatsapp"),
        daemon=True, name="whatsapp",
    ).start()
    from main import main as run_telegram
    run_telegram()


if __name__ == "__main__":
    main()
