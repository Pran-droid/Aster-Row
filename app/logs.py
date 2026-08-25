import json
from datetime import datetime, timezone

from app.config import DEBUG


PRIVATE_KEYS = {"email", "address", "shipping_address", "risk_score", "internal", "warehouse_note"}


def _sanitize(value):
    if isinstance(value, dict):
        return {
            key: "[redacted]" if key in PRIVATE_KEYS else _sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def log_event(event_name: str, payload: dict):
    if not DEBUG:
        return
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_name,
        "payload": _sanitize(payload),
    }
    print(json.dumps(record, ensure_ascii=True))
