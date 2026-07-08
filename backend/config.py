"""
Central place for environment-driven Claude configuration.

Reads LLM_MODEL / LLM_EFFORT / LLM_MAX_TOKENS from the environment (or a
.env file / Streamlit secrets) so the model can be swapped without touching
code. See README.md for the full list of supported variables.
"""

import os

LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-5")
LLM_EFFORT = os.environ.get("LLM_EFFORT", "high")
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "8000"))

# Models that accept the `effort` parameter (adaptive-thinking generation:
# Opus 4.6+, Sonnet 4.6+, Fable 5, Mythos 5). Older pinned/dated models --
# e.g. claude-opus-4-1-20250805, claude-opus-4-5-20251101 -- pre-date this
# and only support the legacy `thinking: {type: "enabled", budget_tokens}`
# form (or no thinking at all). Sending `effort` to one of those returns a
# 400 error, so we detect support before adding it to the request.
_EFFORT_SUPPORTED_PREFIXES = (
    "claude-opus-4-6",
    "claude-opus-4-7",
    "claude-opus-4-8",
    "claude-sonnet-4-6",
    "claude-sonnet-5",
    "claude-fable-5",
    "claude-mythos-5",
)


def model_supports_effort(model: str) -> bool:
    """True if `model` accepts thinking:{type:"adaptive"} + output_config.effort."""
    return model.startswith(_EFFORT_SUPPORTED_PREFIXES)
