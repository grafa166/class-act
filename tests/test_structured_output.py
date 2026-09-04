"""Constraining the reply to a schema instead of hoping it comes back valid.

Measured across seven live runs of the whole flow: a unit lost about one lesson
in three, and several of those losses were the model returning JSON that does
not parse — a stray `or` between two strings, a missing comma between two
fields, seen at 20–25k characters. It is not truncation. `stop_reason` is
clean, the truncation guard passes, and the reply is simply invalid.

Anthropic's documented answer is structured outputs: send the schema with the
request and the reply is constrained to it as it is generated, rather than
asked for in prose and checked afterwards. A retry loop is the wrong first
move here for the same reason a longer timeout was the wrong first move for the
dropped connection — it treats a documented mechanism as bad luck.

Two things are load-bearing in this file:

- **The streaming path carries the schema too.** A lesson is streamed, and a
  schema that only reached the non-streaming call would be a silent no-op on
  the exact request that needed it.
- **A request that asks for no schema gets none.** The worksheet path has been
  verified live seven times and is not being changed underneath.

None of these tests touch the network.
"""

import inspect
import json

import pytest

import llm.client as client_module
from llm.client import generate_structured_content, generate_worksheet_content

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title"],
    "properties": {"title": {"type": "string"}},
}

PAYLOAD = {"title": "Which rock for the job?"}


class _Block:
    type = "text"

    def __init__(self, text):
        self.text = text


class _Message:
    def __init__(self, payload):
        self.content = [_Block(json.dumps(payload))]
        self.stop_reason = "end_turn"


class _Stream:
    """What `client.messages.stream(...)` hands back: a context manager whose
    `get_final_message()` returns the same assembled message a plain request
    would have returned."""

    def __init__(self, message):
        self._message = message

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def get_final_message(self):
        return self._message


class _Messages:
    def __init__(self, message, calls):
        self._message = message
        self.calls = calls

    def create(self, **kwargs):
        self.calls.append(("create", kwargs))
        return self._message

    def stream(self, **kwargs):
        self.calls.append(("stream", kwargs))
        return _Stream(self._message)


class _FakeClient:
    def __init__(self, payload, calls):
        self.messages = _Messages(_Message(payload), calls)


@pytest.fixture
def calls(monkeypatch):
    recorded = []
    monkeypatch.setattr(
        client_module, "_get_client", lambda: _FakeClient(PAYLOAD, recorded)
    )
    return recorded


def _sent(calls):
    assert calls, "No request reached the SDK at all."
    return calls[0]


class TestASchemaReachesTheRequest:
    def test_a_schema_is_sent_as_the_output_format(self, calls):
        generate_structured_content("prompt", "system", schema=SCHEMA)
        _, kwargs = _sent(calls)
        assert kwargs.get("output_config") == {
            "format": {"type": "json_schema", "schema": SCHEMA}
        }

    def test_a_streamed_request_carries_the_schema_too(self, calls):
        """The one that matters. A lesson streams; a worksheet does not. A
        schema wired only into the non-streaming call would look correct in
        every test above and do nothing at all on the request that loses a
        lesson in three."""
        generate_structured_content("prompt", "system", schema=SCHEMA, stream=True)
        verb, kwargs = _sent(calls)
        assert verb == "stream"
        assert kwargs.get("output_config") == {
            "format": {"type": "json_schema", "schema": SCHEMA}
        }

    def test_the_constrained_reply_is_still_parsed_and_returned(self, calls):
        assert generate_structured_content("prompt", "system", schema=SCHEMA) == PAYLOAD


class TestNothingElseChanges:
    def test_a_request_without_a_schema_carries_no_format(self, calls):
        generate_structured_content("prompt", "system")
        _, kwargs = _sent(calls)
        assert not isinstance(kwargs.get("output_config"), dict), (
            "A request that asked for no schema had one attached anyway."
        )

    def test_the_worksheet_path_is_left_unconstrained(self, calls):
        """Verified live seven times as it stands. It is not being changed
        underneath as a side effect of fixing the lesson step."""
        generate_worksheet_content("prompt")
        _, kwargs = _sent(calls)
        assert not isinstance(kwargs.get("output_config"), dict)

    def test_a_request_without_a_schema_still_returns_its_json(self, calls):
        assert generate_structured_content("prompt", "system") == PAYLOAD


class TestTheInstalledSdkAcceptsThis:
    """The same guard as `test_sdk_contract.py`, for the parameter being added.

    `requirements.txt` allows any `anthropic` 1.x. A parameter the installed
    SDK does not accept raises `TypeError` before any network call, and the
    app's error handler blames the API key.
    """

    @pytest.mark.parametrize("method", ["create", "stream"])
    def test_output_config_exists_on_both_request_paths(self, method):
        from anthropic.resources.messages import Messages

        parameters = inspect.signature(getattr(Messages, method)).parameters
        assert "output_config" in parameters, (
            f"The installed anthropic SDK does not accept output_config on "
            f"messages.{method}(). Structured outputs cannot be sent this way; "
            f"pin the SDK to a version that supports it."
        )
