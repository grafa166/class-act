"""
Tests the shape check that sits between Claude and the document builders.

The most valuable test here is the last one: it re-derives the required-keys
map from the generator source on every run, so ``llm/validation.py`` cannot
quietly fall out of step with the code it is protecting.
"""

import pathlib
import re

import pytest

from llm.validation import (
    REQUIRED_KEYS,
    WorksheetContentError,
    validate_worksheet_content,
)
from tests.fixtures import ALL_CONTENT

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# generators/<name>.py holds the builder for worksheet type <name>.
GENERATOR_SOURCES = {name: REPO_ROOT / "generators" / f"{name}.py" for name in REQUIRED_KEYS}


@pytest.mark.parametrize("ws_type", sorted(ALL_CONTENT))
def test_every_fixture_passes_validation(ws_type):
    """Our own test content must satisfy the rules we enforce in production."""
    assert validate_worksheet_content(ws_type, ALL_CONTENT[ws_type]) is ALL_CONTENT[ws_type]


@pytest.mark.parametrize("ws_type", sorted(REQUIRED_KEYS))
def test_each_required_key_is_actually_required(ws_type):
    """Removing any required key must be caught, and the message must name it."""
    for key in REQUIRED_KEYS[ws_type]:
        if ws_type not in ALL_CONTENT:
            continue
        broken = {k: v for k, v in ALL_CONTENT[ws_type].items() if k != key}
        with pytest.raises(WorksheetContentError) as excinfo:
            validate_worksheet_content(ws_type, broken)
        assert key in str(excinfo.value), (
            f"Dropping {key!r} from {ws_type} was rejected, but the message did "
            f"not say which field was missing: {excinfo.value}"
        )


def test_non_dict_is_rejected():
    for rubbish in ([], "a string", 42, None):
        with pytest.raises(WorksheetContentError):
            validate_worksheet_content("cloze", rubbish)


def test_empty_section_is_rejected():
    broken = dict(ALL_CONTENT["cloze"], sections=[])
    with pytest.raises(WorksheetContentError, match="empty"):
        validate_worksheet_content("cloze", broken)


def test_blank_title_is_rejected():
    broken = dict(ALL_CONTENT["matching"], title="   ")
    with pytest.raises(WorksheetContentError, match="title"):
        validate_worksheet_content("matching", broken)


def test_unknown_worksheet_type_is_allowed_through():
    """A missing map entry is our bug, and must not block a teacher's worksheet."""
    content = {"title": "Something"}
    assert validate_worksheet_content("not_a_real_type", content) is content


def test_required_keys_match_what_the_generators_actually_demand():
    """The anti-drift test.

    Each generator accesses some fields as ``content['key']``, which raises if
    the key is absent. Those are exactly the fields validation must require. We
    read them back out of the source so this map cannot rot as the generators
    change.
    """
    pattern = re.compile(r"content\['([a-z_]+)'\]")

    for ws_type, source_path in GENERATOR_SOURCES.items():
        assert source_path.exists(), f"No generator source at {source_path}"
        hard_required = set(pattern.findall(source_path.read_text()))
        declared = set(REQUIRED_KEYS[ws_type])

        unprotected = hard_required - declared
        assert not unprotected, (
            f"generators/{ws_type}.py reads content{sorted(unprotected)} with "
            "square brackets, so a missing one raises KeyError, but "
            "llm/validation.py does not require it. Add it to REQUIRED_KEYS."
        )

        overreach = declared - hard_required
        assert not overreach, (
            f"llm/validation.py requires {sorted(overreach)} for {ws_type}, but "
            f"generators/{ws_type}.py never demands it. This rejects worksheets "
            "that would have built fine — remove it from REQUIRED_KEYS."
        )
