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

        for step in app.stream(inputs):
            if "agent_response" in step:
                print(f"Planner: {step['agent_response']}")
            
            # we break the inner loop and wait for the next user input.
            if "agent_response" in step or "final_response" in step:
                break

        itinerary = get_itinerary(thread_id)
        if itinerary:
            print("\n--- Current Itinerary Status ---")
            print(json.dumps(json.loads(itinerary), indent=2))
            print("------------------------------\n")

if __name__ == "__main__":
    main()
