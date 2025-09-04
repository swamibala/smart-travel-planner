from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, END
from tools.serpapi_tools import tools
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from agents import clarification_agent_node, recommendation_agent_node, orchestrator_agent_node

# Define the graph state
class GraphState(TypedDict):
    thread_id: str
    current_request: str
    itinerary_data: Dict
    clarification_needed: bool
    recommendation_needed: bool
    agent_response: str
    final_response: str

def response_node(state: GraphState) -> GraphState:
    # Combine or finalize responses before ending
    state["final_response"] = state.get("agent_response", "")
    return state

# Build the LangGraph
def build_graph():
    workflow = StateGraph(GraphState)

    # Add the nodes
    workflow.add_node("orchestrator", orchestrator_agent_node)
    workflow.add_node("recommendation", recommendation_agent_node)
    workflow.add_node("clarification", clarification_agent_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("response", response_node)


    # Set the entry point
    workflow.set_entry_point("orchestrator")

    # Define the conditional edges from the orchestrator
    def route_orchestrator(state):
        if state.get("clarification_needed"):
            return "clarification"
        elif state.get("recommendation_needed"):
            return "recommendation"
        else:
            return "response"

    workflow.add_conditional_edges(
        "orchestrator",
        route_orchestrator
    )

    # Define edges from other agents
    workflow.add_conditional_edges("recommendation",
                                   # If the latest message (result) from recommendation is a tool call -> tools_condition routes to tools
                                   # If the latest message (result) from recommendation is a not a tool call -> tools_condition routes to orchestrator
                                   tools_condition)
    workflow.add_edge("tools", "recommendation")
    workflow.add_edge("clarification", "response")
    workflow.add_edge("response", END)
    return workflow.compile()

# Build and export the graph
app = build_graph()
