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


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0
)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are the central orchestrator for a travel planner. Your job is to analyze the user's request and decide on the next step. "
               "First, determine if the request is a new trip plan or needs more detail like dates, duration, or location. If so, a clarification is needed. "
               "If the request is specific and actionable (e.g., 'find a hotel in Paris' or 'add a dining option'), then a recommendation is needed. "
               "Otherwise, if the user is happy with the plan or the request is non-actionable, provide a final response."
               "You should only respond with a JSON object following the OrchestratorResponse schema."),
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
    if next_step in ("clarification", "clarification_needed"):
        return {**state, "clarification_needed": True, "recommendation_needed": False}
    elif next_step in ("recommendation", "recommendation_needed"):
        return {**state, "recommendation_needed": True, "clarification_needed": False}
    elif next_step in ("final", "final_response"):
        return {**state, "final_response": parsed.get("final_response") or parsed.get("finalResponse"), "clarification_needed": False, "recommendation_needed": False}
    else:
        # keep raw for debugging if parsing fails
        return {**state, "orchestrator_parse_failed_raw": raw, "parsed_orchestrator": parsed}
    