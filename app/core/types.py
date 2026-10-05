"""
Shared type aliases for CARA.
Keeps type hints DRY and readable across all modules.
"""

from __future__ import annotations

from typing import Any

# JSON-serialisable dictionary
JsonDict = dict[str, Any]

# Provider identifier string (e.g. "groq", "gemini")
ProviderName = str

# Model variant string (e.g. "llama-3.1-8b-instant")
ModelName = str

# Score in [0.0, 1.0] range
Score = float

# Token count (always a non-negative integer)
TokenCount = int

# Cost in USD (can be 0.0 for free-tier models)
CostUSD = float
