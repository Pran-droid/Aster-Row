class SessionMemory:
    def __init__(self):
        self.sessions = {}

    def get_session(self, session_id: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = {"history": []}
        return self.sessions[session_id]

    def add_message(self, session_id: str, role: str, content: str):
        session = self.get_session(session_id)
        session["history"].append({"role": role, "content": content})

    def get_recent_context(self, session_id: str, limit: int = 5):
        session = self.get_session(session_id)
        return session["history"][-limit:]
