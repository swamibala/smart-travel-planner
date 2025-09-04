import uuid
import json
from langgraph_app.app import app
from database.db_setup import create_table, save_itinerary, get_itinerary


def main():
    print("Welcome to the Smart Travel Planner!")
    print("Type 'exit' to quit.")

    create_table()
    thread_id = str(uuid.uuid4())
    print(f"Your session ID is: {thread_id}")

    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            break

        inputs = {
            "thread_id": thread_id,
            "current_request": user_input,
            "itinerary_data": {}
        }

        state = app.invoke(inputs)
        if "agent_response" in state:
            print(f"Agent: {state['agent_response']}")
        if "final_response" in state:
            itinerary = get_itinerary(thread_id)
            if itinerary:
                print("\n--- Current Itinerary Status ---")
                print(json.dumps(json.loads(itinerary), indent=2))
                print("------------------------------\n")



if __name__ == "__main__":
    main()
