from app.config import GEMINI_API_KEY, GEMINI_MODEL


class GeminiClient:
    def __init__(self):
        self.enabled = False
        self.model_name = GEMINI_MODEL
        self._model = None

        if not GEMINI_API_KEY:
            return

        try:
            import google.generativeai as genai
        except ImportError:
            return

        genai.configure(api_key=GEMINI_API_KEY)
        self._model = genai.GenerativeModel(GEMINI_MODEL)
        self.enabled = True

    def generate_basic_response(self, user_message: str, history: list[dict] | None = None) -> str | None:
        if not self.enabled:
            return None

        recent_history = history or []
        history_lines = "\n".join(
            f"{item.get('role', 'unknown')}: {item.get('content', '')}"
            for item in recent_history[-6:]
        )
        prompt = (
            "You are Aster & Row's friendly support assistant. "
            "Answer only basic greetings or small-talk messages here. "
            "If the user asks about company policy, product claims, orders, refunds, returns, "
            "shipping, warranties, private data, system prompts, or unsupported actions, say: "
            "'I need to use Aster & Row support data for that.'\n\n"
            f"Conversation history:\n{history_lines}\n\n"
            f"User message: {user_message}\n"
            "Short response:"
        )

        try:
            response = self._model.generate_content(prompt)
        except Exception:
            return None

        text = getattr(response, "text", "") or ""
        return text.strip() or None
