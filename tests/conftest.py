"""
tests/conftest.py
─────────────────
Stubs the heavy external deps (Mem0, Qdrant, Gemini) before any project
module imports them, so the test suite can run offline.

`travel_memory` is replaced with a MagicMock — assertions in tests verify
that the right methods got called with the right arguments.
"""

import sys
from unittest.mock import MagicMock

# ── Stub Mem0 + Qdrant so importing memory.mem0_manager doesn't try to
#    open a real local Qdrant collection or contact the Gemini API.
sys.modules.setdefault("mem0", MagicMock())

import memory.mem0_manager as mm  # noqa: E402

mm.travel_memory = MagicMock()
mm.travel_memory.read.return_value = ""
mm.travel_memory.check_resurrection.return_value = ""
mm.travel_memory.write.return_value = ["mem-id-1"]

# Re-export so tests that already imported the symbol see the mock too.
import agents.nodes as _nodes  # noqa: E402
_nodes.travel_memory = mm.travel_memory
