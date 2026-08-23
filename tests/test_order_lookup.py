from app.tools import normalize_order_id, order_lookup


def test_normalize_order_id_handles_case_and_whitespace():
    assert normalize_order_id("  ord-1007  ") == "ORD-1007"
    assert normalize_order_id("ord-1007") == "ORD-1007"


def test_order_lookup_returns_safe_fields_for_valid_order():
    result = order_lookup("ORD-1007")
    assert result["order_id"] == "ORD-1007"
    assert result["status"] == "shipped"
    assert result["carrier"] == "UPS"
    assert "customer" not in result
    assert "email" not in str(result)
    assert "risk_score" not in str(result)


def test_order_lookup_handles_cancelled_order_without_stale_eta():
    result = order_lookup("ORD-1004")
    assert result["status"] == "cancelled"
    assert "estimated_delivery" in result
    assert result["estimated_delivery"] is None or result["estimated_delivery"] == "cancelled"


def test_order_lookup_rejects_unknown_order():
    result = order_lookup("ORD-9999")
    assert result["found"] is False
    assert "not found" in result["message"].lower()
