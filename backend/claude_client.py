"""
Thin wrapper around the Anthropic Claude API for the BRD generator.

Isolating the API call here means the Streamlit UI never has to know
about SDK details, and it makes the client easy to unit test or swap
(e.g. for a different model) without touching app.py.
"""

from typing import Any, Dict, Optional

import anthropic

from backend import config
from backend.brd_prompts import SYSTEM_PROMPT, build_user_prompt

# Defaults now come from environment variables (LLM_MODEL / LLM_EFFORT /
# LLM_MAX_TOKENS) via backend.config, with sensible fallbacks if unset.
# See README.md for how to set these locally or on Streamlit Cloud.
DEFAULT_MODEL = config.LLM_MODEL
DEFAULT_MAX_TOKENS = config.LLM_MAX_TOKENS
DEFAULT_EFFORT = config.LLM_EFFORT


class BRDGenerationError(Exception):
    """Raised when the Claude API call fails or returns no usable content."""


def generate_brd(
    inputs: Dict[str, Any],
    api_key: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = 0.3,
    effort: Optional[str] = None,
) -> str:
    """
    Call Claude to generate a full BRD in Markdown from structured form inputs.

    Args:
        inputs: dict of form field values (see backend.brd_prompts.build_user_prompt)
        api_key: Anthropic API key
        model: model ID to use
        max_tokens: max output tokens for the response
        temperature: sampling temperature (kept low for consistent, formal output)
        effort: "low" | "medium" | "high" | "xhigh" | "max". Only applied if the
            target model supports the `effort` parameter (see backend.config);
            silently ignored on older models like claude-opus-4-1-20250805.

    Returns:
        The generated BRD content as a Markdown string.

    Raises:
        BRDGenerationError: on API errors or empty responses.
    """
    if not api_key:
        raise BRDGenerationError(
            "No Anthropic API key provided. Add it in the sidebar or set "
            "ANTHROPIC_API_KEY as an environment variable / Streamlit secret."
        )

    client = anthropic.Anthropic(api_key=api_key)
    user_prompt = build_user_prompt(inputs)
    effort = effort or DEFAULT_EFFORT

    request_kwargs: Dict[str, Any] = dict(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    if config.model_supports_effort(model):
        request_kwargs["thinking"] = {"type": "adaptive"}
        request_kwargs["output_config"] = {"effort": effort}
        # Adaptive thinking counts thinking + response tokens against
        # max_tokens, so temperature is not accepted alongside it.
        request_kwargs.pop("temperature", None)

    try:
        response = client.messages.create(**request_kwargs)
    except anthropic.APIStatusError as exc:
        raise BRDGenerationError(f"Claude API error ({exc.status_code}): {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise BRDGenerationError(f"Could not reach the Claude API: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - surface any other SDK error clearly
        raise BRDGenerationError(f"Unexpected error calling Claude API: {exc}") from exc

    text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    result = "\n".join(text_blocks).strip()

    if not result:
        raise BRDGenerationError("Claude returned an empty response. Please try again.")

    return result


def refine_brd(
    existing_markdown: str,
    instruction: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    effort: Optional[str] = None,
) -> str:
    """
    Send an already-generated BRD back to Claude with a follow-up instruction
    (e.g. "make the scope section more detailed", "shorten the risks section").
    Returns the revised full BRD in Markdown.
    """
    if not api_key:
        raise BRDGenerationError("No Anthropic API key provided.")

    client = anthropic.Anthropic(api_key=api_key)
    effort = effort or DEFAULT_EFFORT

    refine_prompt = f"""Here is an existing Business Requirements Document in Markdown:

---
{existing_markdown}
---

Apply this revision instruction, then return the FULL revised document in the same \
Markdown structure (all sections, not just the changed one). Output only the document:

Instruction: {instruction}
"""

    request_kwargs: Dict[str, Any] = dict(
        model=model,
        max_tokens=max_tokens,
        temperature=0.3,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": refine_prompt}],
    )

    if config.model_supports_effort(model):
        request_kwargs["thinking"] = {"type": "adaptive"}
        request_kwargs["output_config"] = {"effort": effort}
        request_kwargs.pop("temperature", None)

    try:
        response = client.messages.create(**request_kwargs)
    except Exception as exc:  # noqa: BLE001
        raise BRDGenerationError(f"Unexpected error calling Claude API: {exc}") from exc

    text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    result = "\n".join(text_blocks).strip()

    if not result:
        raise BRDGenerationError("Claude returned an empty response during refinement.")

    return result
