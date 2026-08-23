from app.agent import SupportAgent


def main():
    agent = SupportAgent("knowledge-base")
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() in {"exit", "quit"}:
            break
        result = agent.answer(user_input)
        print("Agent:", result["answer"])
        if result.get("sources"):
            print("Sources:", ", ".join(result["sources"]))


if __name__ == "__main__":
    main()
