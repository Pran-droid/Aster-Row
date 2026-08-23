import json
from datetime import datetime, timezone


def log_event(event_name: str, payload: dict):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_name,
        "payload": payload,
    }
    print(json.dumps(record, ensure_ascii=True))
