from typing import TypedDict, List, Optional
from langchain_core.messages import BaseMessage


class Entities(TypedDict):
    city: Optional[str]
    landmark: Optional[str]
    radius: Optional[str]
    check_in_date: Optional[str]
    check_out_date: Optional[str]


class AgentState(TypedDict):
    messages: List[BaseMessage]
    next_node: str  # Determines which node should run next based on the orchestrator's decision
    entities: Optional[Entities]  # Extracted entities for hotel searches
    search_results: Optional[str]  # Raw results from SERP API or Tavily
    summary: Optional[str]  # Final summary output
    critique: Optional[str]  # Evaluation from the critique node
    is_valid: bool  # Flag indicating if critique passed or failed
