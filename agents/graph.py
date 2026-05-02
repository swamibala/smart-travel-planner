"""
agents/graph.py
───────────────
LangGraph state graph with Mem0 memory layer wired in.

Updated flow:
  START
    → memory_read       ← NEW: retrieves user memories before anything runs
    → orchestrator      (memory-aware: user_memory injected into prompt)
    → entity_extraction | web_search
    → hotel_search      | (web_search path)
    → summarize         (memory-aware: user preferences injected)
    → critique          (autonomous signal: is_valid=False → 100% feedback)
    → memory_write      ← NEW: extracts insights, processes feedback, applies decay
    → END
"""

from langgraph.graph import StateGraph, START, END

from agents.state import AgentState
from agents.nodes import (
    memory_read_node,
    memory_write_node,
    orchestrator_node,
    entity_extraction_node,
    hotel_search_node,
    web_search_node,
    summarize_node,
    critique_node,
)


def route_from_orchestrator(state: AgentState):
    """Routes to entity_extraction, web_search, or memory_write (direct/chitchat)."""
    return state.get("next_node", "web_search")


def build_graph():
    workflow = StateGraph(AgentState)

    # ── Nodes ─────────────────────────────────────────────────────────────────
    workflow.add_node("memory_read",       memory_read_node)
    workflow.add_node("orchestrator",      orchestrator_node)
    workflow.add_node("entity_extraction", entity_extraction_node)
    workflow.add_node("hotel_search",      hotel_search_node)
    workflow.add_node("web_search",        web_search_node)
    workflow.add_node("summarize",         summarize_node)
    workflow.add_node("critique",          critique_node)
    workflow.add_node("memory_write",      memory_write_node)      # NEW

    # ── Edges ─────────────────────────────────────────────────────────────────

    # Memory read is the new entry point — runs before orchestrator
    workflow.add_edge(START, "memory_read")
    workflow.add_edge("memory_read", "orchestrator")

    # Orchestrator routes based on query type
    workflow.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        {
            "entity_extraction": "entity_extraction",
            "web_search":        "web_search",
            "memory_write":      "memory_write",   # direct path — skips search, summarize, critique
        },
    )

    # Hotel path
    workflow.add_edge("entity_extraction", "hotel_search")
    workflow.add_edge("hotel_search",      "summarize")

    # Web search path
    workflow.add_edge("web_search", "summarize")

    # Shared ending — critique always flows to memory_write
    workflow.add_edge("summarize",     "critique")
    workflow.add_edge("critique",      "memory_write")     # NEW
    workflow.add_edge("memory_write",  END)                # NEW

    return workflow.compile()


graph_app = build_graph()