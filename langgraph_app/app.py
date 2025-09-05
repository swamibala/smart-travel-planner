from typing import TypedDict
from langgraph.graph import StateGraph, END, START
from tools.serpapi_tools import tools
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from agents import clarification_agent_node, recommendation_agent_node, orchestrator_agent_node
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AnyMessage
from typing import Annotated
from langgraph.graph.message import add_messages

# Define the graph state
class GraphState(TypedDict):
    thread_id: str
    messages:Annotated[list[AnyMessage],add_messages]
    next_node: str


# Build the LangGraph
def build_graph():
    workflow = StateGraph(GraphState)

    # Add the nodes
    workflow.add_node("orchestrator", orchestrator_agent_node)
    workflow.add_node("clarification", clarification_agent_node)
    workflow.add_node("recommendation", recommendation_agent_node)
    workflow.add_node("tools", ToolNode(tools))


    # Set the entry point
    workflow.add_edge(START, "orchestrator")

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

    workflow.add_edge("orchestrator", "clarification")
    workflow.add_edge("clarification", END)

    workflow.add_edge("orchestrator", "recommendation")
    workflow.add_conditional_edges(
        "recommendation",
        tools_condition,
        {"__end__": END, "tools": "tools"}
    )
    workflow.add_edge("tools","recommendation")
    workflow.add_edge("recommendation", END)
    
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

# Build and export the graph
app = build_graph()