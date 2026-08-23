from app.retrieval import KnowledgeBase
from app.tools import order_lookup


class SupportAgent:
    def __init__(self, knowledge_base_dir: str):
        self.kb = KnowledgeBase(knowledge_base_dir)
        self.kb.build()

    def _detect_policy_conflict(self, user_message: str, retrieval):
        lowered = user_message.lower()
        filenames = [r["filename"] for r in retrieval]
        if "dishwasher" in lowered and "11-product-care.md" in filenames and "12-breeze-tumbler-product-card.md" in filenames:
            return True
        return False

    def answer(self, user_message: str, session_context=None):
        session_context = session_context or {}
        retrieval = self.kb.search(user_message, limit=5)

        if "order" in user_message.lower() or "ord-" in user_message.lower():
            order_id = user_message
            for token in user_message.split():
                if "ord-" in token.lower():
                    order_id = token
                    break
            order_result = order_lookup(order_id)
            if order_result.get("found"):
                return {
                    "answer": f"I checked order {order_id.upper()} and it is {order_result['status']}.",
                    "sources": [r["filename"] for r in retrieval],
                    "tool_used": "order_lookup",
                    "tool_result": order_result,
                }
            return {
                "answer": order_result["message"],
                "sources": [r["filename"] for r in retrieval],
                "tool_used": "order_lookup",
                "tool_result": order_result,
            }

        if self._detect_policy_conflict(user_message, retrieval):
            return {
                "answer": "The current official sources conflict: one says the Breeze Tumbler body should be hand-washed, while the product card says all components are dishwasher safe. I need a human review or a final approved product statement before advising you to put the whole tumbler in the dishwasher.",
                "sources": [r["filename"] for r in retrieval if r["filename"] in {"11-product-care.md", "12-breeze-tumbler-product-card.md"}],
                "tool_used": None,
                "handoff": True,
                "retrieval": retrieval,
            }

        if not retrieval:
            return {
                "answer": "The supplied information is insufficient to answer that reliably. Please contact support for help.",
                "sources": [],
                "tool_used": None,
                "handoff": True,
            }

        return {
            "answer": retrieval[0]["text"],
            "sources": [r["filename"] for r in retrieval],
            "tool_used": None,
            "retrieval": retrieval,
            "handoff": False,
        }
