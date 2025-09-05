from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.messages import AIMessage
from tools.serpapi_tools import tools
import json
import os
import re

class OrchestratorResponse(BaseModel):
    """
    Decides the next action for the travel planning workflow.
    """
    next_step: str = Field(
        description="The next step to take. Must be one of 'clarification_needed', 'recommendation_needed', or 'final_response'."
    )
    final_response: str = Field(
        description="The final response to the user. Only used if next_step is 'final_response'."
    )


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0
)

system_prompt = """
    You are the central orchestrator for a travel planner. Your sole purpose is to analyze the user's request and decide the next step in the workflow.

    **Your decision must be one of the following:**
    1.  **"clarification"**: Use this ONLY when the user's request is missing essential information, such as the **origin city**, **destination city**, or **dates of travel**.
    2.  **"recommendation"**: Use this when the user's request is complete and contains all necessary details (origin, destination, dates) to begin the travel planning process.
    3.  **"final_response"**: Use this when a complete, finalized response can be provided to the user without further steps. This is typically after all necessary information has been gathered and a recommendation has been formulated. The response should be a well-structured travel itinerary.

    **You must respond with a JSON object following this schema:**
    ```json
    {{
    "next_step": "string, one of 'clarification', 'recommendation', or 'final_response'",
    "final_response": "string, the final itinerary or response. ONLY include this if next_step is 'final_response'."
    }}
    ```
    """
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{request}")
])

llm_chain = prompt | llm

def orchestrator_agent_node(state):
    """
    Determines the next step in the workflow based on the user's request.
    """

    request = state["messages"][-1].content
    response = llm_chain.invoke({"request": request})
    print(f"Orchestrator response: {response}")

    # get raw text safely
    raw = getattr(response, "content", "") or ""
    # strip markdown code fences (```json ... ```)
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()

    # try to parse JSON, fallback to extracting {...} block
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        try:
            parsed = json.loads(m.group(0)) if m else {}
        except Exception:
            parsed = {}

    next_step = parsed.get("next_step") or parsed.get("nextStep")

    # map LLM decision into state flags used by the graph routing
    if str.lower(next_step) == "clarification":
        return {**state, "clarification_needed": True, "recommendation_needed": False, "final_response_needed": False}
    elif str.lower(next_step) == "recommendation":
        return {**state, "recommendation_needed": True, "clarification_needed": False, "final_response_needed": False}
    elif str.lower(next_step) == "final_response":
        return {**state, "final_response": parsed.get("final_response") or parsed.get("finalResponse"), "clarification_needed": False, "recommendation_needed": False, "final_response_needed": True}
    else:
        # keep raw for debugging if parsing fails
        return {**state, "orchestrator_parse_failed_raw": raw, "parsed_orchestrator": parsed}
    