from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from database.db_setup import get_itinerary, save_itinerary
import json
import os


class OrchestratorResponse(BaseModel):
    """
    Decides the next action for the travel planning workflow.
    """
    next_step: str = Field(
        description="The next step to take. Must be one of 'clarification_needed', 'recommendation_needed', or 'final_response'."
    )
    details: str = Field(
        description="Details about the next step or the final response message."
    )

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are the central orchestrator for a travel planner. Your job is to analyze the user's request and decide on the next step. "
               "First, determine if the request is a new trip plan or needs more detail like dates, duration, or location. If so, a clarification is needed. "
               "If the request is specific and actionable (e.g., 'find a hotel in Paris' or 'add a dining option'), then a recommendation is needed. "
               "Otherwise, if the user is happy with the plan or the request is non-actionable, provide a final response."
               "You should only respond with a JSON object following the OrchestratorResponse schema."),
    ("human", "{request}")
])

orchestrator_chain = prompt | llm.with_structured_output(OrchestratorResponse)

def orchestrator_agent_node(state):
    """
    Determines the next step in the workflow based on the user's request.
    """
    request = state["current_request"]
    thread_id = state["thread_id"]

    # Load existing itinerary from the database
    existing_itinerary_json = get_itinerary(thread_id)
    if existing_itinerary_json:
        existing_itinerary = json.loads(existing_itinerary_json)
    else:
        existing_itinerary = {}

    # Check for empty tool output from the previous step
    if state.get("tool_output") == "[]":
        return {"agent_response": "I couldn't find any specific recommendations for a two-day trip. Please be more specific with what you'd like to do, like searching for hotels or specific attractions.", "final_response": "I couldn't find any specific recommendations."}

    orchestrator_output = orchestrator_chain.invoke({"request": request})

    # The orchestrator's decision is now explicitly handled.
    if orchestrator_output.next_step == "clarification_needed":
        return {"clarification_needed": True, "agent_response": orchestrator_output.details}
    elif orchestrator_output.next_step == "recommendation_needed":
        return {"recommendation_needed": True}
    else:
        # Process final response and save to database
        existing_itinerary["status"] = "final"
        existing_itinerary["response"] = orchestrator_output.details
        save_itinerary(thread_id, json.dumps(existing_itinerary))
        
        return {"final_response": orchestrator_output.details}