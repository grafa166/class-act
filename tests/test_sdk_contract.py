"""
Guards the boundary between our code and the Anthropic SDK.

This file exists because of a real outage: the app called
``client.messages.create(..., temperature=0.7)``. ``requirements.txt`` pinned
``anthropic>=0.40.0`` with no upper bound, so a rebuild installed the 1.x SDK,
which had dropped ``temperature`` from the method signature. Every worksheet
generation then died with a ``TypeError`` raised *before* any network call --
and the app's error handler blamed the API key, sending the diagnosis in
entirely the wrong direction.

These tests need no API key, make no network calls, and cost nothing. They
compare what we pass against what the installed SDK actually accepts.
"""

import inspect

import pytest
from anthropic.resources.messages import Messages

import llm.client as client_module


def _create_signature_params():
    return set(inspect.signature(Messages.create).parameters)


def test_every_kwarg_we_send_exists_in_the_installed_sdk():
    """The exact failure that took the app down.

    We read the keyword arguments out of our own source rather than calling the
    API, so this stays free and offline while still catching signature drift the
    moment a new SDK is installed.
    """
    source = inspect.getsource(client_module.generate_worksheet_content)
    call_start = source.index("client.messages.create(")
    call_body = source[call_start:]

    sent_kwargs = set()
    depth = 0
    for line in call_body.splitlines():
        depth += line.count("(") - line.count(")")
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith(("#", '"', "'")):
            name = stripped.split("=", 1)[0].strip()
            if name.isidentifier():
                sent_kwargs.add(name)
        if depth <= 0 and "client.messages.create(" not in line:
            break

    accepted = _create_signature_params()
    unknown = sent_kwargs - accepted
    assert not unknown, (
        f"llm/client.py passes {sorted(unknown)} to messages.create(), but the "
        f"installed anthropic SDK ({_installed_version()}) does not accept them. "
        "The call will raise TypeError before reaching the API. Remove the "
        "argument or pin the SDK to a version that still supports it."
    )


def test_sampling_parameters_are_not_passed():
    """``temperature``/``top_p``/``top_k`` are removed on current Claude models.

    Even where an older model still accepts them, the 1.x SDK no longer exposes
    them on ``messages.create``. Passing one is a hard error, not a warning.
    """
    source = inspect.getsource(client_module.generate_worksheet_content)
    for banned in ("temperature=", "top_p=", "top_k="):
        assert banned not in source, (
            f"llm/client.py passes {banned.rstrip('=')} to the Anthropic API. "
            "This raises TypeError on anthropic>=1.0 and is rejected by current "
            "Claude models. Steer output through the prompt instead."
        )


def test_the_model_we_ask_for_is_a_plausible_id():
    """A retired or mistyped model ID returns 404 at request time.

    We cannot verify the model exists without a key, so we assert the shape --
    which catches typos and the date-suffix mistakes that cause most 404s.
    """
    model = client_module.DEFAULT_MODEL
    assert model.startswith("claude-"), f"Unexpected model ID: {model!r}"
    assert " " not in model, f"Model ID contains whitespace: {model!r}"


def test_client_construction_reports_a_missing_key_clearly():
    """A missing key must fail with our own message, not an opaque SDK error."""
    import os

    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            client_module._get_client()
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved


def _installed_version():
    import anthropic

    return getattr(anthropic, "__version__", "unknown")
