"""What the prompt says when she has said what the children should do, and what
is getting in the way.

Two new blocks, and one rule about where they go that is the whole design:

    [source opening] -> [base template] -> [task] -> [barriers] -> [source rules]

Her one hard constraint -- *"only use what I've supplied and do not reveal later
parts"* -- is defended by `SOURCE_LAW` sitting **last**, the strongest position
(measured 2026-09-15). Her main English route is a scanned page, where the name
check cannot run at all, so on that route the ordering is the only defence
there is. A task box saying *"write the next chapter"* placed after the source
rules would outrank them. So the task outranks the template, and her own text
outranks the task.
"""

import pytest

from llm.prompts import (
    SOURCE_LAW,
    TASK_MARKER,
    BARRIERS_MARKER,
    barrier_instructions,
    get_prompt,
    list_worksheet_types,
    task_instructions,
)
from planning.source_material import (
    SourceMaterial,
    actions_for,
    source_from_text,
)
from planning.support import BARRIERS

EXTRACT = (
    "When Mary Lennox was sent to Misselthwaite Manor to live with her uncle "
    "everybody said she was the most disagreeable-looking child ever seen."
)

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

TASK = "Sort the facts about Mary into two piles: what she looks like, and how she behaves."
ALL_BARRIERS = tuple(BARRIERS)


def held():
    return source_from_text(EXTRACT, origin="the text you pasted")


def scanned():
    """Her main English route: a scan, whose words nothing here can read."""
    return SourceMaterial(text="", origin="chapter-3.pdf", blocks=({"type": "document"},))


class TestNothingChangesWhenNothingIsTicked:
    @pytest.mark.parametrize("worksheet_type", list_worksheet_types())
    def test_an_empty_task_and_no_barriers_is_the_string_it_has_always_been(self, worksheet_type):
        before = get_prompt(worksheet_type=worksheet_type, **COMMON)
        after = get_prompt(worksheet_type=worksheet_type, task="  ", barriers=(), **COMMON)
        assert before == after


class TestATaskWithNoUploadIsNotDropped:
    """`get_prompt` used to return the bare template as soon as it saw no source.
    A task typed with no upload would have gone nowhere, silently."""

    @pytest.mark.parametrize("worksheet_type", list_worksheet_types())
    def test_her_task_reaches_the_prompt_with_no_source(self, worksheet_type):
        prompt = get_prompt(worksheet_type=worksheet_type, task=TASK, **COMMON)
        assert TASK in prompt

    @pytest.mark.parametrize("worksheet_type", list_worksheet_types())
    def test_the_barriers_reach_the_prompt_with_no_source(self, worksheet_type):
        prompt = get_prompt(worksheet_type=worksheet_type, barriers=("decoding",), **COMMON)
        assert BARRIERS_MARKER in prompt


def _every_source_case():
    for worksheet_type in list_worksheet_types():
        for make in (held, scanned):
            for action in actions_for(worksheet_type, make()):
                yield worksheet_type, make, action


SOURCE_CASES = list(_every_source_case())


class TestHerTextStillHasTheLastWord:
    def test_there_are_source_cases_to_check(self):
        # A control: a parametrize over an empty list reports green.
        assert len(SOURCE_CASES) > 20

    @pytest.mark.parametrize("worksheet_type,make,action", SOURCE_CASES)
    def test_the_source_law_comes_after_the_task(self, worksheet_type, make, action):
        prompt = get_prompt(
            worksheet_type=worksheet_type,
            source_material=make(),
            source_action=action,
            task="Write the next chapter.",
            barriers=ALL_BARRIERS,
            **COMMON,
        )
        assert prompt.rindex(SOURCE_LAW) > prompt.rindex(TASK_MARKER)
        assert prompt.rindex(SOURCE_LAW) > prompt.rindex(BARRIERS_MARKER)

    @pytest.mark.parametrize("worksheet_type,make,action", SOURCE_CASES)
    def test_the_source_law_is_the_final_block(self, worksheet_type, make, action):
        prompt = get_prompt(
            worksheet_type=worksheet_type,
            source_material=make(),
            source_action=action,
            task="Write the next chapter.",
            barriers=ALL_BARRIERS,
            **COMMON,
        )
        assert prompt.rstrip().endswith(SOURCE_LAW)

    def test_the_task_comes_after_the_template(self):
        prompt = get_prompt(worksheet_type="cloze", task=TASK, **COMMON)
        assert prompt.index(TASK_MARKER) > prompt.index("DIFFERENTIATION LEVEL RULES")

    def test_the_barriers_come_after_the_task(self):
        prompt = get_prompt(
            worksheet_type="cloze", task=TASK, barriers=("decoding",), **COMMON
        )
        assert prompt.index(BARRIERS_MARKER) > prompt.index(TASK_MARKER)


