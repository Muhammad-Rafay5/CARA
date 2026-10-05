"""
Shared constants for CARA.
Centralised place for magic numbers and string literals used across modules.
"""

from __future__ import annotations

# ── Model Tiers ──────────────────────────────────────────────────────────────
TIER_FAST = "fast"           # e.g. llama-3.1-8b-instant, gemini-2.0-flash
TIER_STANDARD = "standard"   # e.g. llama-3.3-70b, gemini-1.5-flash
TIER_ADVANCED = "advanced"   # e.g. gemini-1.5-pro, openrouter advanced

# ── Provider Names ────────────────────────────────────────────────────────────
PROVIDER_GROQ = "groq"
PROVIDER_GEMINI = "gemini"
PROVIDER_OPENROUTER = "openrouter"
PROVIDER_OLLAMA = "ollama"

# ── Circuit Breaker ───────────────────────────────────────────────────────────
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 3       # consecutive failures before OPEN
CIRCUIT_BREAKER_COOLDOWN_SECONDS = 60       # time OPEN before HALF-OPEN probe
CIRCUIT_BREAKER_SUCCESS_THRESHOLD = 1       # successes needed to close circuit
CIRCUIT_BREAKER_HALF_OPEN_CALLS = 1         # allowed calls in HALF-OPEN probe

# ── Retry Policy ──────────────────────────────────────────────────────────────
RETRY_BASE_DELAY_SECONDS = 1.0
RETRY_MAX_DELAY_SECONDS = 30.0
RETRY_BACKOFF_FACTOR = 2.0

# ── HTTP / Tool Defaults ──────────────────────────────────────────────────────
DEFAULT_HTTP_TIMEOUT_SECONDS = 15
DEFAULT_MAX_RESPONSE_BYTES = 1_048_576      # 1 MB

# ── SSRF Blocklist ────────────────────────────────────────────────────────────
SSRF_BLOCKED_PREFIXES = (
    "http://localhost",
    "https://localhost",
    "http://127.",
    "https://127.",
    "http://10.",
    "https://10.",
    "http://192.168.",
    "https://192.168.",
    "http://169.254.",   # AWS metadata / link-local
    "https://169.254.",
    "http://172.16.",
    "https://172.16.",
    "http://[::1]",      # IPv6 loopback
    "https://[::1]",
)

# ── Token / Cost ──────────────────────────────────────────────────────────────
TOKENS_PER_CHAR_ESTIMATE = 0.25   # rough estimate: 1 token ≈ 4 characters

# ── Research ──────────────────────────────────────────────────────────────────
MIN_EVIDENCE_FOR_SIMPLE = 2
MIN_EVIDENCE_FOR_MEDIUM = 4
MIN_EVIDENCE_FOR_COMPLEX = 6
VERIFICATION_PASS_THRESHOLD = 0.75   # minimum score to consider research complete
