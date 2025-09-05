import uuid
import json
from langgraph_app.app import app
from langchain_core.messages import HumanMessage


def main():
    print("Welcome to the Smart Travel Planner!")
    print("Type 'exit' to quit.")

    thread_id = str(uuid.uuid4())
    print(f"Your session ID is: {thread_id}")

    state = {"thread_id": thread_id, "messages": []}

    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            break
        state["messages"].append(HumanMessage(content=user_input))
        state = app.invoke(state, config={"thread_id": thread_id})
        print(f"Agent: {state['messages'][-1].content}")

if __name__ == "__main__":
    main()
