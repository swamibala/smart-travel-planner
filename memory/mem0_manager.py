"""
memory/mem0_manager.py
─────────────────────
The dedicated Mem0 memory manager — the "Chief of Staff" between agents.

Responsibilities:
  - READ:  Retrieve relevant memories before any agent runs
  - WRITE: Extract lasting insights after every agent run
  - FEEDBACK: Process explicit (👎) and implicit ("too expensive") signals
  - DECAY:    Periodically reduce confidence of stale memories
  - ARCHIVE:  Move zero-score memories to cold storage (never hard delete)

Signal confidence weights:
  Explicit negative (👎)        → 1.0  (100%) → update directly
  Implicit follow-up            → 0.10 (10%)  → accumulate across sessions
  Accumulated pattern (5x)      → 0.50 (50%)  → flag for HITL
  Autonomous (critique failed)  → 1.0  (100%) → update directly

Decision thresholds:
  score > 0.8   → update memory directly
  0.3–0.8       → flag for HITL review
  < 0.3         → accumulate (watch for pattern)
  score == 0    → archive (never hard delete)
"""

import os
import json
import sqlite3
from datetime import datetime
from mem0 import Memory


# ── Mem0 Local Config ────────────────────────────────────────────────────────
# Uses Google Gemini for LLM extraction + Google embeddings
# No OpenAI key needed — runs fully locally with persistent qdrant storage

def _build_mem0_config() -> dict:
    return {
        "llm": {
            "provider": "litellm",
            "config": {
                "model": "gemini/gemini-2.5-flash",
                "api_key": os.environ.get("GOOGLE_API_KEY"),
            },
        },
        "embedder": {
            "provider": "gemini",
            "config": {
                "model": "models/gemini-embedding-001",
                "api_key": os.environ.get("GOOGLE_API_KEY"),
            },
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "smart_travel_planner",
                "path": "./memory_store",      # persists to disk
            },
        },
    }


# ── Signal Score Store (SQLite) ───────────────────────────────────────────────
# Tracks accumulated confidence scores and implicit signal counts
# Separate from Mem0's vector store — lightweight bookkeeping

SCORE_DB = "./memory_store/signal_scores.db"

