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

import ast
import inspect
import pathlib
import textwrap

import pytest
from anthropic.resources.messages import Messages

import llm.client as client_module


def _create_signature_params():
    return set(inspect.signature(Messages.create).parameters)


def _find_create_call():
    """Locate the ``client.messages.create(...)`` call node in llm/client.py.

    Parsed with ``ast`` rather than scanned line by line. An earlier version of
    this test split each physical line on its first ``=``, which silently missed
    a second keyword sharing a line (``model=model, temperature=0.7``) and every
    ``**kwargs`` form -- so the guard passed on code that crashes on every run.
    """
    source = pathlib.Path(client_module.__file__).read_text()
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "create"
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == "messages"
        ):
            return node
    raise AssertionError(
        "No client.messages.create(...) call found in llm/client.py. Either the "
        "call was renamed or this test needs updating -- do not delete it."
    )


def test_every_kwarg_we_send_exists_in_the_installed_sdk():
    """The exact failure that took the app down, generalised to any parameter.

    Reads the call out of our own source rather than hitting the API, so this
    stays free and offline while still catching signature drift the moment a new
    SDK is installed.
    """
    call = _find_create_call()

    starred = [kw for kw in call.keywords if kw.arg is None]
    assert not starred, (
        "llm/client.py passes **kwargs to messages.create(). This test cannot "
        "see what is inside, so SDK drift would go undetected. Pass keyword "
        "arguments explicitly."
    )

    sent_kwargs = {kw.arg for kw in call.keywords}
    accepted = _create_signature_params()
    unknown = sent_kwargs - accepted

    assert not unknown, (
        f"llm/client.py passes {sorted(unknown)} to messages.create(), but the "
        f"installed anthropic SDK ({_installed_version()}) does not accept them. "
        "The call will raise TypeError before reaching the API. Remove the "
        "argument, or pin the SDK to a version that still supports it."
    )


def test_our_arguments_actually_bind_to_the_sdk_signature():
    """Stronger than a name check: prove Python could really make this call.

    Catches arity and positional-argument problems a set comparison misses.
    """
    call = _find_create_call()
    sent_kwargs = {kw.arg for kw in call.keywords if kw.arg}

    signature = inspect.signature(Messages.create)
    try:
        signature.bind_partial(**{name: None for name in sent_kwargs})
    except TypeError as exc:
        pytest.fail(
            f"The arguments llm/client.py sends do not bind to "
            f"messages.create() in anthropic {_installed_version()}: {exc}"
        )


def test_the_guard_itself_catches_a_bad_argument():
    """A positive control for this file.

    A guard nobody has seen fail is not a guard. This proves the AST walk
    detects a bad keyword in the shapes the old line-based parser missed --
    including two keywords sharing one line.
    """
    accepted = _create_signature_params()

    for snippet in (
        "client.messages.create(model=m, temperature=0.7)",
        "client.messages.create(model=m, temperature=0.7, max_tokens=1)",
        textwrap.dedent(
            """
            client.messages.create(
                model=m, temperature=0.7,
                max_tokens=1,
            )
            """
        ),
    ):
        tree = ast.parse(snippet)
        call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call))
        sent = {kw.arg for kw in call.keywords}
        assert "temperature" in sent, f"AST walk missed temperature in: {snippet!r}"
        assert sent - accepted, (
            f"The guard would not have flagged this call: {snippet!r}"
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
