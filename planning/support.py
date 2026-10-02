"""What is getting in the way, and what the sheet does about it.

Her words, 2026-10-02 (relayed by Graeme): *"so the site removes the actual
barrier rather than just making the work easier."*

⚠️ **The question is about the work, never the child.** She asked *"what does
this pupil need help with?"* -- and the word *pupil* invites a name into a box
that is sent to Anthropic. `pages/2_Lesson_Plans.py` already records that a
free-text need box *"predictably attracts pupil names, and 'we did not ask for
them' is not a control."* So: seven tick-boxes and no free text. What leaves
the building is one of 128 fixed strings, which is a privacy claim that is true
and checkable rather than hoped for.

⚠️ **Held as a dict.** The keys decide what happens to the sheet; the labels
are hers to reword. Rewording a label must never change what gets printed.
"""

import copy
import dataclasses
import math

# Her list, in her order, in her words.
BARRIERS = {
    "decoding": "Decoding the words",
    "limited_english": "Vocabulary or limited English",
    "comprehension": "Understanding what they read",
    "forming_sentences": "Forming a sentence",
    "writing_length": "Writing a lot",
    "remembering_instructions": "Remembering the instructions",
    "working_independently": "Working without an adult",
}


# --------------------------------------------------------------------------
# What each barrier can do on each kind of sheet
# --------------------------------------------------------------------------

PRINTED = "printed"            # the sheet she prints is different
ASKED = "asked"                # Claude is asked; nothing checks it happened
NOTHING_TO_CHANGE = "nothing_to_change"   # this kind of sheet has nothing to move

# Where each kind of sheet keeps the writing space a child fills, as paths
# into the reply. ⚠️ MEASURED BY RENDERING, 2026-10-02: only these six read
# their answer lines from the data. `investigation` fixes its lines by level in
# the generator; `cloze`, `word_bank` and `times_tables` have no writing space
# of their own -- their only ruled lines are the EAL glossary's, which is a
# support and is never shrunk.
WRITING_SPACE = {
    "reading_comprehension": ("questions", "[]"),
    "problem_solving": ("questions", "[]"),
    "matching": ("bonus_activity",),
    "sentence_builder": ("extension",),
    "calculation_practice": ("challenge",),
    "fraction_practice": ("challenge",),
}

# The kinds of sheet that print a list of questions a child reads and answers.
QUESTION_SHEETS = ("reading_comprehension", "problem_solving")

# Where the word lists live, for counting how many meanings came back.
WORD_LISTS = {
    "cloze": ("word_bank", "[]", "words", "[]"),
    "word_bank": ("categories", "[]", "words", "[]"),
    "reading_comprehension": ("vocabulary", "[]"),
}

_NOT_CHECKED = "Whether it did is not checked on the printed sheet."


def what_this_sheet_does(barrier, worksheet_type):
    """`(how, sentence)` for one ticked barrier on one kind of sheet.

    Said out loud per type rather than hiding the box -- `source_panel`'s idiom.
    A type that cannot carry a barrier says so; it never implies otherwise.
    """
    if barrier == "decoding":
        return PRINTED, "printed with extra-large spacing."
    if barrier == "limited_english":
        return PRINTED, (
            "the EAL glossary box is printed, and Claude is asked to give every word a meaning."
        )
    if barrier == "comprehension":
        if worksheet_type in QUESTION_SHEETS:
            return PRINTED, "the last two questions are taken off, never leaving fewer than three."
        return ASKED, f"Claude is asked to keep questions to finding things in the text. {_NOT_CHECKED}"
    if barrier == "writing_length":
        if worksheet_type in WRITING_SPACE:
            return PRINTED, "every space to write in is half as long."
        if worksheet_type == "investigation":
            return ASKED, (
                "Claude is asked for short answers. This sheet's writing lines are set by the "
                f"level and cannot be shortened yet. {_NOT_CHECKED}"
            )
        return NOTHING_TO_CHANGE, "this kind of sheet has no writing space to shorten."
    if barrier == "forming_sentences":
        return ASKED, f"Claude is asked to start sentences for them. {_NOT_CHECKED}"
    if barrier == "remembering_instructions":
        return ASKED, f"Claude is asked for one instruction per step. {_NOT_CHECKED}"
    if barrier == "working_independently":
        return ASKED, f"Claude is asked to start each part with an example. {_NOT_CHECKED}"
    raise KeyError(f"not a barrier this app asks about: {barrier!r}")


