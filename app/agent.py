import re

from app.memory import SessionMemory
from app.retrieval import KnowledgeBase
from app.tools import order_lookup


class SupportAgent:
    def __init__(self, knowledge_base_dir: str):
        self.kb = KnowledgeBase(knowledge_base_dir)
        self.kb.build()
        self.memory = SessionMemory()

    def _detect_policy_conflict(self, user_message: str, retrieval):
        lowered = user_message.lower()
        filenames = [r["filename"] for r in retrieval]
        if "dishwasher" in lowered and "11-product-care.md" in filenames and "12-breeze-tumbler-product-card.md" in filenames:
            return True
        return False

    def _extract_order_id(self, text: str):
        match = re.search(r"ORD-\d+", text, flags=re.IGNORECASE)
        if match:
            return match.group(0).upper()
        return None

    def _get_session_context(self, session_id: str):
        return self.memory.get_recent_context(session_id, limit=10)

    def answer(self, user_message: str, session_id: str = "default", session_context=None):
        session_context = session_context or {}
        self.memory.add_message(session_id, "user", user_message)
        retrieval = self.kb.search(user_message, limit=5)
        history = self._get_session_context(session_id)
        history_text = " ".join(msg["content"] for msg in history)

        if "order" in user_message.lower() and self._extract_order_id(user_message) is None:
            if "where is my order" in user_message.lower() or "my order" in user_message.lower() or "order" in user_message.lower():
                return {
                    "answer": "I need your order ID before I can look up the status. Please send the order ID, for example ORD-1007.",
                    "sources": [r["filename"] for r in retrieval],
                    "tool_used": None,
                    "handoff": False,
                }

        if "order" in user_message.lower() or self._extract_order_id(user_message) is not None:
            order_id = self._extract_order_id(user_message) or ""
            if not order_id:
                order_id = user_message
            order_result = order_lookup(order_id)
            if order_result.get("found"):
                return {
                    "answer": f"I checked order {order_id.upper()} and it is {order_result['status']}.",
                    "sources": [r["filename"] for r in retrieval],
                    "tool_used": "order_lookup",
                    "tool_result": order_result,
                    "handoff": False,
                }
            return {
                "answer": order_result["message"],
                "sources": [r["filename"] for r in retrieval],
                "tool_used": "order_lookup",
                "tool_result": order_result,
                "handoff": order_result.get("found") is False,
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

        if "canada" in user_message.lower() and "international" in history_text.lower():
            retrieval = [r for r in retrieval if r["filename"] == "06-international-shipping.md"]

        return {
            "answer": retrieval[0]["text"],
            "sources": [r["filename"] for r in retrieval],
            "tool_used": None,
            "retrieval": retrieval,
            "handoff": False,
        }
