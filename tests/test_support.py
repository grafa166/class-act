"""A barrier changes the page, not just the prompt.

`with_the_barriers_answered` edits the JSON that already came back, so it costs
no tokens, and it works at all because several renderers are data-gated rather
than level-gated: six of the ten answer-line sites read `lines` from the data.

⚠️ **Measured by rendering, not by grepping** (adversarial pass, 2026-10-02):
"writing a lot" moves the page on six types only. `investigation` hard-codes its
lines by level; `cloze`, `word_bank` and `times_tables` have no writing space of
their own -- their only ruled lines are the EAL glossary's four, which is a
*support* and is never shrunk. So the headline test is scoped to an allow-list,
with a companion asserting the other four are untouched. ⚠️ Do not soften the
`<` to `<=` to make one test cover all ten: that passes vacuously on the four,
which is the empty-haystack-reports-green failure this project is built against.
"""

import copy
import io
import math
import random
from itertools import combinations

import pytest
from docx import Document

from llm.prompts import list_worksheet_types
from planning.support import (
    ASKED,
    BARRIERS,
    NOTHING_TO_CHANGE,
    PRINTED,
    WRITING_SPACE,
    print_switches,
    what_this_sheet_does,
    with_the_barriers_answered,
)
from tests.fixtures import ALL_CONTENT
from tests.test_worksheet_typography import GENERATORS, text_of

LEVELS = ("developing", "expected", "greater_depth")
WRITES_AT_LENGTH = (
    "calculation_practice",
    "fraction_practice",
    "matching",
    "problem_solving",
    "reading_comprehension",
    "sentence_builder",
)
NO_WRITING_TO_CUT = ("cloze", "investigation", "times_tables", "word_bank")


def render(kind, content, level="expected", extra_spacing=False, eal_glossary=True):
    # ⚠️ Matching pairs and sentence-builder cards are shuffled on purpose, so
    # two renders of one sheet differ. Seeded here, or a comparison of two
    # renders measures the shuffle instead of the barrier.
    random.seed(0)
    return Document(
        GENERATORS[kind](
            content=content,
            theme_key="space",
            level=level,
            objective="Pupils can describe a rock using property words.",
            extra_spacing=extra_spacing,
            eal_glossary=eal_glossary,
            show_answers=False,
        )
    )


def ruled_lines(doc):
    """Every line a child writes on: a run of underscores and nothing else."""
    return sum(
        1
        for line in text_of(doc).splitlines()
        if len(line.strip()) >= 20 and set(line.strip()) == {"_"}
    )


def answered(kind, barriers, content=None):
    return with_the_barriers_answered(
        copy.deepcopy(content or ALL_CONTENT[kind]), kind, barriers
    )


class TestTheAllowListIsTheTruth:
    def test_the_two_lists_cover_every_type_exactly_once(self):
        assert sorted(WRITES_AT_LENGTH + NO_WRITING_TO_CUT) == list_worksheet_types()

    def test_the_module_agrees_with_what_rendering_measured(self):
        assert set(WRITING_SPACE) == set(WRITES_AT_LENGTH)


class TestWritingALot:
    @pytest.mark.parametrize("kind", WRITES_AT_LENGTH)
    def test_the_printed_sheet_has_strictly_fewer_lines_to_write_on(self, kind):
        before = ruled_lines(render(kind, ALL_CONTENT[kind]))
        after = ruled_lines(render(kind, answered(kind, ("writing_length",)).content))
        assert after < before

    @pytest.mark.parametrize("kind", NO_WRITING_TO_CUT)
    def test_a_sheet_with_no_writing_space_of_its_own_is_untouched(self, kind):
        before = text_of(render(kind, ALL_CONTENT[kind]))
        after = text_of(render(kind, answered(kind, ("writing_length",)).content))
        assert after == before

    @pytest.mark.parametrize("kind", NO_WRITING_TO_CUT)
    def test_the_eal_glossary_lines_are_never_shrunk(self, kind):
        # The four glossary lines are the only ruled lines these sheets have.
        lines = ruled_lines(render(kind, answered(kind, ("writing_length",)).content))
        assert lines >= 4

    def test_no_writing_space_falls_below_one_line(self):
        content = answered("reading_comprehension", ("writing_length",)).content
        assert all(q["lines"] >= 1 for q in content["questions"])

    def test_the_task_itself_is_kept_only_the_space_shrinks(self):
        """Her words: remove the barrier, don't just make the work easier.
        So the extension task stays on the page with less room, not deleted."""
        content = answered("sentence_builder", ("writing_length",)).content
        assert content["extension"]["instructions"] == ALL_CONTENT["sentence_builder"]["extension"]["instructions"]


def _with_questions(kind, n):
    content = copy.deepcopy(ALL_CONTENT[kind])
    template = content["questions"][0]
    content["questions"] = [
        {**template, "number": i + 1, "question": f"Question {i + 1}?"} for i in range(n)
    ]
    return content


class TestUnderstandingWhatTheyRead:
    @pytest.mark.parametrize("kind", ("reading_comprehension", "problem_solving"))
    def test_the_printed_sheet_asks_fewer_questions(self, kind):
        content = _with_questions(kind, 9)
        after = answered(kind, ("comprehension",), content).content
        assert len(after["questions"]) < 9
        assert "Question 9?" not in text_of(render(kind, after))

    def test_one_question_is_never_cut_to_none(self):
        after = answered("reading_comprehension", ("comprehension",), _with_questions("reading_comprehension", 1)).content
        assert len(after["questions"]) == 1

    def test_a_longer_sheet_still_ends_up_longer(self):
        """The three levels ask for different numbers of questions. Cutting the
        same number off each keeps their order, so the three sheets do not
        collapse into one -- and she does not pay three times for one sheet."""
        kept = [
            len(answered("reading_comprehension", ("comprehension",), _with_questions("reading_comprehension", n)).content["questions"])
            for n in range(1, 13)
        ]
        assert kept == sorted(kept)
        # ...and the three counts the template asks for stay three counts.
        for dev, exp, gd in ((5, 6, 8), (4, 6, 8), (5, 7, 10)):
            counts = {
                len(answered("reading_comprehension", ("comprehension",), _with_questions("reading_comprehension", n)).content["questions"])
                for n in (dev, exp, gd)
            }
            assert len(counts) == 3, (dev, exp, gd, counts)