def print_switches(barriers):
    """`(extra_spacing, eal_glossary)` the ticked barriers turn on.

    The one definition: the outcome reads it, and so does `app.py` when it
    builds the documents from the replayed barriers. Turns things on, never off
    -- she may have ticked either box herself.
    """
    ticked = set(barriers or ())
    return ("decoding" in ticked, "limited_english" in ticked)


@dataclasses.dataclass(frozen=True)
class SupportOutcome:
    """The sheet with the barriers answered, the two print switches they turn
    on, and one sentence per ticked barrier saying what was done."""

    content: dict
    extra_spacing: bool = False
    eal_glossary: bool = False
    notes: tuple = ()


def _at(node, path):
    """Every dict at `path`, where `"[]"` means each item of a list."""
    if not path:
        if isinstance(node, dict):
            yield node
        return
    step, rest = path[0], path[1:]
    if step == "[]":
        for item in node if isinstance(node, list) else ():
            yield from _at(item, rest)
    elif isinstance(node, dict) and step in node:
        yield from _at(node[step], rest)


def _halve_the_writing(content, worksheet_type):
    for space in _at(content, WRITING_SPACE.get(worksheet_type, ())):
        if isinstance(space.get("lines"), int):
            space["lines"] = max(1, math.ceil(space["lines"] / 2))


# 🚨 A FIXED NUMBER OFF, NOT A FRACTION. The templates ask for 4-5, 6-8 and
# 8-10 questions by level. A third off rounds a 5-question sheet and a
# 6-question sheet to 4 each, collapsing two levels into one -- found by
# `test_a_longer_sheet_still_ends_up_longer`, 2026-10-02. Only a constant cut
# keeps every count apart.
QUESTIONS_TAKEN_OFF = 2
FEWEST_QUESTIONS = 3


def _fewer_questions(content):
    """The last two off, never below three -- so a longer sheet stays longer
    and the three levels stay three different sheets."""
    questions = content.get("questions") or []
    keep = max(min(len(questions), FEWEST_QUESTIONS), len(questions) - QUESTIONS_TAKEN_OFF)
    # Cut from the end, so a sheet numbered 1..n is still numbered 1..k.
    content["questions"] = questions[:keep]


def _meanings_counted(content, worksheet_type):
    words = [w for w in _at(content, WORD_LISTS.get(worksheet_type, ()))]
    if not words:
        return ""
    with_a_meaning = sum(1 for w in words if str(w.get("definition") or "").strip())
    return f" {with_a_meaning} of {len(words)} words came back with a meaning."


def with_the_barriers_answered(content, worksheet_type, barriers):
    """Edit the reply that already came back, so the barriers cost no tokens.

    Unconditional, like `with_the_source_in_place`: with nothing ticked it
    hands back an unchanged copy, so there is no branch for anyone to forget.
    ⚠️ Only ever adds support. Never more writing, never more questions, never
    a part of the sheet taken away -- the extension task stays, with less room.
    """
    ticked = [key for key in BARRIERS if key in set(barriers)]
    unknown = set(barriers) - set(BARRIERS)
    if unknown:
        raise KeyError(f"not a barrier this app asks about: {sorted(unknown)}")

    content = copy.deepcopy(content)
    if "writing_length" in ticked:
        _halve_the_writing(content, worksheet_type)
    if "comprehension" in ticked and worksheet_type in QUESTION_SHEETS:
        _fewer_questions(content)

    notes = []
    for key in ticked:
        _, sentence = what_this_sheet_does(key, worksheet_type)
        if key == "limited_english":
            sentence += _meanings_counted(content, worksheet_type)
        notes.append(f"{BARRIERS[key]} — {sentence}")

    extra_spacing, eal_glossary = print_switches(ticked)
    return SupportOutcome(
        content=content,
        extra_spacing=extra_spacing,
        eal_glossary=eal_glossary,
        notes=tuple(notes),
    )
