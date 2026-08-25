#!/usr/bin/env python3
"""
CLI interface for the Aster & Row support agent.

Run with: python cli.py
"""

import sys

from app.agent import SupportAgent

# Emoji/UTF-8 output must not crash on consoles that default to a legacy code
# page (e.g. Windows cp1252). Reconfigure stdout/stderr to UTF-8 when possible.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass


def format_sources(sources: list) -> str:
    """Format sources for display."""
    if not sources:
        return ""
    unique = list(dict.fromkeys(sources))  # Remove duplicates, preserve order
    return "📄 Sources: " + ", ".join(unique)


def format_handoff(handoff: bool) -> str:
    """Format handoff recommendation."""
    if handoff:
        return "🤝 Human handoff recommended"
    return ""


def main():
    """Run the interactive CLI agent."""
    print("\n" + "=" * 70)
    print("Aster & Row Support Agent")
    print("=" * 70)
    print("Ask a question about returns, shipping, warranties, or orders.")
    print("Type 'exit' to quit.\n")

    agent = SupportAgent("knowledge-base")
    session_id = "cli-session"

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit", "bye"}:
                print("\nAgent: Thank you for contacting Aster & Row support. Goodbye! 👋\n")
                break

            # Get agent response
            response = agent.answer(user_input, session_id=session_id)

            # Display answer
            print("\nAgent:", response.get("answer", ""))

            # Display sources if available
            sources = format_sources(response.get("sources", []))
            if sources:
                print(sources)

            # Display handoff recommendation if needed
            handoff = format_handoff(response.get("handoff", False))
            if handoff:
                print(handoff)

            print()

        except KeyboardInterrupt:
            print("\n\nAgent: Session interrupted. Goodbye! 👋\n")
            break
        except Exception as e:
            print(f"\nError: {e}\n")
            continue


if __name__ == "__main__":
    main()