class TestTheRenderSwitches:
    def test_decoding_turns_the_extra_spacing_on(self):
        assert answered("cloze", ("decoding",)).extra_spacing is True

    def test_limited_english_turns_the_glossary_box_on(self):
        assert answered("cloze", ("limited_english",)).eal_glossary is True

    def test_the_outcome_and_the_document_builder_share_one_rule(self):
        """`app.py` builds the documents from the replayed barriers, not from
        the outcome, so the rule must have one definition both read."""
        for combo in EVERY_TICKING:
            outcome = answered("cloze", combo)
            assert print_switches(combo) == (outcome.extra_spacing, outcome.eal_glossary)

    def test_nothing_ticked_turns_nothing_on(self):
        outcome = answered("cloze", ())
        assert outcome.extra_spacing is False and outcome.eal_glossary is False


class TestNothingTickedIsTheSheetAsItWas:
    @pytest.mark.parametrize("kind", list_worksheet_types())
    @pytest.mark.parametrize("level", LEVELS)
    def test_the_rendered_text_is_character_identical(self, kind, level):
        before = text_of(render(kind, ALL_CONTENT[kind], level=level))
        after = text_of(render(kind, answered(kind, ()).content, level=level))
        assert after == before

    def test_her_content_is_not_edited_in_place(self):
        original = copy.deepcopy(ALL_CONTENT["reading_comprehension"])
        with_the_barriers_answered(original, "reading_comprehension", ("writing_length", "comprehension"))
        assert original == ALL_CONTENT["reading_comprehension"]


EVERY_TICKING = [
    combo for n in range(len(BARRIERS) + 1) for combo in combinations(BARRIERS, n)
]


def _lines_in(content):
    total = 0

    def walk(node):
        nonlocal total
        if isinstance(node, dict):
            if isinstance(node.get("lines"), int):
                total += node["lines"]
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(content)
    return total


def _keys_in(node, path=()):
    if isinstance(node, dict):
        for key, value in node.items():
            yield path + (key,)
            yield from _keys_in(value, path + (key,))
    elif isinstance(node, list) and node:
        yield from _keys_in(node[0], path + ("[]",))


class TestNeverHarder:
    def test_all_128_tickings_are_checked(self):
        assert len(EVERY_TICKING) == 128

    @pytest.mark.parametrize("kind", list_worksheet_types())
    def test_no_ticking_adds_writing_questions_or_takes_a_part_away(self, kind):
        original = ALL_CONTENT[kind]
        for combo in EVERY_TICKING:
            after = answered(kind, combo).content
            assert _lines_in(after) <= _lines_in(original), combo
            assert len(after.get("questions", ())) <= len(original.get("questions", ())), combo
            assert set(_keys_in(after)) == set(_keys_in(original)), combo


class TestSayingWhatThisSheetCanCarry:
    """Four of seven barriers change the printed sheet in this slice; three do
    not, because they need a worked example or chunked steps, which exist
    nowhere in the repo. The screen must not imply all seven are handled."""

    @pytest.mark.parametrize("kind", list_worksheet_types())
    @pytest.mark.parametrize("barrier", list(BARRIERS))
    def test_every_barrier_has_an_answer_for_every_type(self, barrier, kind):
        how, sentence = what_this_sheet_does(barrier, kind)
        assert how in (PRINTED, ASKED, NOTHING_TO_CHANGE)
        assert sentence.strip()

    @pytest.mark.parametrize("barrier", ("forming_sentences", "remembering_instructions", "working_independently"))
    @pytest.mark.parametrize("kind", list_worksheet_types())
    def test_the_three_with_nothing_printed_never_claim_to_be_printed(self, barrier, kind):
        how, sentence = what_this_sheet_does(barrier, kind)
        assert how == ASKED
        assert "not checked" in sentence

    @pytest.mark.parametrize("kind", NO_WRITING_TO_CUT)
    def test_writing_a_lot_is_not_claimed_where_nothing_moves(self, kind):
        how, _ = what_this_sheet_does("writing_length", kind)
        assert how != PRINTED

    @pytest.mark.parametrize("kind", WRITES_AT_LENGTH)
    def test_writing_a_lot_is_claimed_where_the_page_moves(self, kind):
        how, _ = what_this_sheet_does("writing_length", kind)
        assert how == PRINTED

    def test_the_outcome_carries_one_note_per_ticked_barrier(self):
        outcome = answered("cloze", ("decoding", "working_independently"))
        assert len(outcome.notes) == 2
        assert outcome.notes[0].startswith(BARRIERS["decoding"])


class TestTheMeaningsAreCounted:
    """Asking for word meanings is a request to a model. Whether they came back
    is a fact about the reply, so the screen says how many did."""

    def test_the_note_counts_the_meanings_that_came_back(self):
        content = copy.deepcopy(ALL_CONTENT["cloze"])
        words = [w for group in content["word_bank"] for w in group["words"]]
        del words[0]["definition"]
        outcome = with_the_barriers_answered(content, "cloze", ("limited_english",))
        assert f"{len(words) - 1} of {len(words)}" in outcome.notes[0]
