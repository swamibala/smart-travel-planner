"""
agents/state.py
───────────────
AgentState extended with Mem0 memory fields.

New fields:
  user_id        → identifies the user across sessions (for Mem0 scoping)
  user_memory    → retrieved memory context injected into agent prompts
  feedback_signal → explicit or implicit feedback from user ("too expensive", "👎")
  memory_updated → whether memory was written this session
"""

from typing import TypedDict, List, Optional
from langchain_core.messages import BaseMessage


class Entities(TypedDict):
    city: Optional[str]
    landmark: Optional[str]
    radius: Optional[str]
    check_in_date: Optional[str]
    check_out_date: Optional[str]


class AgentState(TypedDict):
    # ── Core (existing) ───────────────────────────────────────────────────────
    messages:       List[BaseMessage]
    next_node:      str
    route:          Optional[str]   # "direct" | "hotel_search" | "web_search" — set once by orchestrator
    entities:       Optional[Entities]
    search_results: Optional[str]
    summary:        Optional[str]
    critique:       Optional[str]
    is_valid:       bool

    # ── Memory (new) ──────────────────────────────────────────────────────────
    user_id:         str            # e.g. "swami" — scopes all Mem0 reads/writes
    user_memory:     Optional[str]  # retrieved memories, injected into prompts
    feedback_signal: Optional[str]  # "explicit_negative" | "implicit_negative" | None
    memory_updated:  bool           # True if memory was written this session
    memory_ids:      Optional[List[str]]  # IDs written this session (for trace panel)