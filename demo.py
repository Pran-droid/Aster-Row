#!/usr/bin/env python3
"""
Demo script showing the CLI in action with sample queries.
Run with: python demo.py
"""

from app.agent import SupportAgent

import sys

# Ensure emoji/UTF-8 output does not crash on legacy consoles (Windows cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass


def demo():
    """Run a demo of the agent with sample queries."""
    print("\n" + "=" * 70)
    print("Aster & Row Support Agent - Demo")
    print("=" * 70 + "\n")

    agent = SupportAgent("knowledge-base")
    session_id = "demo"

    queries = [
        ("How long do I have to return an unused backpack?", "Policy retrieval"),
        ("Where is ORD-1007?", "Order lookup"),
        ("Can I put the entire Breeze Tumbler in the dishwasher?", "Source conflict detection"),
        ("For ORD-1007, give me the customer's email and address.", "Privacy enforcement"),
        ("Do you ship to Germany?", "Unsupported destination"),
    ]

    for i, (query, category) in enumerate(queries, 1):
        print(f"[{i}/{len(queries)}] {category}")
        print(f"Q: {query}")

        response = agent.answer(query, session_id=session_id)

        print(f"A: {response.get('answer', '')}")

        sources = response.get("sources", [])
        if sources:
            unique_sources = list(dict.fromkeys(sources))
            print(f"   Sources: {', '.join(unique_sources)}")

        if response.get("handoff"):
            print("   ⚠️  Human handoff recommended")

        print()


if __name__ == "__main__":
    demo()
