"""Refusing a reply that Claude stopped writing half way through.

`stop_reason` was logged and then ignored, so the response was parsed whatever
it said. Most truncations break the JSON and fail loudly at the parser, which
is why this went unnoticed.

The case that does not fail loudly is the one that matters: Claude runs out of
tokens at a point where the JSON happens to still be well-formed. Then a
worksheet renders with three questions instead of six, or a six-lesson unit
comes back with four lessons, and nothing anywhere says so. The teacher finds
out in front of the class.
"""

import json

import pytest

import llm.client as client_module
from llm.client import TruncatedResponseError, generate_worksheet_content

COMPLETE = {
    "title": "Which rock for the job?",
    "questions": ["one", "two", "three", "four", "five", "six"],
}

# Well-formed JSON. Also missing half its questions.
TRUNCATED_BUT_VALID = {
    "title": "Which rock for the job?",
    "questions": ["one", "two", "three"],
}


class _Block:
    type = "text"

    def __init__(self, text):
        self.text = text


class _Message:
    def __init__(self, payload, stop_reason):
        self.content = [_Block(json.dumps(payload))]
        self.stop_reason = stop_reason


class _Messages:
    def __init__(self, message):
        self._message = message

    def create(self, **_kwargs):
        return self._message


class _FakeClient:
    def __init__(self, payload, stop_reason):
        self.messages = _Messages(_Message(payload, stop_reason))


@pytest.fixture
def claude(monkeypatch):
    def _install(payload, stop_reason):
        monkeypatch.setattr(
            client_module, "_get_client", lambda: _FakeClient(payload, stop_reason)
        )

    return _install


def test_a_complete_response_is_returned(claude):
    claude(COMPLETE, "end_turn")
    assert generate_worksheet_content("prompt") == COMPLETE


def test_a_tool_use_stop_is_accepted(claude):
    """Not used today, but it is a legitimate, complete ending."""
    claude(COMPLETE, "tool_use")
    assert generate_worksheet_content("prompt") == COMPLETE


def test_a_missing_stop_reason_is_accepted(claude):
    """Older SDKs and some fakes leave it unset; do not fail on that alone."""
    claude(COMPLETE, None)
    assert generate_worksheet_content("prompt") == COMPLETE


def test_truncation_is_rejected_even_when_the_json_parses(claude):
    """The whole point. Valid JSON is not evidence of a complete answer."""
    claude(TRUNCATED_BUT_VALID, "max_tokens")
    with pytest.raises(TruncatedResponseError):
        generate_worksheet_content("prompt")


def test_the_error_names_the_cause(claude):
    claude(TRUNCATED_BUT_VALID, "max_tokens")
    with pytest.raises(TruncatedResponseError, match="max_tokens"):
        generate_worksheet_content("prompt")


def test_a_refusal_is_rejected(claude):
    claude(COMPLETE, "refusal")
    with pytest.raises(TruncatedResponseError):
        generate_worksheet_content("prompt")


def test_truncation_error_is_catchable_as_valueerror(claude):
    """Existing callers catch ValueError; this must not slip past them."""
    claude(TRUNCATED_BUT_VALID, "max_tokens")
    with pytest.raises(ValueError):
        generate_worksheet_content("prompt")