class TestTheTaskCannotFlattenTheThreeLevels:
    """The three API calls differ only by `level`. A task that fixes the number
    of questions or the length collapses three sheets into one sheet at three
    font sizes -- and she pays for three."""

    def test_the_task_block_says_the_levels_still_decide_how_much(self):
        block = task_instructions(TASK)
        assert "DIFFERENTIATION LEVEL RULES" in block
        assert "how many questions" in block

    def test_the_task_block_says_the_objective_stands(self):
        assert "objective" in task_instructions(TASK).lower()

    def test_the_task_block_says_the_json_shape_stands(self):
        assert "field this worksheet already has" in task_instructions(TASK)

    def test_the_barrier_block_says_the_levels_still_decide_how_much(self):
        assert "DIFFERENTIATION LEVEL RULES" in barrier_instructions(ALL_BARRIERS)

    def test_word_meanings_are_asked_for_even_where_the_level_leaves_them_out(self):
        """Found by reading the assembled prompt, 2026-10-02: the cloze and word
        bank level rules say an expected sheet's words "should NOT include
        definition fields". A barrier block that asked for meanings while also
        saying it overrides no level rule handed the model a contradiction.
        A support is a floor, never a ceiling: it may only ever add help."""
        block = barrier_instructions(("limited_english",))
        assert '"definition"' in block
        assert "even where the level rules above leave it out" in block
        assert "more support" in block

    @pytest.mark.parametrize("worksheet_type", list_worksheet_types())
    def test_the_three_prompts_still_differ_with_a_task_and_every_barrier(self, worksheet_type):
        prompts = {
            get_prompt(
                worksheet_type=worksheet_type,
                task=TASK,
                barriers=ALL_BARRIERS,
                **{**COMMON, "level": level},
            )
            for level in ("developing", "expected", "greater_depth")
        }
        assert len(prompts) == 3


class TestHerWordsCannotBreakTheTemplate:
    def test_a_task_with_curly_braces_in_it_survives(self):
        task = "Fill in {the gaps} using the {word bank}."
        assert task in get_prompt(worksheet_type="cloze", task=task, **COMMON)


class TestWhatLeavesTheBuilding:
    """Seven tick-boxes means what is sent is one of 128 fixed strings."""

    def test_exactly_128_different_things_can_be_sent(self):
        from itertools import combinations

        every_ticking = [
            combo
            for n in range(len(ALL_BARRIERS) + 1)
            for combo in combinations(ALL_BARRIERS, n)
        ]
        assert len({barrier_instructions(combo) for combo in every_ticking}) == 128

    def test_every_line_sent_is_one_this_module_wrote(self):
        from llm import prompts

        written = set(
            "\n".join(
                [prompts.BARRIERS_HEADER, prompts.BARRIERS_FOOTER, *prompts.BARRIER_SENTENCES.values()]
            ).splitlines()
        )
        sent = set(barrier_instructions(ALL_BARRIERS).splitlines()) - {""}
        assert sent <= written

    def test_an_unknown_barrier_is_refused_not_sent(self):
        with pytest.raises(KeyError):
            barrier_instructions(("Ellie cannot read",))

    def test_no_barriers_means_no_block(self):
        assert barrier_instructions(()) == ""

    def test_the_order_she_ticks_them_in_does_not_change_what_is_sent(self):
        assert barrier_instructions(("decoding", "writing_length")) == barrier_instructions(
            ("writing_length", "decoding")
        )
