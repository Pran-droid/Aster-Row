from app.agent import SupportAgent


def test_agent_handles_order_lookup_without_exposing_private_fields():
    agent = SupportAgent("knowledge-base")
    response = agent.answer("Where is ORD-1007 and when should it arrive?")
    assert response["tool_used"] == "order_lookup"
    assert response["tool_result"]["found"] is True
    assert "email" not in str(response)
    assert "risk_score" not in str(response)


def test_agent_uses_policy_for_return_window_query():
    agent = SupportAgent("knowledge-base")
    response = agent.answer("How long does a regular customer have to return an unused backpack?")
    assert any("01-returns-policy-current.md" in source for source in response.get("sources", []))
    assert "30" in response["answer"]


def test_agent_flag_conflicting_breeze_tumbler_guidance_and_handoff():
    agent = SupportAgent("knowledge-base")
    response = agent.answer("Can I put the entire Breeze Tumbler in the dishwasher?")
    assert response.get("handoff") is True
    assert any("11-product-care.md" in source for source in response.get("sources", []))
    assert any("12-breeze-tumbler-product-card.md" in source for source in response.get("sources", []))
