"""
tests/test_routing.py
─────────────────────
Smoke tests for the orchestrator's three routing paths and the
memory_write_node's "skip on greeting" behaviour.

We mock the Gemini LLM so tests are fast, deterministic, and offline.
"""

from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage

import agents.nodes as nodes
from agents.nodes import (
    orchestrator_node,
    memory_write_node,
    OrchestratorDecision,
)


def _state(query: str, **overrides) -> dict:
    base = {
        "messages":       [HumanMessage(content=query)],
        "user_id":        "tester",
        "user_memory":    "",
        "next_node":      "",
        "route":          None,
        "entities":       None,
        "search_results": None,
        "summary":        None,
        "critique":       None,
        "is_valid":       True,
        "memory_updated": False,
        "memory_ids":     None,
    }
    base.update(overrides)
    return base


def _patch_orchestrator_llm(decision: OrchestratorDecision):
    """Patches get_llm() so orchestrator returns the given decision."""
    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value.invoke.return_value = decision
    return patch.object(nodes, "get_llm", return_value=fake_llm)


# ── Routing tests ────────────────────────────────────────────────────────────

def test_greeting_routes_to_direct():
    decision = OrchestratorDecision(route="direct", direct_response="Hi there!")
    with _patch_orchestrator_llm(decision):
        out = orchestrator_node(_state("Hi"))
    assert out["route"]     == "direct"
    assert out["next_node"] == "memory_write"   # skips search + critique
    assert out["is_valid"]  is True
    assert out["summary"]   == "Hi there!"


def test_hotel_query_routes_to_hotel_search():
    decision = OrchestratorDecision(route="entity_extraction")
    with _patch_orchestrator_llm(decision):
        out = orchestrator_node(_state("Find me a hotel in Paris"))
    assert out["route"]     == "hotel_search"
    assert out["next_node"] == "entity_extraction"


def test_general_query_routes_to_web_search():
    decision = OrchestratorDecision(route="web_search")
    with _patch_orchestrator_llm(decision):
        out = orchestrator_node(_state("What is the weather in Tokyo?"))
    assert out["route"]     == "web_search"
    assert out["next_node"] == "web_search"


# ── Memory-write skip behaviour ──────────────────────────────────────────────

def test_memory_write_skipped_for_greeting(monkeypatch):
    """Greetings have no search_results → memory_write must NOT call write()."""
    nodes.travel_memory.write.reset_mock()
    nodes.travel_memory.process_feedback.reset_mock()

    state = _state("Hi", search_results=None, summary="Hi there!")
    out = memory_write_node(state)

    nodes.travel_memory.write.assert_not_called()
    nodes.travel_memory.process_feedback.assert_not_called()
    assert out["memory_updated"] is False
    assert out["memory_ids"]     == []


def test_memory_write_runs_for_travel_query():
    """Travel queries with search_results SHOULD persist preferences."""
    nodes.travel_memory.write.reset_mock()
    nodes.travel_memory.write.return_value = ["mem-1", "mem-2"]

    state = _state(
        "Find me a hotel in Paris",
        search_results="<hotel data>",
        summary="Here are 3 hotels...",
        is_valid=True,
    )
    out = memory_write_node(state)

    nodes.travel_memory.write.assert_called_once()
    assert out["memory_updated"] is True
    assert out["memory_ids"]     == ["mem-1", "mem-2"]


def test_iso_date_normalizer():
    """_to_iso_date must handle all natural-language variants the LLM might produce."""
    from tools.serpapi_tools import _to_iso_date

    assert _to_iso_date("2026-05-10")     == "2026-05-10"   # already correct
    assert _to_iso_date("10th may 2026")  == "2026-05-10"   # ordinal, lowercase month
    assert _to_iso_date("10th May 2026")  == "2026-05-10"   # ordinal, title-case
    assert _to_iso_date("May 10 2026")    == "2026-05-10"   # month-first
    assert _to_iso_date("1st January 2027") == "2027-01-01"
    assert _to_iso_date("totally wrong")  is None            # unparseable → None


def test_critique_failure_fires_autonomous_signal():
    """is_valid=False on a travel query → autonomous_failure feedback."""
    nodes.travel_memory.write.reset_mock()
    nodes.travel_memory.process_feedback.reset_mock()
    nodes.travel_memory.write.return_value = ["mem-1"]

    state = _state(
        "Find me a hotel",
        search_results="<results>",
        summary="bad summary",
        is_valid=False,
        critique="Did not answer the query",
    )
    memory_write_node(state)

    nodes.travel_memory.process_feedback.assert_called_once()
    kwargs = nodes.travel_memory.process_feedback.call_args.kwargs
    assert kwargs["signal_type"] == "autonomous_failure"