def _init_score_db():
    os.makedirs("./memory_store", exist_ok=True)
    conn = sqlite3.connect(SCORE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_scores (
            memory_id     TEXT PRIMARY KEY,
            user_id       TEXT,
            topic         TEXT,
            score         REAL DEFAULT 1.0,
            implicit_hits INTEGER DEFAULT 0,
            archived      INTEGER DEFAULT 0,
            last_updated  TEXT
        )
    """)
    conn.commit()
    conn.close()


def _get_score(memory_id: str) -> dict | None:
    conn = sqlite3.connect(SCORE_DB)
    row = conn.execute(
        "SELECT * FROM memory_scores WHERE memory_id = ?", (memory_id,)
    ).fetchone()
    conn.close()
    if row:
        return {
            "memory_id": row[0], "user_id": row[1], "topic": row[2],
            "score": row[3], "implicit_hits": row[4],
            "archived": row[5], "last_updated": row[6]
        }
    return None


def _upsert_score(memory_id: str, user_id: str, topic: str,
                   score: float, implicit_hits: int = 0, archived: int = 0):
    conn = sqlite3.connect(SCORE_DB)
    conn.execute("""
        INSERT INTO memory_scores
            (memory_id, user_id, topic, score, implicit_hits, archived, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(memory_id) DO UPDATE SET
            score         = excluded.score,
            implicit_hits = excluded.implicit_hits,
            archived      = excluded.archived,
            last_updated  = excluded.last_updated
    """, (memory_id, user_id, topic, score, implicit_hits, archived,
          datetime.now().isoformat()))
    conn.commit()
    conn.close()


# ── TravelMemoryManager ───────────────────────────────────────────────────────

class TravelMemoryManager:
    """
    The dedicated memory manager sitting between all agents in the
    Smart Travel Planner. Handles read, write, feedback, decay, and
    resurrection for both conversational and autonomous signals.
    """

    def __init__(self):
        _init_score_db()
        self.mem0 = Memory.from_config(_build_mem0_config())

    # ── READ ──────────────────────────────────────────────────────────────────

    def read(self, user_id: str, query: str) -> str:
        """
        Retrieve relevant memories before an agent runs.
        Called at the START of every graph execution.

        Returns a formatted string ready to inject into any system prompt.
        """
        try:
            results = self.mem0.search(
                query=query,
                filters={"user_id": user_id},
                top_k=5,
            )

            if not results or not results.get("results"):
                return ""

            # Filter out archived memories
            active = [
                r for r in results["results"]
                if not self._is_archived(r.get("id", ""))
            ]

            if not active:
                return ""

            lines = ["[User Memory — from past sessions]"]
            for r in active:
                lines.append(f"  • {r.get('memory', '')}")

            return "\n".join(lines)

        except Exception as e:
            print(f"[Mem0] Read error: {e}")
            return ""

    # ── WRITE ─────────────────────────────────────────────────────────────────

    def write(self, user_id: str, content: str, agent_id: str,
              topic: str = "general") -> list[str]:
        """
        Extract lasting insights from agent output and store them.
        Called at the END of every graph execution (memory_write_node).

        Mem0 internally uses an LLM to separate:
          - Lasting user facts   → user memory (cross-session)
          - Task-specific noise  → ignored (not stored)
        """
        try:
            result = self.mem0.add(
                messages=content,
                user_id=user_id,
                agent_id=agent_id,
                metadata={"topic": topic},
            )

            memory_ids = []
            if result and result.get("results"):
                for r in result["results"]:
                    mid = r.get("id", "")
                    if mid:
                        _upsert_score(mid, user_id, topic, score=1.0)
                        memory_ids.append(mid)

            return memory_ids

        except Exception as e:
            print(f"[Mem0] Write error: {e}")
            return []

    # ── FEEDBACK LOOP ─────────────────────────────────────────────────────────

    def process_feedback(self, user_id: str, signal_type: str,
                          topic: str, memory_id: str | None = None):
        """
        Process feedback signals and update memory scores accordingly.

        signal_type options:
          "explicit_negative"  → 100% confidence → update directly
          "explicit_positive"  → 100% confidence → reinforce
          "implicit_negative"  → 10% confidence  → accumulate
          "autonomous_failure" → 100% confidence → update directly (critique node)

        This is the core feedback loop that makes memory improve over time.
        """
        # ── Signal weight assignment ──────────────────────────────────────────
        weights = {
            "explicit_negative":  1.0,    # user clicked 👎
            "explicit_positive":  1.0,    # user clicked 👍
            "implicit_negative":  0.10,   # "too expensive", "explain more"
            "autonomous_failure": 1.0,    # critique_node: is_valid=False
        }
        confidence = weights.get(signal_type, 0.0)

        if confidence == 0.0:
            return  # no actionable signal

        # ── Retrieve or create score record ───────────────────────────────────
        if memory_id:
            record = _get_score(memory_id)
        else:
            # Search for most relevant memory to update
            results = self.mem0.search(query=topic, filters={"user_id": user_id}, top_k=1)
            if results and results.get("results"):
                memory_id = results["results"][0].get("id")
                record = _get_score(memory_id) if memory_id else None
            else:
                record = None

        if not record and memory_id:
            _upsert_score(memory_id, user_id, topic, score=1.0)
            record = _get_score(memory_id)

        if not record:
            print(f"[Mem0] No memory found for topic: {topic}")
            return

        # ── Score update logic ────────────────────────────────────────────────
        if signal_type in ("explicit_negative", "autonomous_failure"):
            new_score = max(0.0, record["score"] - confidence)
            implicit_hits = record["implicit_hits"]

        elif signal_type == "implicit_negative":
            # Accumulate implicit signals — 10% each
            implicit_hits = record["implicit_hits"] + 1
            new_score = max(0.0, record["score"] - confidence)
            print(f"[Mem0] Implicit signal #{implicit_hits} for '{topic}' "
                  f"(accumulated confidence: {implicit_hits * 0.10:.0%})")

        elif signal_type == "explicit_positive":
            new_score = min(1.0, record["score"] + confidence)
            implicit_hits = record["implicit_hits"]

        else:
            return

        # ── Decision thresholds ───────────────────────────────────────────────
        if new_score <= 0.0:
            self._archive(memory_id, user_id, topic)
            print(f"[Mem0] Memory archived (score=0): '{topic}'")

        elif new_score <= 0.3:
            print(f"[Mem0] Watching pattern for '{topic}' "
                  f"(score={new_score:.2f} < 0.3, accumulating...)")
            _upsert_score(memory_id, user_id, topic, new_score, implicit_hits)

        elif 0.3 < new_score <= 0.8:
            print(f"[Mem0] ⚠️  HITL FLAG: Memory for '{topic}' needs review "
                  f"(score={new_score:.2f})")
            _upsert_score(memory_id, user_id, topic, new_score, implicit_hits)

        else:
            # score > 0.8 — reinforce or keep
            _upsert_score(memory_id, user_id, topic, new_score, implicit_hits)
            if signal_type == "explicit_positive":
                print(f"[Mem0] ✅ Memory reinforced: '{topic}' (score={new_score:.2f})")

    # ── DECAY ─────────────────────────────────────────────────────────────────

    def apply_decay(self, user_id: str, decay_rate: float = 0.01):
        """
        Periodically reduce confidence of all memories for a user.
        Call this at session end to fade stale preferences over time.

        decay_rate=0.01 means 1% reduction per session.
        A memory stored 100 sessions ago with no reinforcement hits zero.
        """
        conn = sqlite3.connect(SCORE_DB)
        rows = conn.execute(
            "SELECT memory_id, topic, score FROM memory_scores "
            "WHERE user_id = ? AND archived = 0",
            (user_id,)
        ).fetchall()
        conn.close()

        for memory_id, topic, score in rows:
            new_score = max(0.0, score - decay_rate)
            if new_score <= 0.0:
                self._archive(memory_id, user_id, topic)
                print(f"[Mem0] Decayed to zero → archived: '{topic}'")
            else:
                _upsert_score(memory_id, user_id, topic, new_score)

    # ── RESURRECTION ─────────────────────────────────────────────────────────

    def check_resurrection(self, user_id: str, query: str) -> str:
        """
        Before treating a signal as new, check the archive first.
        If the pattern existed before, fast-track confidence to 60%.

        This is why we never hard delete — returning patterns get
        rebuilt faster than truly new preferences.
        """
        try:
            conn = sqlite3.connect(SCORE_DB)
            archived = conn.execute(
                "SELECT memory_id, topic FROM memory_scores "
                "WHERE user_id = ? AND archived = 1",
                (user_id,)
            ).fetchall()
            conn.close()

            for memory_id, topic in archived:
                if any(word in query.lower() for word in topic.lower().split()):
                    # Pattern matches archived memory — resurrect it
                    _upsert_score(memory_id, user_id, topic,
                                   score=0.6,      # fast-tracked, not starting from 0
                                   archived=0)
                    print(f"[Mem0] 🔄 Resurrected memory: '{topic}' "
                          f"(score fast-tracked to 60%)")
                    return topic

        except Exception as e:
            print(f"[Mem0] Resurrection check error: {e}")

        return ""

    # ── HELPERS ───────────────────────────────────────────────────────────────

    def _archive(self, memory_id: str, user_id: str, topic: str):
        """Move to cold storage. Never hard delete."""
        _upsert_score(memory_id, user_id, topic, score=0.0, archived=1)

    def _is_archived(self, memory_id: str) -> bool:
        record = _get_score(memory_id)
        return bool(record and record["archived"])


# ── Singleton ─────────────────────────────────────────────────────────────────
# One manager instance shared across all nodes in the graph

travel_memory = TravelMemoryManager()