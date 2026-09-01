"""WhatsApp session state management."""

import threading

_state_lock = threading.Lock()
_wa_state = {}


def get_state(phone):
    with _state_lock:
        return _wa_state.setdefault(phone, {
            "state": None,
            "data": {},
            "last_file": None,
            "pending_files": [],
            "welcome_sent": False,
        })


def reset_state(phone):
    with _state_lock:
        old = _wa_state.get(phone, {})
        _wa_state[phone] = {
            "state": None,
            "data": {},
            "last_file": old.get("last_file"),
            "pending_files": [],
            "welcome_sent": old.get("welcome_sent", True),
        }
