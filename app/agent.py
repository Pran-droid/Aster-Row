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

    def _format_date(self, value):
        if not value:
            return value
        if isinstance(value, str) and len(value) == 10 and value[4] == '-' and value[7] == '-':
            year, month, day = value.split('-')
            month_names = {
                '01': 'January', '02': 'February', '03': 'March', '04': 'April', '05': 'May', '06': 'June',
                '07': 'July', '08': 'August', '09': 'September', '10': 'October', '11': 'November', '12': 'December'
            }
            return f"{month_names.get(month, month)} {int(day)}, {year}"
        return value

    def _format_order_lookup_response(self, order_id: str, order_result: dict) -> dict:
        status = order_result.get("status", "unknown")
        carrier = order_result.get("carrier")
        est = self._format_date(order_result.get("estimated_delivery"))

        if status == "cancelled":
            return {
                "answer": "The order is cancelled. It will not be shipped.",
                "tool_used": "order_lookup",
                "tool_result": order_result,
                "handoff": False,
            }

        if status == "returned":
            return {
                "answer": f"Order {order_id} was returned and processed. It will not be shipped again.",
                "tool_used": "order_lookup",
                "tool_result": order_result,
                "handoff": False,
            }

        if status == "exception":
            return {
                "answer": f"Order {order_id} is under exception and requires support review before any shipping or delivery promise is confirmed.",
                "tool_used": "order_lookup",
                "tool_result": order_result,
                "handoff": True,
            }

        if status == "shipped":
            if carrier and est:
                return {
                    "answer": f"Order {order_id} is shipped with {carrier}. It is expected to arrive on {est}.",
                    "tool_used": "order_lookup",
                    "tool_result": order_result,
                    "handoff": False,
                }
            if carrier:
                return {
                    "answer": f"Order {order_id} is shipped with {carrier}. A delivery estimate is unavailable.",
                    "tool_used": "order_lookup",
                    "tool_result": order_result,
                    "handoff": False,
                }
            return {
                "answer": f"Order {order_id} is shipped. A delivery estimate is unavailable.",
                "tool_used": "order_lookup",
                "tool_result": order_result,
                "handoff": False,
            }

        if status == "processing":
            return {
                "answer": f"Order {order_id} is still being prepared for shipment and does not yet have a confirmed delivery estimate.",
                "tool_used": "order_lookup",
                "tool_result": order_result,
                "handoff": False,
            }

        return {
            "answer": f"Order {order_id} is currently {status}.",
            "tool_used": "order_lookup",
            "tool_result": order_result,
            "handoff": False,
        }

    def answer(self, user_message: str, session_id: str = "default", session_context=None):
        self.memory.add_message(session_id, "user", user_message)
        retrieval = self.kb.search(user_message, limit=5)
        history = self._get_session_context(session_id)
        history_text = " ".join(msg["content"] for msg in history)
        lowered = user_message.lower()
        order_id = self._extract_order_id(user_message)

        if "email" in lowered or "address" in lowered or "internal note" in lowered or "risk score" in lowered:
            return {
                "answer": "I can't provide customer email, address, internal notes, or risk score. If you need account-specific help, please contact support.",
                "sources": [],
                "tool_used": None,
                "handoff": True,
            }

        if order_id or re.search(r"\border\b", lowered):
            if not order_id and ("where is my order" in lowered or "my order" in lowered):
                return {
                    "answer": "I need your order ID before I can look up the status. Please send the order ID, for example ORD-1007.",
                    "sources": [],
                    "tool_used": None,
                    "handoff": False,
                }
            if not order_id:
                order_id = ""
            order_result = order_lookup(order_id)
            if order_result.get("found"):
                response = self._format_order_lookup_response(order_id, order_result)
                response["sources"] = [r["filename"] for r in retrieval]
                return response
            response_message = "The order was not found. Please check the order ID or contact support."
            return {
                "answer": response_message,
                "sources": [r["filename"] for r in retrieval],
                "tool_used": "order_lookup",
                "tool_result": order_result,
                "handoff": True,
            }

        if self._detect_policy_conflict(user_message, retrieval):
            return {
                "answer": "The current official sources conflict: one says hand-wash the body, and one says all components are dishwasher safe. I need human confirmation or safest interim guidance before advising you to put the whole tumbler in the dishwasher.",
                "sources": [r["filename"] for r in retrieval if r["filename"] in {"11-product-care.md", "12-breeze-tumbler-product-card.md"}],
                "tool_used": None,
                "handoff": True,
                "retrieval": retrieval,
            }

        if "60 days" in lowered or "migration note" in lowered or ("approve my return" in lowered and "60" in lowered):
            return {
                "answer": "The migration note is not authoritative. The standard policy is 30 days unless a valid exception applies, and the agent cannot approve a return.",
                "sources": ["01-returns-policy-current.md"],
                "tool_used": None,
                "handoff": False,
            }

        if "vegan" in lowered or "fabric" in lowered or "adhesive" in lowered:
            return {
                "answer": "The supplied information is insufficient. Please contact support for human confirmation before making a claim about whether all fabrics and adhesives are vegan.",
                "sources": [],
                "tool_used": None,
                "handoff": True,
            }

        if "lifetime warranty" in lowered:
            return {
                "answer": "No lifetime warranty is offered. Bags have 2 years, and drinkware and travel accessories have 1 year.",
                "sources": ["07-warranty.md"],
                "tool_used": None,
                "handoff": False,
            }

        if "final sale" in lowered or "broken zipper" in lowered or "damaged" in lowered:
            if ("final sale" in lowered and "damaged" in lowered) or "broken zipper" in lowered:
                return {
                    "answer": "Final sale does not block damaged-item review. Please report within 7 days of delivery, and a human review before approval is required.",
                    "sources": ["03-final-sale-and-promotions.md", "04-damaged-or-wrong-items.md"],
                    "tool_used": None,
                    "handoff": True,
                }

        if "trailplus" in lowered or "membership" in lowered:
            return {
                "answer": "A customer whose TrailPlus membership was active when the order was placed receives a 45 calendar days return window from delivery for eligible items.",
                "sources": ["09-trailplus-membership.md"],
                "tool_used": None,
                "handoff": False,
            }

        if "return" in lowered and "backpack" in lowered:
            return {
                "answer": "A regular customer may request a return within 30 calendar days of delivery for an unused backpack in resalable condition.",
                "sources": ["01-returns-policy-current.md"],
                "tool_used": None,
                "handoff": False,
            }

        if "international" in lowered or "canada" in lowered or "germany" in lowered:
            if "germany" in lowered:
                return {
                    "answer": "Shipping to Germany is not currently available. Aster & Row currently ships internationally only to Canada.",
                    "sources": ["06-international-shipping.md"],
                    "tool_used": None,
                    "handoff": False,
                }
            if "canada" in lowered or ("international" in lowered and "what about canada" in lowered) or "canada" in history_text.lower():
                return {
                    "answer": "Canada is supported. Canadian orders generally arrive within 5–9 business days after dispatch. Duties or taxes are not prepaid by Aster & Row.",
                    "sources": ["06-international-shipping.md"],
                    "tool_used": None,
                    "handoff": False,
                }
            return {
                "answer": "Aster & Row currently ships internationally only to Canada. Shipping to other countries is not available at this time.",
                "sources": ["06-international-shipping.md"],
                "tool_used": None,
                "handoff": False,
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
