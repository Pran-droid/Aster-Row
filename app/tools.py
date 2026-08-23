import json
import re
from pathlib import Path

from app.config import ORDERS_PATH


SAFE_ORDER_FIELDS = {
    "order_id",
    "membership_tier",
    "items",
    "placed_at",
    "status",
    "status_updated_at",
    "shipped_at",
    "delivered_at",
    "carrier",
    "tracking_number",
    "estimated_delivery",
    "customer_safe_message",
}


def normalize_order_id(raw_order_id: str) -> str:
    if raw_order_id is None:
        return ""
    cleaned = str(raw_order_id).strip().upper()
    cleaned = re.sub(r"[^A-Z0-9-]", "", cleaned)
    return cleaned


def _load_orders() -> list:
    with ORDERS_PATH.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("orders", [])


def _safe_order_record(order: dict) -> dict:
    safe = {}
    for field in SAFE_ORDER_FIELDS:
        if field in order:
            safe[field] = order[field]
    if "items" in safe and isinstance(safe["items"], list):
        safe["items"] = [
            {"name": item.get("name"), "quantity": item.get("quantity"), "final_sale": item.get("final_sale")}
            for item in safe["items"]
        ]
    return safe


def order_lookup(order_id: str) -> dict:
    normalized = normalize_order_id(order_id)
    if not normalized:
        return {
            "found": False,
            "message": "I need an order ID before I can look up an order.",
            "requires_id": True,
        }

    orders = _load_orders()
    for order in orders:
        if order.get("order_id") == normalized:
            safe = _safe_order_record(order)
            status = order.get("status")
            if status in {"cancelled", "returned"}:
                safe["estimated_delivery"] = None
            elif status == "shipped" and order.get("estimated_delivery") is None:
                safe["estimated_delivery"] = None
            return {
                "found": True,
                "message": f"Order {normalized} was found.",
                **safe,
            }

    return {
        "found": False,
        "message": f"Order {normalized} was not found. Please check the order ID or contact support.",
        "requires_id": False,
    }
