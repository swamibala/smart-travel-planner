from typing import TypedDict
from langgraph.graph import StateGraph, END, START
from tools.serpapi_tools import tools
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from agents import clarification_agent_node, recommendation_agent_node, orchestrator_agent_node, formatter_agent_node
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AnyMessage
from typing import Annotated
from langgraph.graph.message import add_messages
import os
import dotenv

dotenv.load_dotenv()


# Define the graph state
class GraphState(TypedDict):
    thread_id: str
    messages:Annotated[list[AnyMessage],add_messages]
    next_node: str
    clarification_needed: bool
    recommendation_needed: bool
    final_response_needed: bool


# Build the LangGraph
def build_graph():
    workflow = StateGraph(GraphState)

    # Add the nodes
    workflow.add_node("orchestrator", orchestrator_agent_node)
    workflow.add_node("clarification", clarification_agent_node)
    workflow.add_node("recommendation", recommendation_agent_node)
    workflow.add_node("formatter", formatter_agent_node)

    workflow.add_node("tools", ToolNode(tools))


    # Set the entry point
    workflow.add_edge(START, "orchestrator")

    # Define the conditional edges from the orchestrator
    def route_orchestrator(state):
        if state.get("clarification_needed"):
            return "clarification"
        elif state.get("recommendation_needed"):
            return "recommendation"
        elif state.get("final_response_needed"):
            return "formatter"        
        else:
            return END

    workflow.add_conditional_edges(
        "orchestrator",
        route_orchestrator
    )

    workflow.add_edge("clarification", "orchestrator")

    # Conditional edges for the recommendation agent
    def route_recommendation(state):
        messages = state.get("messages")
        if messages and messages[-1].tool_calls:
            return "tools"
        else:
            # Route back to orchestrator to re-evaluate the next step
            return "orchestrator"

    workflow.add_conditional_edges(
        "recommendation",
        route_recommendation,
        # This mapping is used for the conditional edges
        {"tools": "tools", "orchestrator": "orchestrator"}
    )
    
    workflow.add_edge("tools","recommendation")
    workflow.add_edge("formatter", END)

    
    # Check if the LangGraph API environment variable is set.
    # If it is, no custom checkpointer should be used.
    if os.getenv("LANGCHAIN_API_KEY"):
        memory = None
    else:
        # Use the InMemorySaver for local development only.
        memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

# Build and export the graph
app = build_graph()