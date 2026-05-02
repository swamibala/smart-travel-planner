# CLAUDE.md — AI Agent House Rules

## Stack
- Python 3.12 · uv (dependency manager) · LangGraph · Gemini 2.5 Flash · Mem0 · Qdrant · Streamlit
- Run commands with `uv run …`, not bare `python …`
- Install packages with `uv add <pkg>`, not `pip install`

## Folder contract
| Path | Purpose |
|---|---|
| `agents/state.py` | `AgentState` TypedDict — only place to add state fields |
| `agents/nodes.py` | All LangGraph node functions |
| `agents/graph.py` | Graph wiring only — no business logic |
| `memory/mem0_manager.py` | All Mem0 interactions — do not call `mem0` directly from nodes |
| `app.py` | Streamlit UI entry point |
| `main.py` | CLI entry point |

## Mem0 / Qdrant gotchas
- LLM provider is `"litellm"` with model `"gemini/gemini-2.5-flash"` — `litellm` must be installed
- Qdrant runs **embedded** at `./memory_store/` — no Docker or external server needed
- SQLite signal scores live at `./memory_store/signal_scores.db` — never hard-delete rows, use archive flag

## Conventions
- observability is in the Streamlit trace panel
- All memory reads/writes go through the `travel_memory` singleton in `mem0_manager.py`
- Feedback signals: `explicit_negative/positive` = 100% · `implicit_negative` = 10% · `autonomous_failure` = 100%
- `user_id` scopes all memories — always pass it through `AgentState`
