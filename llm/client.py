"""
Claude API client wrapper for generating worksheet content.

Uses the Anthropic Python SDK to send prompts to Claude and parse
structured JSON responses for UK Primary School worksheet generation.
"""

import os
import json
import re
import logging
from typing import Optional

from dotenv import load_dotenv
from anthropic import Anthropic, APIError, APITimeoutError, RateLimitError

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Default model - Claude Haiku for fast, cost-effective worksheet generation
DEFAULT_MODEL = "claude-haiku-4-5-20251001"

# Maximum tokens for worksheet content generation
DEFAULT_MAX_TOKENS = 4096

# Request timeout in seconds
DEFAULT_TIMEOUT = 60.0

# Stop reasons that mean Claude finished saying what it had to say. Anything
# else means the reply was cut short, and its content must not be used --
# see _reject_incomplete().
COMPLETE_STOP_REASONS = frozenset({"end_turn", "stop_sequence", "tool_use"})


class TruncatedResponseError(ValueError):
    """Claude stopped before finishing the response.

    A ValueError so that callers already catching ValueError cannot let a
    half-written worksheet through.
    """


def _reject_incomplete(stop_reason):
    """Refuse a reply Claude did not finish writing.

    Most truncations produce broken JSON and fail at the parser anyway. The
    reason this check has to exist separately is the case that does not: the
    model runs out of tokens at a point where the JSON is still well-formed.
    Then a six-question worksheet renders with three questions and nothing
    reports a problem. Valid JSON is not evidence of a complete answer.

    `None` is accepted: some SDK versions and test doubles do not set it, and
    failing on a missing value would block correct work.
    """
    if stop_reason is None or stop_reason in COMPLETE_STOP_REASONS:
        return
    raise TruncatedResponseError(
        f"Claude stopped early (stop_reason={stop_reason!r}), so the response is "
        f"incomplete and has not been used. If this is 'max_tokens', the content "
        f"asked for is too long for the token budget."
    )


