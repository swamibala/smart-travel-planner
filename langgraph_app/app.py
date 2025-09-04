from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, END
from tools.serpapi_tools import tools
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
    tool_calls: List[Dict]
    tool_output: str

# Define the Tool Executor node
def tool_executor_node(state: GraphState):
    tool_calls = state["tool_calls"]
    tool_output = []
    for call in tool_calls:
        tool_name = call.get("name")
        tool_args = call.get("args", {})
        for tool in tools:
            if hasattr(tool, "name") and tool.name == tool_name:
                try:
                    result = tool(**tool_args)
                except Exception as e:
                    result = f"Error executing tool '{tool_name}': {e}"
                tool_output.append(result)
    return {"tool_output": str(tool_output), "tool_calls": []}

# Build the LangGraph
def build_graph():
    workflow = StateGraph(GraphState)

    # Add the nodes
    workflow.add_node("orchestrator", orchestrator_agent_node)
    workflow.add_node("recommendation", recommendation_agent_node)
    workflow.add_node("clarification", clarification_agent_node)
    workflow.add_node("tool_executor", tool_executor_node)

    # Set the entry point
    workflow.set_entry_point("orchestrator")

    # Define the conditional edges from the orchestrator
    def route_orchestrator(state):
        if state.get("clarification_needed"):
            return "clarification"
        elif state.get("recommendation_needed"):
            return "recommendation"
        else:
            return END

    workflow.add_conditional_edges(
        "orchestrator",
        route_orchestrator
    )

    # Define edges from other agents
    workflow.add_edge("recommendation", "tool_executor")
    workflow.add_edge("tool_executor", "orchestrator")
    workflow.add_edge("clarification", END)

    return workflow.compile()

# Build and export the graph
app = build_graph()
