"""
agents/nodes.py
───────────────
All agent nodes for the Smart Travel Planner.

Memory additions:
  memory_read_node   → reads Mem0 BEFORE orchestrator runs
  memory_write_node  → writes insights to Mem0 AFTER critique runs
  orchestrator_node  → injects user_memory into system prompt
  summarize_node     → injects user preferences into summary prompt
  critique_node      → autonomous failure signal → 100% confidence feedback

Signal flow:
  Conversational: user feedback in main.py → process_feedback()
  Autonomous:     critique is_valid=False  → process_feedback("autonomous_failure")
"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

from agents.state import AgentState, Entities
from tools.tavily_tools import web_search
from tools.serpapi_tools import search_hotels
from memory.mem0_manager import travel_memory

LLM_MODEL = "gemini-2.5-flash"


def get_llm():
    return ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        temperature=0,
        api_key=os.environ.get("GOOGLE_API_KEY"),
    )


# ── MEMORY READ NODE ──────────────────────────────────────────────────────────

def memory_read_node(state: AgentState) -> AgentState:
    """
    Reads relevant memories from Mem0 BEFORE any agent runs.
    Injects retrieved memories into state so all downstream nodes can use them.

    Also checks the archive for resurrection opportunities —
    if a pattern was forgotten but is reappearing, fast-track it back.

    Signal type: READ (no write, no feedback processing)
    """
    user_id   = state.get("user_id", "default_user")
    user_query = state["messages"][-1].content

    print(f"\n[Mem0] Reading memories for user: {user_id}")

    # Check archive first — maybe this topic was forgotten but is back
    resurrected = travel_memory.check_resurrection(user_id, user_query)
    if resurrected:
        print(f"[Mem0] Resurrected preference: '{resurrected}'")

    # Retrieve active memories relevant to this query
    memory_context = travel_memory.read(
        user_id=user_id,
        query=user_query,
    )

    if memory_context:
        print(f"[Mem0] Retrieved memory context:\n{memory_context}\n")
    else:
        print("[Mem0] No relevant memories found — fresh start\n")

    state["user_memory"]    = memory_context
    state["memory_updated"] = False
    return state


# ── MEMORY WRITE NODE ─────────────────────────────────────────────────────────

def memory_write_node(state: AgentState) -> AgentState:
    """
    Extracts lasting insights from this session and writes them to Mem0.
    Called AFTER critique_node — end of every graph execution.

    What gets written:
      - User preferences extracted from the conversation
      - Critique quality signal (autonomous feedback loop)

    What does NOT get written:
      - Raw search results (task-specific noise)
      - Hotel prices (temporary data)
      - Specific dates (session-scoped)

    Signal type: WRITE + autonomous feedback if critique failed
    """
    user_id  = state.get("user_id", "default_user")
    messages = state["messages"]
    summary  = state.get("summary", "")
    is_valid = state.get("is_valid", True)

    # ── Extract user preference signals from the conversation ─────────────────
    # Mem0's LLM extractor will separate lasting facts from task noise
    conversation_content = "\n".join([
        f"{m.type}: {m.content}" for m in messages
    ])

    if conversation_content:
        print(f"[Mem0] Writing user preferences from conversation...")
        memory_ids = travel_memory.write(
            user_id=user_id,
            content=conversation_content,
            agent_id="orchestrator",
            topic="travel_preferences",
        )
        print(f"[Mem0] Stored {len(memory_ids)} memory entries")

    # ── Autonomous feedback signal from critique node ─────────────────────────
    # This is the KEY autonomous signal — no human involved
    # critique_node set is_valid=False → the system knows the summary failed
    # Confidence: 100% (programmatic signal, not ambiguous language)
    if not is_valid:
        critique_text = state.get("critique", "Summary quality check failed")
        print(f"\n[Mem0] 🤖 Autonomous signal detected: critique failed")
        print(f"[Mem0] Signal confidence: 100% (programmatic — no ambiguity)")
        print(f"[Mem0] Critique: {critique_text}")

        travel_memory.process_feedback(
            user_id=user_id,
            signal_type="autonomous_failure",
            topic=f"search_quality: {state['messages'][-1].content[:50]}",
        )

        # Also write the failure pattern as a memory so future searches learn
        failure_insight = (
            f"Previous search failed quality check. "
            f"Critique feedback: {critique_text}. "
            f"Query was: {state['messages'][-1].content}"
        )
        travel_memory.write(
            user_id=user_id,
            content=failure_insight,
            agent_id="critique_agent",
            topic="search_quality_failure",
        )

    # ── Apply time-based decay to all memories ────────────────────────────────
    # Stale preferences fade naturally — 1% per session
    travel_memory.apply_decay(user_id=user_id, decay_rate=0.01)
    print(f"[Mem0] Applied session decay (rate: 1%)")

    state["memory_updated"] = True
    return state


# ── ORCHESTRATOR NODE (updated) ───────────────────────────────────────────────

from typing import Optional as _Optional


class OrchestratorDecision(BaseModel):
    route: Literal["entity_extraction", "web_search", "direct"] = Field(
        description=(
            "Route to 'entity_extraction' for hotel or accommodation queries. "
            "Route to 'web_search' for general travel or destination questions. "
            "Route to 'direct' for greetings, small talk, or anything unrelated to travel — "
            "and provide a short friendly response in direct_response."
        )
    )
    direct_response: _Optional[str] = Field(
        default=None,
        description="Required when route is 'direct'. A warm, brief reply to the user.",
    )


def orchestrator_node(state: AgentState) -> AgentState:
    """
    Routes the query and handles chitchat inline — no extra node needed.

    - entity_extraction  → hotel/accommodation query
    - web_search         → general travel question
    - direct             → greeting or off-topic; response written straight to summary,
                           graph skips search+summarize and goes to critique
    """
    llm = get_llm().with_structured_output(OrchestratorDecision)

    user_query  = state["messages"][-1].content
    user_memory = state.get("user_memory", "")

    base_prompt = (
        "You are the Orchestrator Planner Agent for a Smart Travel Planner. "
        "Route the user's query accurately. "
        "For greetings or off-topic input, respond directly with a warm message "
        "and set route to 'direct'."
    )
    system_prompt = f"{base_prompt}\n\n{user_memory}" if user_memory else base_prompt

    response: OrchestratorDecision = llm.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_query)]
    )

    if response.route == "direct":
        state["summary"]   = response.direct_response or "Hi! I'm your Smart Travel Planner. Ask me about hotels or destinations!"
        state["is_valid"]  = True
        state["next_node"] = "memory_write"   # skip search, summarize, and critique
    else:
        state["next_node"] = response.route

    return state


# ── ENTITY EXTRACTION NODE (unchanged) ───────────────────────────────────────

def entity_extraction_node(state: AgentState) -> AgentState:
    """Extracts entities for the hotel search."""
    llm = get_llm().with_structured_output(Entities)

    user_query    = state["messages"][-1].content
    system_prompt = (
        "You are an Entity Extraction Agent. "
        "Extract relevant details for a hotel search from the user query."
    )

    extracted: Entities = llm.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_query)]
    )

    state["entities"]  = extracted
    state["next_node"] = "hotel_search"
    return state


# ── HOTEL SEARCH NODE (unchanged) ────────────────────────────────────────────

def hotel_search_node(state: AgentState) -> AgentState:
    """Performs the SERP API Hotel Search using the extracted entities."""
    entities   = state.get("entities", {})
    city       = entities.get("city", "")
    landmark   = entities.get("landmark", "")
    base_query = f"{landmark} {city}".strip() or state["messages"][-1].content
    check_in   = entities.get("check_in_date")
    check_out  = entities.get("check_out_date")

    try:
        results = search_hotels(
            query=base_query, check_in_date=check_in, check_out_date=check_out
        )
        state["search_results"] = results
    except Exception as e:
        state["search_results"] = f"Error during hotel search: {str(e)}"

    state["next_node"] = "summarize"
    return state


# ── WEB SEARCH NODE (unchanged) ──────────────────────────────────────────────

def web_search_node(state: AgentState) -> AgentState:
    """Performs Tavily web search for general queries."""
    user_query             = state["messages"][-1].content
    results                = web_search(query=user_query)
    state["search_results"] = results
    state["next_node"]     = "summarize"
    return state


# ── SUMMARIZE NODE (updated) ──────────────────────────────────────────────────

def summarize_node(state: AgentState) -> AgentState:
    """
    Summarizes raw search results for the user.

    Memory injection: user preferences (e.g. "prefers budget hotels",
    "wants city center locations") are injected so the summary is
    personalised without the user needing to repeat themselves.
    """
    llm         = get_llm()
    user_query  = state["messages"][-1].content
    raw_results = state.get("search_results", "No results.")
    user_memory = state.get("user_memory", "")

    # ── Inject memory into summarisation prompt ───────────────────────────────
    base_prompt = (
        "You are a helpful Summarisation Agent. You will be given raw search results "
        "and the user's original query. Formulate a comprehensive, conversational, "
        "and clear response answering the user's query based strictly on the provided "
        "search results."
    )
    if user_memory:
        system_prompt = (
            f"{base_prompt}\n\n"
            f"Apply these known user preferences when crafting your response:\n"
            f"{user_memory}"
        )
    else:
        system_prompt = base_prompt

    content  = f"User Query: {user_query}\n\nSearch Results:\n{raw_results}"
    response = llm.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=content)]
    )

    state["summary"]   = response.content
    state["next_node"] = "critique"
    return state


# ── CRITIQUE NODE (updated — autonomous signal) ───────────────────────────────

class CritiqueDecision(BaseModel):
    is_valid: bool = Field(
        description="True if the summary adequately addresses the user's query."
    )
    critique: str = Field(
        description="A short explanation of the quality check."
    )


def critique_node(state: AgentState) -> AgentState:
    """
    Critiques the summary against the user query to ensure quality.

    AUTONOMOUS FEEDBACK SIGNAL:
    When is_valid=False, this is a 100% confidence programmatic signal.
    No human interpretation needed. memory_write_node will detect this
    and update memory directly — no accumulation required.

    This demonstrates the autonomous feedback loop:
      critique fails → memory learns what went wrong → next search improves
    """
    llm        = get_llm().with_structured_output(CritiqueDecision)
    user_query = state["messages"][-1].content
    summary    = state.get("summary", "")

    system_prompt = (
        "You are a strict Critique Agent. "
        "Perform a quality check on whether the drafted summary answers the query."
    )
    content  = f"User Query: {user_query}\n\nDrafted Summary:\n{summary}"
    response: CritiqueDecision = llm.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=content)]
    )

    state["is_valid"]  = response.is_valid
    state["critique"]  = response.critique
    state["next_node"] = "memory_write"     # always flows to memory_write next

    # Log the autonomous signal clearly
    if not response.is_valid:
        print(f"\n[Critique] ❌ Quality check FAILED")
        print(f"[Critique] This is an autonomous 100% confidence signal")
        print(f"[Critique] Memory will be updated without human input")
    else:
        print(f"\n[Critique] ✅ Quality check PASSED")

    return state