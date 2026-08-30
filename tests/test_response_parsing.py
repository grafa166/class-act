"""
Covers the layer between Claude's raw reply and the document generators.

The rest of the suite hands the generators a ready-made dictionary. In
production nothing does that: Claude returns *text*, and
``_extract_json_from_text`` has to turn it into that dictionary. If it fails,
every worksheet fails -- and no other test in this repo would notice.

So these tests take the real fixtures, serialise them the way Claude actually
replies (usually fenced in markdown, sometimes with a sentence in front), pull
them back out, and build a real .docx from the result. That is the whole
pipeline apart from the network call.
"""

import json

import docx
import pytest

from llm.client import _extract_json_from_text
from tests.fixtures import ALL_CONTENT
from tests.test_smoke import GENERATORS, _document_text

WORKSHEET_TYPES = sorted(ALL_CONTENT)


# --------------------------------------------------------------------------
# The reply shapes Claude actually produces.
# --------------------------------------------------------------------------


def _as_json(content):
    return json.dumps(content, ensure_ascii=False)


@pytest.mark.parametrize("ws_type", WORKSHEET_TYPES)
def test_fenced_json_is_recovered(ws_type):
    """The common case: Claude wraps its JSON in a ```json block."""
    payload = _as_json(ALL_CONTENT[ws_type])
    reply = f"```json\n{payload}\n```"
    assert _extract_json_from_text(reply) == ALL_CONTENT[ws_type]


@pytest.mark.parametrize("ws_type", WORKSHEET_TYPES)
def test_bare_fenced_json_is_recovered(ws_type):
    """Sometimes the fence has no language tag."""
    payload = _as_json(ALL_CONTENT[ws_type])
    reply = f"```\n{payload}\n```"
    assert _extract_json_from_text(reply) == ALL_CONTENT[ws_type]


@pytest.mark.parametrize("ws_type", WORKSHEET_TYPES)
def test_unfenced_json_is_recovered(ws_type):
    """The system prompt asks for raw JSON, so this is the intended shape."""
    payload = _as_json(ALL_CONTENT[ws_type])
    assert _extract_json_from_text(payload) == ALL_CONTENT[ws_type]


def test_json_with_a_preamble_is_recovered():
    """Models sometimes add a sentence despite being told not to."""
    payload = _as_json(ALL_CONTENT["cloze"])
    reply = f"Here is the worksheet you asked for:\n\n```json\n{payload}\n```"
    assert _extract_json_from_text(reply) == ALL_CONTENT["cloze"]


def test_json_with_trailing_commentary_is_recovered():
    payload = _as_json(ALL_CONTENT["matching"])
    reply = f"```json\n{payload}\n```\n\nLet me know if you'd like it harder."
    assert _extract_json_from_text(reply) == ALL_CONTENT["matching"]


def test_unparseable_reply_fails_loudly():
    """A failure here must raise, not return half a worksheet."""
    with pytest.raises(json.JSONDecodeError):
        _extract_json_from_text("I'm sorry, I can't help with that request.")


def test_empty_reply_fails_loudly():
    with pytest.raises(json.JSONDecodeError):
        _extract_json_from_text("")


# --------------------------------------------------------------------------
# Characters that appear in real primary-school worksheets.
# --------------------------------------------------------------------------


def test_apostrophes_and_accents_survive_the_round_trip():
    """UK worksheets are full of apostrophes; a mangled one is visible to a child."""
    content = {
        "title": "The Baker's Dozen — a Café Story",
        "activities": [
            {
                "title": "Match the Words",
                "instructions": 'Draw a line. Don\'t rush — check each one.',
                "pairs": [
                    {"left": "café", "right": "a place that sells coffee"},
                    {"left": "don't", "right": "short for 'do not'"},
                    {"left": "naïve", "right": "innocent or inexperienced"},
                    {"left": "“quotation”", "right": "words someone said"},
                ],
            }
        ],
        "bonus_activity": {"title": "Challenge", "instructions": "Write a sentence.", "lines": 2},
        "success_criteria": ["I can use an apostrophe correctly."],
    }

    recovered = _extract_json_from_text(f"```json\n{_as_json(content)}\n```")
    assert recovered == content

    buffer = GENERATORS["matching"](
        content=recovered,
        theme_key="classic",
        level="expected",
        objective="",
        extra_spacing=False,
        eal_glossary=False,
        show_answers=False,
    )
    text = _document_text(buffer)
    for expected in ("Baker's Dozen", "café", "don't", "naïve"):
        assert expected in text, f"{expected!r} was lost or mangled in the document"


def test_escaped_newlines_become_real_paragraph_breaks():
    """Reading passages use \\n\\n for paragraph breaks -- they must survive."""
    reply = json.dumps(ALL_CONTENT["reading_comprehension"], ensure_ascii=False)
    recovered = _extract_json_from_text(f"```json\n{reply}\n```")
    assert "\n\n" in recovered["passage"]["text"]


# --------------------------------------------------------------------------
# The whole chain: Claude's reply -> parsed -> Word document.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("ws_type", WORKSHEET_TYPES)
@pytest.mark.parametrize("show_answers", [False, True])
def test_full_pipeline_from_a_realistic_reply_to_a_document(ws_type, show_answers):
    """End to end, exactly as production runs it apart from the network call."""
    claude_reply = f"```json\n{_as_json(ALL_CONTENT[ws_type])}\n```"

    content = _extract_json_from_text(claude_reply)

    buffer = GENERATORS[ws_type](
        content=content,
        theme_key="jungle",
        level="expected",
        objective="Pupils can apply what they have learned this week.",
        extra_spacing=False,
        eal_glossary=False,
        show_answers=show_answers,
    )

    buffer.seek(0)
    document = docx.Document(buffer)  # raises if the file is not a valid .docx
    assert len(document.paragraphs) > 3, f"{ws_type} produced a suspiciously empty document"
    assert ALL_CONTENT[ws_type]["title"] in _document_text(buffer)