def _get_client() -> Anthropic:
    """
    Create and return an Anthropic client instance.

    Raises:
        ValueError: If ANTHROPIC_API_KEY is not set in environment or .env file.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not found. Please set it in your .env file or "
            "environment variables. Example .env entry:\n"
            "ANTHROPIC_API_KEY=sk-ant-api03-..."
        )
    return Anthropic(api_key=api_key, timeout=DEFAULT_TIMEOUT)


def _extract_json_from_text(text: str) -> dict:
    """
    Extract and parse JSON from Claude's response text.

    Handles cases where Claude wraps JSON in markdown code blocks
    (```json ... ```) or returns raw JSON.

    Args:
        text: The raw text response from Claude.

    Returns:
        Parsed dictionary from the JSON content.

    Raises:
        json.JSONDecodeError: If no valid JSON can be extracted from the text.
    """
    # Strip leading/trailing whitespace
    text = text.strip()

    # Strategy 1: Try to extract JSON from markdown code blocks (```json ... ``` or ``` ... ```)
    code_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    matches = re.findall(code_block_pattern, text, re.DOTALL)
    if matches:
        # Try each match (use the first valid one)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

    # Strategy 2: Try to parse the entire text as JSON directly
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 3: Find the outermost JSON object by matching braces
    # Look for the first { and the last } in the text
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_candidate = text[first_brace : last_brace + 1]
        try:
            return json.loads(json_candidate)
        except json.JSONDecodeError:
            pass

    # Strategy 4: Try to find a JSON array if no object was found
    first_bracket = text.find("[")
    last_bracket = text.rfind("]")
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        json_candidate = text[first_bracket : last_bracket + 1]
        try:
            return json.loads(json_candidate)
        except json.JSONDecodeError:
            pass

    # All strategies failed
    raise json.JSONDecodeError(
        "Could not extract valid JSON from Claude's response. "
        f"Response started with: {text[:200]}...",
        text,
        0,
    )


def generate_structured_content(
    content,
    system_prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: Optional[float] = None,
) -> dict:
    """Send content to Claude and return the parsed JSON it replies with.

    The shared engine underneath both worksheet and planning generation. It was
    already generic -- only the name, the logging and the system prompt were
    worksheet-specific -- so this exposes it rather than duplicating the error
    handling, the truncation check and the JSON extraction a second time.

    Args:
        content: Either a prompt string, or a list of content blocks. The list
            form is what lets a planning request carry a PDF or a photograph of
            a scheme of work alongside its instructions; put the document and
            image blocks *before* the instruction text.
        system_prompt: The system prompt for this kind of request.

    Raises:
        TruncatedResponseError: Claude did not finish the response.
        json.JSONDecodeError: The reply was not usable JSON.
    """
    return _request_json(content, system_prompt, model, max_tokens, timeout)


def generate_worksheet_content(
    prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: Optional[float] = None,
    subject: str = "English",
) -> dict:
    """
    Send a prompt to Claude and return parsed JSON worksheet content.

    This function sends the given prompt to the Claude API, requesting
    structured JSON output suitable for worksheet generation. It handles
    response parsing, including extracting JSON from markdown code blocks.

    Args:
        prompt: The full prompt string to send to Claude. Should include
            instructions for JSON output format.
        model: The Claude model to use. Defaults to claude-haiku-4-5-20251001
            for fast, cost-effective generation.
        max_tokens: Maximum number of tokens in the response. Defaults to 4096.
        timeout: Optional request timeout in seconds. If None, uses the
            client default (60s).
        subject: The curriculum subject (e.g. "English", "Maths", "Science").
            Used to tailor the system prompt for better subject-specific output.

    Returns:
        A dictionary containing the parsed worksheet content matching the
        JSON schema specified in the prompt.

    Raises:
        ValueError: If the API key is not configured.
        anthropic.APIError: If the API returns an error (auth, server, etc.).
        anthropic.APITimeoutError: If the request times out.
        anthropic.RateLimitError: If the API rate limit is exceeded.
        json.JSONDecodeError: If the response cannot be parsed as JSON.
    """
    return _request_json(
        prompt,
        (
            f"You are an expert UK primary school teacher and curriculum designer "
            f"specialising in {subject}. "
            "You create engaging, age-appropriate educational content aligned to the "
            "UK National Curriculum. You ALWAYS respond with valid JSON only - no "
            "additional text, explanations, or markdown formatting outside the JSON. "
            "Your JSON output must be precise and match the exact schema requested."
        ),
        model,
        max_tokens,
        timeout,
    )


def _request_json(content, system_prompt, model, max_tokens, timeout):
    """One request, one parsed JSON reply.

    Every caller goes through here so the truncation check, the error logging
    and the JSON extraction exist in exactly one place.
    """
    client = _get_client()

    # Override timeout if specified
    if timeout is not None:
        client = Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            timeout=timeout,
        )

    logger.info("Sending request to Claude (model=%s)", model)

    try:
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": content}],
            system=system_prompt,
        )
    except APITimeoutError as e:
        logger.error("Claude API request timed out: %s", e)
        raise
    except RateLimitError as e:
        logger.error("Claude API rate limit exceeded: %s", e)
        raise
    except APIError as e:
        logger.error("Claude API error (status=%s): %s", getattr(e, "status_code", "unknown"), e)
        raise

    # Extract text content from the response
    if not message.content:
        raise ValueError("Claude returned an empty response with no content blocks.")

    response_text = ""
    for block in message.content:
        if block.type == "text":
            response_text += block.text

    if not response_text.strip():
        raise ValueError("Claude returned a response with no text content.")

    logger.debug(
        "Received response from Claude (%d chars, stop_reason=%s)",
        len(response_text),
        message.stop_reason,
    )

    # Checked before parsing: a truncated reply can still be valid JSON.
    _reject_incomplete(message.stop_reason)

    # Parse the JSON from the response
    try:
        result = _extract_json_from_text(response_text)
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse JSON from Claude's response. First 500 chars: %s",
            response_text[:500],
        )
        raise json.JSONDecodeError(
            f"Failed to parse worksheet JSON from Claude's response: {e.msg}",
            e.doc,
            e.pos,
        )

    logger.info("Parsed JSON from Claude (keys: %s)", list(result.keys()))

    return result
