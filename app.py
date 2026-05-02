"""
app.py
──────
Streamlit UI for Smart Travel Planner.
Replaces the CLI main.py with a visual interface that shows:
  - Chat conversation
  - Per-response observability trace (memory, route, entities, critique)
  - 👍/👎 feedback buttons + text feedback input
"""

import streamlit as st
from langchain_core.messages import HumanMessage
from agents.graph import graph_app
from memory.mem0_manager import travel_memory

IMPLICIT_SIGNALS = [
    "too expensive", "too cheap", "not what i wanted", "explain more",
    "more detail", "too many", "too few", "not helpful", "wrong",
    "that's not right", "not accurate", "didn't answer",
]

st.set_page_config(
    page_title="Smart Travel Planner",
    page_icon="🌍",
    layout="wide",
)

# ── Init session state ────────────────────────────────────────────────────────
if "user_id" not in st.session_state:
    st.session_state.user_id = "default_user"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "lc_messages" not in st.session_state:
    st.session_state.lc_messages = []
if "last_query" not in st.session_state:
    st.session_state.last_query = ""

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🌍 Smart Travel Planner")
    st.caption("Powered by Gemini 2.5 Flash · LangGraph · Mem0")
    st.divider()

    new_user_id = st.text_input(
        "Your name",
        value=st.session_state.user_id,
        placeholder="Enter your name...",
        help="Scopes your memory. Change to switch users.",
    )
    if new_user_id and new_user_id != st.session_state.user_id:
        st.session_state.user_id = new_user_id
        st.session_state.messages = []
        st.session_state.lc_messages = []
        st.rerun()

    st.caption("Your preferences are remembered across sessions via Mem0.")
    st.divider()

    st.subheader("📊 Session")
    query_count = sum(1 for m in st.session_state.messages if m["role"] == "user")
    st.metric("Queries", query_count)

    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.lc_messages = []
        st.rerun()

# ── Page title ────────────────────────────────────────────────────────────────
st.title("🌍 Smart Travel Planner")

