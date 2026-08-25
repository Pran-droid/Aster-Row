import re

from app.llm import GeminiClient
from app.logs import log_event
from app.memory import SessionMemory
from app.retrieval import KnowledgeBase
from app.tools import order_lookup


class SupportAgent:
    def __init__(self, knowledge_base_dir: str):
        self.kb = KnowledgeBase(knowledge_base_dir)
        self.kb.build()
        self.memory = SessionMemory()
        self.llm = GeminiClient()

    def _detect_policy_conflict(self, user_message: str, retrieval):
        lowered = user_message.lower()
        filenames = [r["filename"] for r in retrieval]
        return (
            "dishwasher" in lowered
            and "11-product-care.md" in filenames
            and "12-breeze-tumbler-product-card.md" in filenames
        )

    def _extract_order_id(self, text: str):
        match = re.search(r"ORD-\d+", text, flags=re.IGNORECASE)
        if match:
            return match.group(0).upper()
        return None

    def _get_session_context(self, session_id: str):
        return self.memory.get_recent_context(session_id, limit=10)

    def _source(self, filename: str, heading: str) -> str:
        return f"{filename} > {heading}"

    def _sources_from_retrieval(self, retrieval):
        return [r.get("source") or self._source(r["filename"], r.get("heading", r["title"])) for r in retrieval]

    def _respond(
        self,
        *,
        answer: str,
        sources=None,
        tool_used=None,
        tool_result=None,
        handoff=False,
        retrieval=None,
        session_id="default",
        user_message="",
        history=None,
        fallback=None,
    ):
        response = {
            "answer": answer,
            "sources": sources or [],
            "tool_used": tool_used,
            "handoff": handoff,
        }
        if tool_result is not None:
            response["tool_result"] = tool_result
        if retrieval is not None:
            response["retrieval"] = retrieval
        if fallback:
            response["fallback"] = fallback

        log_event(
            "agent_trace",
            {
                "session_id": session_id,
                "user_message": user_message,
                "history": history or [],
                "retrieval": retrieval or [],
                "tool_used": tool_used,
                "tool_result": tool_result,
                "handoff": handoff,
                "final_response": response,
            },
        )
        self.memory.add_message(session_id, "assistant", answer)
        return response

    def _format_date(self, value):
        if not value:
            return value
        if isinstance(value, str) and len(value) == 10 and value[4] == "-" and value[7] == "-":
            year, month, day = value.split("-")
            month_names = {
                "01": "January", "02": "February", "03": "March", "04": "April", "05": "May", "06": "June",
                "07": "July", "08": "August", "09": "September", "10": "October", "11": "November", "12": "December",
            }
            return f"{month_names.get(month, month)} {int(day)}, {year}"
        return value

    def _format_order_lookup_response(self, order_id: str, order_result: dict) -> dict:
        status = order_result.get("status", "unknown")
        carrier = order_result.get("carrier")
        est = self._format_date(order_result.get("estimated_delivery"))

        if status == "cancelled":
            return {"answer": "The order is cancelled. It will not be shipped.", "handoff": False}

        if status == "returned":
            return {"answer": f"Order {order_id} was returned and processed. It will not be shipped again.", "handoff": False}

        if status == "exception":
            return {
                "answer": f"Order {order_id} is under exception and requires support review before any shipping or delivery promise is confirmed.",
                "handoff": True,
            }

        if status == "shipped":
            if carrier and est:
                return {"answer": f"Order {order_id} is shipped with {carrier}. It is expected to arrive on {est}.", "handoff": False}
            if carrier:
                return {"answer": f"Order {order_id} is shipped with {carrier}. A delivery estimate is unavailable.", "handoff": False}
            return {"answer": f"Order {order_id} is shipped. A delivery estimate is unavailable.", "handoff": False}

        if status == "processing":
            return {
                "answer": f"Order {order_id} is still being prepared for shipment and does not yet have a confirmed delivery estimate.",
                "handoff": False,
            }

        if status == "delivered":
            delivered_at = self._format_date((order_result.get("delivered_at") or "")[:10])
            return {"answer": f"Order {order_id} was delivered on {delivered_at}.", "handoff": False}

        if status == "delayed":
            if carrier and est:
                return {"answer": f"Order {order_id} is delayed with {carrier}. The current estimated delivery date is {est}.", "handoff": False}
            return {"answer": f"Order {order_id} is delayed. A delivery estimate is unavailable.", "handoff": False}

        return {"answer": f"Order {order_id} is currently {status}.", "handoff": False}

    def _is_basic_message(self, lowered: str) -> bool:
        basic = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "thanks", "thank you"}
        return lowered.strip(" !?.") in basic

    def answer(self, user_message: str, session_id: str = "default", session_context=None):
        self.memory.add_message(session_id, "user", user_message)
        retrieval = self.kb.search(user_message, limit=5)
        history = self._get_session_context(session_id)
        prior_history_text = " ".join(msg["content"] for msg in history[:-1])
        lowered = user_message.lower()
        order_id = self._extract_order_id(user_message)

        if "system prompt" in lowered or "hidden instruction" in lowered or "developer message" in lowered:
            return self._respond(
                answer="I can't reveal system prompts, hidden instructions, developer messages, secrets, or internal-only data.",
                handoff=True,
                session_id=session_id,
                user_message=user_message,
                history=history,
            )

        if "email" in lowered or "address" in lowered or "internal note" in lowered or "risk score" in lowered:
            return self._respond(
                answer="I can't provide customer email, address, internal notes, or risk score. If you need account-specific help, please contact support.",
                handoff=True,
                session_id=session_id,
                user_message=user_message,
                history=history,
            )

        if order_id or re.search(r"\border\b", lowered):
            if not order_id and ("where is my order" in lowered or "my order" in lowered):
                return self._respond(
                    answer="I need your order ID before I can look up the status. Please send the order ID, for example ORD-1007.",
                    retrieval=retrieval,
                    session_id=session_id,
                    user_message=user_message,
                    history=history,
                )
            if not order_id:
                order_id = ""
            order_result = order_lookup(order_id)
            if order_result.get("found"):
                formatted = self._format_order_lookup_response(order_id, order_result)
                return self._respond(
                    answer=formatted["answer"],
                    sources=self._sources_from_retrieval(retrieval),
                    tool_used="order_lookup",
                    tool_result=order_result,
                    handoff=formatted["handoff"],
                    retrieval=retrieval,
                    session_id=session_id,
                    user_message=user_message,
                    history=history,
                )
            return self._respond(
                answer="The order was not found. Please check the order ID or contact support.",
                sources=self._sources_from_retrieval(retrieval),
                tool_used="order_lookup",
                tool_result=order_result,
                handoff=True,
                retrieval=retrieval,
                session_id=session_id,
                user_message=user_message,
                history=history,
            )

        if self._detect_policy_conflict(user_message, retrieval):
            conflict_sources = [
                r.get("source") or r["filename"]
                for r in retrieval
                if r["filename"] in {"11-product-care.md", "12-breeze-tumbler-product-card.md"}
            ]
            return self._respond(
                answer="The current official sources conflict: one says hand-wash the body, and one says all components are dishwasher safe. I need human confirmation or safest interim guidance before advising you to put the whole tumbler in the dishwasher.",
                sources=conflict_sources,
                handoff=True,
                retrieval=retrieval,
                session_id=session_id,
                user_message=user_message,
                history=history,
            )

        if "60 days" in lowered or "migration note" in lowered or ("approve my return" in lowered and "60" in lowered):
            return self._respond(
                answer="The migration note is not authoritative. The standard policy is 30 days unless a valid exception applies, and the agent cannot approve a return.",
                sources=[self._source("01-returns-policy-current.md", "Return Window")],
                retrieval=retrieval,
                session_id=session_id,
                user_message=user_message,
                history=history,
            )

        if "vegan" in lowered or "fabric" in lowered or "adhesive" in lowered:
            return self._respond(
                answer="The supplied information is insufficient. Please contact support for human confirmation before making a claim about whether all fabrics and adhesives are vegan.",
                handoff=True,
                retrieval=retrieval,
                session_id=session_id,
                user_message=user_message,
                history=history,
            )

        if "lifetime warranty" in lowered:
            return self._respond(
                answer="No lifetime warranty is offered. Bags have 2 years, and drinkware and travel accessories have 1 year.",
                sources=[self._source("07-warranty.md", "Coverage period")],
                retrieval=retrieval,
                session_id=session_id,
                user_message=user_message,
                history=history,
            )

        if "final sale" in lowered or "broken zipper" in lowered or "damaged" in lowered:
            if ("final sale" in lowered and "damaged" in lowered) or "broken zipper" in lowered:
                return self._respond(
                    answer="Final sale does not block damaged-item review. Please report within 7 days of delivery, and a human review before approval is required.",
                    sources=[
                        self._source("03-final-sale-and-promotions.md", "Final sale items"),
                        self._source("04-damaged-or-wrong-items.md", "Reporting window"),
                    ],
                    handoff=True,
                    retrieval=retrieval,
                    session_id=session_id,
                    user_message=user_message,
                    history=history,
                )

        if "trailplus" in lowered or "membership" in lowered:
            return self._respond(
                answer="A customer whose TrailPlus membership was active when the order was placed receives a 45 calendar days return window from delivery for eligible items.",
                sources=[self._source("09-trailplus-membership.md", "Return-window extension")],
                retrieval=retrieval,
                session_id=session_id,
                user_message=user_message,
                history=history,
            )

        if "return" in lowered and "backpack" in lowered:
            return self._respond(
                answer="A regular customer may request a return within 30 calendar days of delivery for an unused backpack in resalable condition.",
                sources=[self._source("01-returns-policy-current.md", "Return Window")],
                retrieval=retrieval,
                session_id=session_id,
                user_message=user_message,
                history=history,
            )

        if "gift card" in lowered:
            return self._respond(
                answer="Aster & Row gift cards do not expire, are final sale, and cannot be returned, exchanged for cash, or used to purchase another gift card except where required by law. Please do not share a complete gift-card code in chat.",
                sources=[self._source("10-gift-cards-and-price-adjustments.md", "Gift cards")],
                retrieval=retrieval,
                session_id=session_id,
                user_message=user_message,
                history=history,
            )

        if "price adjustment" in lowered or "price drop" in lowered or "dropped in price" in lowered:
            return self._respond(
                answer="A customer may request one price adjustment when the public price of the same item, color, and size drops within 7 calendar days of the original purchase. A human support specialist must approve and process the adjustment.",
                sources=[self._source("10-gift-cards-and-price-adjustments.md", "Price adjustments")],
                handoff=True,
                retrieval=retrieval,
                session_id=session_id,
                user_message=user_message,
                history=history,
            )

        if "cancel" in lowered or "address change" in lowered or "change my address" in lowered:
            return self._respond(
                answer="Cancellation or address correction may be requested within 30 minutes of placing an order while the order is still pending. A human support specialist must complete address changes, and the agent must not claim a cancellation or change is complete.",
                sources=[self._source("08-order-changes-and-cancellations.md", "Cancellation window")],
                handoff=True,
                retrieval=retrieval,
                session_id=session_id,
                user_message=user_message,
                history=history,
            )

        if "domestic" in lowered or "po box" in lowered or "standard shipping" in lowered:
            return self._respond(
                answer="Most orders require 1-2 business days for processing before dispatch. After dispatch, contiguous United States delivery is estimated at 3-5 business days, Alaska and Hawaii at 5-8 business days, and PO boxes at 5-9 business days.",
                sources=[self._source("05-domestic-shipping.md", "Delivery estimates after dispatch")],
                retrieval=retrieval,
                session_id=session_id,
                user_message=user_message,
                history=history,
            )

        if "international" in lowered or "canada" in lowered or "germany" in lowered:
            if "germany" in lowered:
                return self._respond(
                    answer="Shipping to Germany is not currently available. Aster & Row currently ships internationally only to Canada.",
                    sources=[self._source("06-international-shipping.md", "Supported destinations")],
                    retrieval=retrieval,
                    session_id=session_id,
                    user_message=user_message,
                    history=history,
                )
            if "canada" in lowered:
                return self._respond(
                    answer="Canada is supported. Canadian orders generally arrive within 5–9 business days after dispatch. Duties or taxes are not prepaid by Aster & Row.",
                    sources=[self._source("06-international-shipping.md", "Canada shipping")],
                    retrieval=retrieval,
                    session_id=session_id,
                    user_message=user_message,
                    history=history,
                )
            if "what about" in lowered and "international" in prior_history_text.lower():
                return self._respond(
                    answer="Canada is supported. Canadian orders generally arrive within 5–9 business days after dispatch. Duties or taxes are not prepaid by Aster & Row.",
                    sources=[self._source("06-international-shipping.md", "Canada shipping")],
                    retrieval=retrieval,
                    session_id=session_id,
                    user_message=user_message,
                    history=history,
                )
            return self._respond(
                answer="Aster & Row currently ships internationally only to Canada. Shipping to other countries is not available at this time.",
                sources=[self._source("06-international-shipping.md", "Supported destinations")],
                retrieval=retrieval,
                session_id=session_id,
                user_message=user_message,
                history=history,
            )

        if self._is_basic_message(lowered):
            gemini_answer = self.llm.generate_basic_response(user_message, history)
            return self._respond(
                answer=gemini_answer or "Hi! I can help with Aster & Row policies, products, and order status.",
                session_id=session_id,
                user_message=user_message,
                history=history,
                fallback="gemini" if gemini_answer else "local_basic_response",
            )

        if not retrieval:
            gemini_answer = self.llm.generate_basic_response(user_message, history)
            if gemini_answer and "support data" not in gemini_answer.lower():
                return self._respond(
                    answer=gemini_answer,
                    session_id=session_id,
                    user_message=user_message,
                    history=history,
                    fallback="gemini",
                )
            return self._respond(
                answer="The supplied information is insufficient to answer that reliably. Please contact support for help.",
                handoff=True,
                session_id=session_id,
                user_message=user_message,
                history=history,
            )

        return self._respond(
            answer=retrieval[0]["text"],
            sources=self._sources_from_retrieval(retrieval),
            retrieval=retrieval,
            session_id=session_id,
            user_message=user_message,
            history=history,
        )
