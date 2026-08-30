"""
Checks Claude's reply has the fields the document builders need.

Claude returns valid JSON reliably, but not always JSON of the *right shape* --
a missing ``sections`` key parses fine and then raises ``KeyError: 'sections'``
deep inside a generator, which reaches the teacher as an incomprehensible
error. This turns that into a clear message and a retry.

The required keys below are the ones the generators access with square
brackets, which raise if absent. ``tests/test_validation.py`` re-derives them
from the generator source on every run, so this list cannot drift out of step
with the code.
"""

from typing import Any, Dict, Sequence


class WorksheetContentError(ValueError):
    """Claude's reply was valid JSON but missing something we need."""


# Keys each generator accesses with content['key'] -- absence is fatal.
REQUIRED_KEYS: Dict[str, Sequence[str]] = {
    "cloze": ("title", "sections", "word_bank", "success_criteria"),
    "word_bank": ("title", "categories", "activities", "success_criteria"),
    "matching": ("title", "activities", "success_criteria"),
    "sentence_builder": ("title", "exercises", "success_criteria"),
    "reading_comprehension": ("title", "passage", "questions", "success_criteria"),
    "problem_solving": ("title", "questions", "success_criteria"),
    "calculation_practice": ("title", "sections", "success_criteria"),
    "fraction_practice": ("title",),
    "times_tables": ("title",),
    "investigation": ("title",),
}


def validate_worksheet_content(worksheet_type: str, content: Any) -> Dict:
    """Return the content unchanged, or raise with a message worth reading.

    Args:
        worksheet_type: Key from REQUIRED_KEYS, e.g. "cloze".
        content: Whatever came back from the model.

    Raises:
        WorksheetContentError: If the content cannot drive a generator.
    """
    if not isinstance(content, dict):
        raise WorksheetContentError(
            f"Expected a set of worksheet fields but got {type(content).__name__}. "
            "The AI returned something unexpected -- try generating again."
        )

    required = REQUIRED_KEYS.get(worksheet_type)
    if required is None:
        # An unknown type is a programming error, not bad model output. Let it
        # through rather than blocking a worksheet over a missing map entry.
        return content

    missing = [key for key in required if key not in content]
    if missing:
        raise WorksheetContentError(
            f"The AI's response was missing: {', '.join(missing)}. "
            "This is usually a one-off -- try generating again."
        )

    empty = [key for key in required if key != "title" and not content[key]]
    if empty:
        raise WorksheetContentError(
            f"The AI returned an empty {', '.join(empty)} section. "
            "Try generating again."
        )

    if not str(content.get("title", "")).strip():
        raise WorksheetContentError(
            "The AI did not give the worksheet a title. Try generating again."
        )

    return content
