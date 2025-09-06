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
        description="The next step to take. Must be one of 'clarification_needed', 'recommendation_needed', or 'formatter'."
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
    3.  **"formatter"**: Use this when all information has been gathered and is ready to be presented to the user. The recommendation agent will have already collected all the necessary data.

    **You must respond with a JSON object following this schema:**
    ```json
    {{
      "next_step": "string, one of 'clarification', 'recommendation', or 'formatter'"
    }}
    ```
    **Example Scenarios:**
    * **User**: "I need a flight to Paris." -> **Next Step**: clarification
    * **User**: "Find me a flight from New York to London for next week." -> **Next Step**: recommendation

    """
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{request}")
])

llm_chain = prompt | llm.with_structured_output(OrchestratorResponse, include_raw=True)

def orchestrator_agent_node(state):
    """
    Determines the next step in the workflow based on the user's request.
    """

    request = state["messages"][-1].content
    response = llm_chain.invoke({"request": request})
    print(f"Orchestrator response: {response}")

    next_step = response.get("parsed").next_step

    # map LLM decision into state flags used by the graph routing
    if str.lower(next_step) == "clarification":
        return {**state, "clarification_needed": True, "recommendation_needed": False, "final_response_needed": False}
    elif str.lower(next_step) == "recommendation":
        return {**state, "recommendation_needed": True, "clarification_needed": False, "final_response_needed": False}
    elif str.lower(next_step) == "formatter":
        return {**state, "final_response_needed": True, "clarification_needed": False, "recommendation_needed": False}
    else:
        # Fallback for unexpected output
        return state
    