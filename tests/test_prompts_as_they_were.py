"""The ten prompts, byte for byte, as they were the day this guard was written.

🚨 **The guard this repo thought it already had.** `tests/test_source_prompts.py:54-67`
compares two *live* calls — `get_prompt(**COMMON)` against the same call with
`source_material=None` — so it proves only that passing `None` is a no-op. It says
nothing about whether the templates themselves still read as they did. Measured
2026-10-02: edit a `DIFFERENTIATION LEVEL RULES` block in any of the ten templates and
the entire suite stays green.

That matters because every feature added to this file since has been built on one
promise — *"no template constant is edited"* — and the promise was kept by code review
alone. Three separate pieces of work now lean on it: the source overrides that ship
today, and the task, barrier and curriculum blocks planned next. A promise nothing
checks is not a property, it is a habit.

So: one stored file per worksheet type, compared literally.

⚠️ **This passes the day it is written, like `TestRegenerateReplaysEveryInput` in
`tests/test_source_panel.py`. Its RED step is the mutation**
`a differentiation rule is reworded in one template`, which caught nothing before this
file existed.

**When this test fails and the change was deliberate**, read the diff it prints, satisfy
yourself the wording really is meant to move, then regenerate:

    .venv/bin/python tests/test_prompts_as_they_were.py --rewrite

Regenerating without reading the diff defeats the whole file.
"""

import difflib
import pathlib
import sys

import pytest

from llm.prompts import get_prompt, list_worksheet_types

AS_THEY_WERE = pathlib.Path(__file__).resolve().parent / "prompts_as_they_were"

# The same eight arguments `tests/test_source_prompts.py` uses, deliberately: one set of
# inputs across both files means a snapshot and a live assertion can never be comparing
# two different prompts and both be right.
COMMON = dict(
    year_group="Year 3",
    topic="A story opening",
    objective="retrieve and record information from a text",
    age_range="7-8",
    theme_name="Space Explorer",
    theme_icon="\U0001F680",
    level="expected",
    subject="English",
)


def _as_it_is_now(worksheet_type):
    return get_prompt(worksheet_type=worksheet_type, **COMMON)


def _stored(worksheet_type):
    return AS_THEY_WERE / f"{worksheet_type}.txt"


class TestEveryPromptIsTheStringItWas:
    @pytest.mark.parametrize("worksheet_type", list_worksheet_types())
    def test_the_prompt_has_not_changed(self, worksheet_type):
        stored = _stored(worksheet_type)
        assert stored.exists(), (
            f"no stored prompt for {worksheet_type}. If the type is new, run "
            f"`.venv/bin/python tests/test_prompts_as_they_were.py --rewrite` and read "
            f"what it writes before committing it."
        )
        was = stored.read_text(encoding="utf-8")
        now = _as_it_is_now(worksheet_type)
        if was != now:
            diff = "\n".join(
                difflib.unified_diff(
                    was.splitlines(),
                    now.splitlines(),
                    fromfile=f"{worksheet_type} (as it was)",
                    tofile=f"{worksheet_type} (now)",
                    lineterm="",
                )
            )
            pytest.fail(
                f"the {worksheet_type} prompt has changed. If that was deliberate, read "
                f"this diff, then regenerate the stored copy:\n\n{diff}"
            )


class TestTheStoredPromptsAreWorthComparingAgainst:
    """⚠️ Controls. A stored file that is empty, truncated or missing its
    differentiation rules would pass the comparison above and guard nothing — which is
    the empty-haystack-reports-green failure this project keeps finding."""

    def test_there_is_one_stored_prompt_per_worksheet_type(self):
        stored = {path.stem for path in AS_THEY_WERE.glob("*.txt")}
        assert stored == set(list_worksheet_types()), (
            "the stored prompts and the worksheet types have drifted apart: "
            f"only stored {sorted(stored - set(list_worksheet_types()))}, "
            f"only a type {sorted(set(list_worksheet_types()) - stored)}"
        )

    @pytest.mark.parametrize("worksheet_type", list_worksheet_types())
    def test_each_stored_prompt_carries_the_rules_it_exists_to_protect(
        self, worksheet_type
    ):
        """The differentiation block is the thing most likely to be edited and the thing
        a new input is most likely to flatten, so a snapshot without it is not
        protecting the part that matters."""
        was = _stored(worksheet_type).read_text(encoding="utf-8")
        assert "DIFFERENTIATION LEVEL RULES" in was, (
            f"the stored {worksheet_type} prompt has no differentiation rules in it"
        )
        assert len(was) > 2_000, (
            f"the stored {worksheet_type} prompt is {len(was)} characters, which is too "
            f"short to be a whole prompt — it was probably truncated when written"
        )

    @pytest.mark.parametrize("worksheet_type", list_worksheet_types())
    def test_a_stored_prompt_describes_all_three_levels(self, worksheet_type):
        """One snapshot per type is only enough because each template carries the rules
        for all three levels as static text — measured: a prompt rendered at
        `level="expected"` still contains the developing and greater-depth rules in
        full. If that ever stops being true, one level's rules could be edited without
        any snapshot noticing.

        ⚠️ The level names are read from `DIFF_LEVELS`, not written out here. The first
        version of this control asserted `"GREATER DEPTH"` and failed on all ten types,
        because the templates spell them as the keys do — `greater_depth`. A control
        that carries its own copy of a name is a control that can be wrong about it.
        """
        from generators.styles import DIFF_LEVELS

        was = _stored(worksheet_type).read_text(encoding="utf-8")
        for level in DIFF_LEVELS:
            assert level in was, (
                f"the stored {worksheet_type} prompt does not mention {level!r}, so a "
                f"change to that level's rules would not be caught here"
            )


def _rewrite():
    """Write the stored copies from the code as it stands. Read the diff first."""
    AS_THEY_WERE.mkdir(exist_ok=True)
    for worksheet_type in list_worksheet_types():
        _stored(worksheet_type).write_text(
            _as_it_is_now(worksheet_type), encoding="utf-8"
        )
        print(f"wrote {_stored(worksheet_type).name}")


if __name__ == "__main__":
    if "--rewrite" not in sys.argv:
        raise SystemExit(
            "This file is a test. To regenerate the stored prompts deliberately:\n"
            "    .venv/bin/python tests/test_prompts_as_they_were.py --rewrite"
        )
    _rewrite()
