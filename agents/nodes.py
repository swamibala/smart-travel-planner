from langchain_google_genai import ChatGoogleGenerativeAI
from langsmith import traceable
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

from agents.state import AgentState, Entities
from tools.tavily_tools import web_search
from tools.serpapi_tools import search_hotels

# Using gemini-2.5-flash as the latest standard flash model
LLM_MODEL = "gemini-2.5-flash"


import os

def get_llm():
    return ChatGoogleGenerativeAI(
        model=LLM_MODEL, 
        temperature=0, 
        api_key=os.environ.get("GOOGLE_API_KEY")
    )


class RouteDecision(BaseModel):
    route: Literal["entity_extraction", "web_search"] = Field(
        description="Route to 'entity_extraction' if the user is asking about hotels, accommodation, or places to stay. Route to 'web_search' for general questions."
    )


@traceable
def orchestrator_node(state: AgentState) -> AgentState:
    """
    Decides whether the user is asking for hotels or general info.
    Routes to `entity_extraction` or `web_search`.
    """
    llm = get_llm().with_structured_output(RouteDecision)
    messages = state["messages"]
    user_query = messages[-1].content

    system_prompt = "You are the Orchestrator Planner Agent. Your goal is to route the user's query accurately."
    
    response: RouteDecision = llm.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_query)]
    )

    state["next_node"] = response.route

    return state


@traceable
def entity_extraction_node(state: AgentState) -> AgentState:
    """
    Extracts entities for the hotel search.
    """
    llm = get_llm()
    # Structured output capabilities
    llm_with_tools = llm.with_structured_output(Entities)

    user_query = state["messages"][-1].content
    system_prompt = "You are an Entity Extraction Agent. Extract relevant details for a hotel search from the user query."

    extracted: Entities = llm_with_tools.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_query)]
    )

    state["entities"] = extracted
    state["next_node"] = "hotel_search"
    return state


@traceable(run_type="tool")
def hotel_search_node(state: AgentState) -> AgentState:
    """
    Performs the SERP API Hotel Search using the extracted entities.
    """
    entities = state.get("entities", {})

    # Construct a sensible query from entities
    city = entities.get("city", "")
    landmark = entities.get("landmark", "")
    base_query = f"{landmark} {city}".strip()
    if not base_query:
        base_query = state["messages"][-1].content  # fallback

    check_in = entities.get("check_in_date")
    check_out = entities.get("check_out_date")

    try:
        results = search_hotels(
            query=base_query, check_in_date=check_in, check_out_date=check_out
        )
        state["search_results"] = results
    except Exception as e:
        state["search_results"] = f"Error during hotel search: {str(e)}"

    state["next_node"] = "summarize"
    return state


@traceable(run_type="tool")
def web_search_node(state: AgentState) -> AgentState:
    """
    Performs Tavily web search for general queries.
    """
    user_query = state["messages"][-1].content
    results = web_search(query=user_query)

    state["search_results"] = results
    state["next_node"] = "summarize"
    return state


@traceable
def summarize_node(state: AgentState) -> AgentState:
    """
    Summarizes the raw search results for the user.
    """
    llm = get_llm()
    user_query = state["messages"][-1].content
    raw_results = state.get("search_results", "No results.")

    system_prompt = (
        "You are a helpful Summarisation Agent. You will be given raw search results "
        "and the user's original query. Formulate a comprehensive, conversational, "
        "and clear response answering the user's query based strictly on the provided search results."
    )

    content = f"User Query: {user_query}\n\nSearch Results:\n{raw_results}"

    response = llm.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=content)]
    )

    state["summary"] = response.content
    state["next_node"] = "critique"

    return state


class CritiqueDecision(BaseModel):
    is_valid: bool = Field(description="True if the summary adequately addresses the user's query, False otherwise.")
    critique: str = Field(description="A short explanation of the quality check.")


@traceable
def critique_node(state: AgentState) -> AgentState:
    """
    Critiques the summary against the user query to ensure quality.
    """
    llm = get_llm().with_structured_output(CritiqueDecision)
    user_query = state["messages"][-1].content
    summary = state.get("summary", "")

    system_prompt = "You are a strict Critique Agent. Perform a quality check on whether the drafted summary answers the query."
    content = f"User Query: {user_query}\n\nDrafted Summary:\n{summary}"

    response: CritiqueDecision = llm.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=content)]
    )

    state["is_valid"] = response.is_valid
    state["critique"] = response.critique

    # Normally if it fails we might loop back, but for this linear path we just end
    state["next_node"] = "END"

    return state
