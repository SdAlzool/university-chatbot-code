"""معالجة رسائل واتساب الواردة من الـwebhook."""

import asyncio
import logging

from config import WHATSAPP_PHONE_NUMBER_ID
from whatsapp.handlers import process_wa_message


def handle_webhook_payload(payload):
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value") or {}
                metadata = value.get("metadata") or {}
                inbound_phone_id = metadata.get("phone_number_id")
                if inbound_phone_id and inbound_phone_id != WHATSAPP_PHONE_NUMBER_ID:
                    logging.warning("Ignoring webhook for unexpected phone_number_id=%s", inbound_phone_id)
                    continue
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
