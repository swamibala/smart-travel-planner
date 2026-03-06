from langgraph.graph import StateGraph, START, END

from agents.state import AgentState
from agents.nodes import (
    orchestrator_node,
    entity_extraction_node,
    hotel_search_node,
    web_search_node,
    summarize_node,
    critique_node,
)


def route_from_orchestrator(state: AgentState):
    """
    Returns the next node to execute based on the chosen path from the orchestrator.
    """
    return state.get("next_node", "web_search")


def route_to_end(state: AgentState):
    """
    Terminal node routing.
    """
    return END


def build_graph():
    # 1. Define the State Graph
    workflow = StateGraph(AgentState)

    # 2. Add Nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("entity_extraction", entity_extraction_node)
    workflow.add_node("hotel_search", hotel_search_node)
    workflow.add_node("web_search", web_search_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("critique", critique_node)

    # 3. Add Edges
    workflow.add_edge(START, "orchestrator")

    # Orchestrator decides where to go
    workflow.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        {"entity_extraction": "entity_extraction", "web_search": "web_search"},
    )

    # Hotel Path
    workflow.add_edge("entity_extraction", "hotel_search")
    workflow.add_edge("hotel_search", "summarize")

    # Web Search Path
    workflow.add_edge("web_search", "summarize")

    # Shared Ending
    workflow.add_edge("summarize", "critique")

    workflow.add_conditional_edges("critique", route_to_end, {END: END})

    # Compile the graph
    app = workflow.compile()
    return app


# Expose compiled app
graph_app = build_graph()
