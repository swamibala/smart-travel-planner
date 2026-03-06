import os
from dotenv import load_dotenv

load_dotenv()

import uuid
from langchain_core.messages import HumanMessage
from agents.graph import graph_app


def main():
    print("Welcome to the Smart Travel Planner!")
    print("Type 'exit' or 'quit' to exit.")

    thread_id = str(uuid.uuid4())
    print(f"Session ID: {thread_id}\n")

    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            if not user_input.strip():
                continue

            # Initial State
            state = {
                "messages": [HumanMessage(content=user_input)],
                "next_node": "",
                "entities": None,
                "search_results": "",
                "summary": "",
                "critique": "",
                "is_valid": False,
            }

            print("\nThinking...")

            # Streaming execution to show progress
            for event in graph_app.stream(
                state, config={"configurable": {"thread_id": thread_id}}
            ):
                for node_name, node_state in event.items():
                    print(f"  [Executed Node: {node_name}]")
                    # Update final state ref
                    state = node_state

            summary = state.get("summary", "No summary generated.")
            critique = state.get("critique", "")

            print(f"\nAgent: {summary}")
            print(f"[Internal Critique]: {critique}\n")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