# ── Render conversation ───────────────────────────────────────────────────────
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

        if msg["role"] == "assistant":
            trace = msg.get("trace", {})
            route = trace.get("route") or "unknown"

            ROUTE_LABELS = {
                "direct":       "💬 Direct reply (greeting / chitchat)",
                "hotel_search": "🏨 Hotel search (SerpAPI)",
                "web_search":   "🌐 Web search (Tavily)",
                "unknown":      "❓ Unknown",
            }

            with st.expander(f"🔍 Trace — Route: {ROUTE_LABELS[route]}"):
                # ── 1. Flow ───────────────────────────────────────────────────
                st.markdown("**1️⃣  Flow**")
                if route == "direct":
                    st.code("memory_read → orchestrator → memory_write", language="text")
                    st.caption("Greeting/chitchat — search, summarize, and critique are skipped.")
                elif route == "hotel_search":
                    st.code(
                        "memory_read → orchestrator → entity_extraction → "
                        "hotel_search → summarize → critique → memory_write",
                        language="text",
                    )
                else:
                    st.code(
                        "memory_read → orchestrator → web_search → "
                        "summarize → critique → memory_write",
                        language="text",
                    )

                st.divider()

                # ── 2. Input / Output ─────────────────────────────────────────
                left, right = st.columns(2)
                with left:
                    st.markdown("**2️⃣  Input (user query)**")
                    st.code(trace.get("query", ""), language="text")
                with right:
                    st.markdown("**3️⃣  Output (assistant)**")
                    st.code((trace.get("summary") or "")[:500], language="text")

                st.divider()

                # ── 3. Memory read ────────────────────────────────────────────
                st.markdown("**4️⃣  Memory Read** (injected into prompts)")
                if trace.get("user_memory"):
                    st.info(trace["user_memory"])
                else:
                    st.caption("No relevant memories — fresh start for this user.")

                # ── 4. Entities (hotel path only) ─────────────────────────────
                if route == "hotel_search":
                    st.markdown("**5️⃣  Extracted Entities**")
                    entities = trace.get("entities") or {}
                    if isinstance(entities, dict) and any(entities.values()):
                        st.json({k: v for k, v in entities.items() if v})
                    else:
                        st.caption("None extracted.")

                # ── 5. Quality check (skipped on direct path) ────────────────
                st.markdown("**6️⃣  Quality Check (critique)**")
                if route == "direct":
                    st.caption("Skipped — direct replies don't go through critique.")
                elif trace.get("is_valid", True):
                    st.success(f"✅ Passed — {trace.get('critique', '')}")
                else:
                    st.error(f"❌ Failed — autonomous signal sent to memory. {trace.get('critique', '')}")

                # ── 6. Memory write ──────────────────────────────────────────
                st.markdown("**7️⃣  Memory Write**")
                if trace.get("memory_updated"):
                    n = len(trace.get("memory_ids") or [])
                    st.success(f"Stored {n} preference entry(s) for next session.")
                else:
                    st.caption("Nothing stored — no lasting preferences extracted from this turn.")

                # ── 7. Raw search results (collapsed) ────────────────────────
                if trace.get("search_results"):
                    with st.expander("📄 Raw Search Results"):
                        st.text(str(trace["search_results"])[:3000])

            # Feedback row — only for the latest assistant message
            if i == len(st.session_state.messages) - 1 and not msg.get("feedback_done"):
                st.write("**Was this helpful?**")
                col_pos, col_neg, col_text, col_send = st.columns([1, 1, 6, 1])

                with col_pos:
                    if st.button("👍", key=f"pos_{i}", use_container_width=True):
                        travel_memory.process_feedback(
                            user_id=st.session_state.user_id,
                            signal_type="explicit_positive",
                            topic=st.session_state.last_query,
                        )
                        st.session_state.messages[i]["feedback_done"] = True
                        st.toast("Memory reinforced ✅")
                        st.rerun()

                with col_neg:
                    if st.button("👎", key=f"neg_{i}", use_container_width=True):
                        travel_memory.process_feedback(
                            user_id=st.session_state.user_id,
                            signal_type="explicit_negative",
                            topic=st.session_state.last_query,
                        )
                        st.session_state.messages[i]["feedback_done"] = True
                        st.toast("Memory updated 📝")
                        st.rerun()

                with col_text:
                    feedback_text = st.text_input(
                        "text_feedback",
                        key=f"fb_{i}",
                        label_visibility="collapsed",
                        placeholder="e.g. too expensive, wanted more budget options...",
                    )

                with col_send:
                    if st.button("Send", key=f"send_{i}", use_container_width=True):
                        if feedback_text:
                            if any(sig in feedback_text.lower() for sig in IMPLICIT_SIGNALS):
                                travel_memory.process_feedback(
                                    user_id=st.session_state.user_id,
                                    signal_type="implicit_negative",
                                    topic=st.session_state.last_query,
                                )
                                st.toast("Implicit signal recorded (10% confidence) 📊")
                            else:
                                travel_memory.write(
                                    user_id=st.session_state.user_id,
                                    content=f"User feedback: {feedback_text}",
                                    agent_id="feedback_collector",
                                    topic="user_feedback",
                                )
                                st.toast("Feedback stored as preference 📝")
                            st.session_state.messages[i]["feedback_done"] = True
                            st.rerun()

# ── Chat input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about hotels or travel destinations..."):
    st.session_state.last_query = prompt
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.lc_messages.append(HumanMessage(content=prompt))

    with st.spinner("Searching and planning..."):
        result = graph_app.invoke({
            "messages":        st.session_state.lc_messages,
            "user_id":         st.session_state.user_id,
            "user_memory":     None,
            "feedback_signal": None,
            "memory_updated":  False,
            "memory_ids":      None,
            "next_node":       "",
            "route":           None,
            "entities":        None,
            "search_results":  None,
            "summary":         None,
            "critique":        None,
            "is_valid":        True,
        })

    st.session_state.messages.append({
        "role": "assistant",
        "content": result.get("summary", "No response generated."),
        "trace": {
            "query":          prompt,
            "summary":        result.get("summary"),
            "route":          result.get("route"),
            "user_memory":    result.get("user_memory"),
            "entities":       result.get("entities"),
            "is_valid":       result.get("is_valid", True),
            "critique":       result.get("critique", ""),
            "memory_updated": result.get("memory_updated", False),
            "memory_ids":     result.get("memory_ids"),
            "search_results": result.get("search_results"),
        },
        "feedback_done": False,
    })

    st.rerun()
