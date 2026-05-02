"""
main.py
───────
Smart Travel Planner CLI — with Mem0 memory + feedback loop.

What's new vs the original:
  1. user_id is set at startup (scopes all memories to this user)
  2. After every response, user is asked for feedback
  3. Explicit 👎  → 100% confidence → memory updated directly
  4. Implicit     → 10% confidence  → accumulated across sessions
  5. Session ends → decay applied   → stale memories fade naturally

Two feedback paths demonstrated:
  CONVERSATIONAL:  user types feedback here → process_feedback()
  AUTONOMOUS:      critique_node fails      → process_feedback() in memory_write_node
"""

from langchain_core.messages import HumanMessage
from agents.graph import graph_app
from memory.mem0_manager import travel_memory


# ── Implicit signal keywords ──────────────────────────────────────────────────
# These phrases suggest dissatisfaction without explicit thumbs down
IMPLICIT_NEGATIVE_SIGNALS = [
    "too expensive", "too cheap", "not what i wanted", "explain more",
    "more detail", "too many", "too few", "not helpful", "wrong",
    "that's not right", "not accurate", "didn't answer",
]

def detect_implicit_signal(text: str) -> bool:
    """Returns True if the feedback text contains an implicit negative signal."""
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in IMPLICIT_NEGATIVE_SIGNALS)


def collect_feedback(user_id: str, last_query: str) -> str | None:
    """
    Collects user feedback after every response.

    Returns:
      "explicit_negative"  if user typed 👎 or 'bad'
      "explicit_positive"  if user typed 👍 or 'good'
      "implicit_negative"  if user's feedback contains implicit signal
      None                 if user skipped feedback
    """
    print("\n─────────────────────────────────────────")
    print("Feedback (press Enter to skip):")
    print("  👍  Type 'good' or '👍'")
    print("  👎  Type 'bad'  or '👎'")
    print("  Or describe what was wrong (e.g. 'too expensive')")
    print("─────────────────────────────────────────")

    feedback = input("Your feedback: ").strip()

    if not feedback:
        return None

    # ── Explicit signals ──────────────────────────────────────────────────────
    if feedback.lower() in ("bad", "👎", "thumbs down", "negative"):
        print(f"\n[Feedback] Explicit 👎 detected")
        print(f"[Feedback] Confidence: 100% → memory will update directly")
        travel_memory.process_feedback(
            user_id=user_id,
            signal_type="explicit_negative",
            topic=last_query,
        )
        return "explicit_negative"

    if feedback.lower() in ("good", "👍", "thumbs up", "positive", "great", "perfect"):
        print(f"\n[Feedback] Explicit 👍 detected")
        print(f"[Feedback] Confidence: 100% → memory reinforced")
        travel_memory.process_feedback(
            user_id=user_id,
            signal_type="explicit_positive",
            topic=last_query,
        )
        return "explicit_positive"

    # ── Implicit signals ──────────────────────────────────────────────────────
    if detect_implicit_signal(feedback):
        print(f"\n[Feedback] Implicit signal detected: '{feedback}'")
        print(f"[Feedback] Confidence: 10% → accumulating across sessions")
        print(f"[Feedback] (5 implicit signals = 50% → HITL flag)")
        travel_memory.process_feedback(
            user_id=user_id,
            signal_type="implicit_negative",
            topic=last_query,
        )
        return "implicit_negative"

    # ── Unrecognised — store as preference update ─────────────────────────────
    print(f"\n[Feedback] Storing as user preference update...")
    travel_memory.write(
        user_id=user_id,
        content=f"User said about the last response: {feedback}",
        agent_id="feedback_collector",
        topic="user_feedback",
    )
    return None


# ── Main CLI loop ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Smart Travel Planner — with Mem0 Memory + Feedback Loop")
    print("=" * 60)

    # User identification — scopes all memories
    user_id = input("\nYour name (used to scope your memories): ").strip()
    if not user_id:
        user_id = "default_user"

    print(f"\nWelcome, {user_id}! Your preferences will be remembered across sessions.")
    print("Type 'quit' to exit.\n")

    messages      = []
    last_query    = ""

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ("quit", "exit", "bye"):
            print(f"\n[Mem0] Saving session... goodbye {user_id}!")
            break

        if not user_input:
            continue

        last_query = user_input
        messages.append(HumanMessage(content=user_input))

        # ── Invoke graph ──────────────────────────────────────────────────────
        print(f"\n[Graph] Processing your request...\n")

        result = graph_app.invoke({
            "messages":        messages,
            "user_id":         user_id,           # Mem0 user scope
            "user_memory":     None,               # filled by memory_read_node
            "feedback_signal": None,
            "memory_updated":  False,
            "next_node":       "",
            "entities":        None,
            "search_results":  None,
            "summary":         None,
            "critique":        None,
            "is_valid":        True,
        })

        # ── Display response ──────────────────────────────────────────────────
        summary  = result.get("summary", "No response generated.")
        critique = result.get("critique", "")
        is_valid = result.get("is_valid", True)

        print("\n" + "=" * 60)
        print("Assistant:", summary)
        print("=" * 60)

        if not is_valid:
            print(f"\n⚠️  [Quality] This response may be incomplete.")
            print(f"   Critique: {critique}")
            print(f"   [Mem0] Autonomous signal sent — memory updated for next time")

        # ── Collect conversational feedback ───────────────────────────────────
        feedback_type = collect_feedback(user_id, last_query)

        if feedback_type:
            print(f"\n[Mem0] Feedback recorded: {feedback_type}")
            print(f"[Mem0] This will improve your next session automatically")

        print()


if __name__ == "__main__":
    main()