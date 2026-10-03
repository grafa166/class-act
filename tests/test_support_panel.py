"""The two new boxes on the worksheet screen, run through `app.py`.

1. *"What should pupils actually do on this worksheet?"* -- optional, about the
   work.
2. *"What is getting in the way?"* -- seven tick-boxes and **no free text**.

⚠️ **Her wording was "what does this pupil need help with?"** The word *pupil*
invites a name into a box that is sent to Anthropic, and the lesson page already
records that a free-text need box *"predictably attracts pupil names, and 'we
did not ask for them' is not a control."* So the heading asks about the work,
and the only thing that can leave the building is one of 128 fixed strings.
"""

import ast
import pathlib

import pytest
from streamlit.testing.v1 import AppTest

from llm.prompts import barrier_instructions
from planning.support import BARRIERS, what_this_sheet_does
from support_panel import TASK_LIMIT, task_as_sent, task_box_problem

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"
PANEL = ROOT / "support_panel.py"
LESSON_PAGE = ROOT / "pages" / "2_Lesson_Plans.py"
TIMEOUT = 30


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(str(APP), default_timeout=TIMEOUT)
    at.run()
    return at


def _box(at, label):
    return next(c for c in at.checkbox if c.label == label)


class TestTheTwoBoxesAreOnTheScreen:
    def test_the_app_still_loads(self, app):
        assert not app.exception, f"app.py raised on load: {app.exception}"

    def test_there_is_a_box_for_what_pupils_should_do(self, app):
        labels = [t.label for t in app.text_area]
        assert "What should pupils actually do on this worksheet?" in labels

    def test_all_seven_barriers_are_offered_in_her_words(self, app):
        labels = {c.label for c in app.checkbox}
        assert set(BARRIERS.values()) <= labels

    def test_the_heading_asks_about_the_work_not_the_child(self, app):
        said = " ".join(m.value for m in app.markdown if isinstance(m.value, str))
        assert "What is getting in the way?" in said

    def test_no_label_on_either_box_says_pupil_needs(self):
        """'Pupil' in the task question is about the work. Anywhere near the
        barriers it invites a name."""
        source = PANEL.read_text(encoding="utf-8")
        barrier_part = source[source.index("def barriers_panel"):]
        assert "pupil" not in barrier_part.lower()


class TestNothingAboutAChildCanBeTyped:
    """⚠️ SOFTENED mutation target. Adding a free-text "anything else?" box here
    is exactly what a future well-meaning session will do, and this is the only
    thing standing in front of it."""

    def test_the_barrier_panel_offers_no_box_to_type_in(self):
        tree = ast.parse(PANEL.read_text(encoding="utf-8"))
        panel = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "barriers_panel"
        )
        called = {
            node.func.attr
            for node in ast.walk(panel)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert called, "the parse found no calls at all -- the check is blind"
        assert "checkbox" in called
        assert not called & {"text_area", "text_input", "chat_input"}

    def test_ticking_every_barrier_adds_no_box_to_type_in(self):
        at = AppTest.from_file(str(APP), default_timeout=TIMEOUT)
        at.run()
        before = len(at.text_area) + len(at.text_input)
        for label in BARRIERS.values():
            _box(at, label).check()
        at.run()
        assert not at.exception
        assert len(at.text_area) + len(at.text_input) == before


class TestShowMeWhatGetsSent:
    def test_the_literal_block_is_shown_from_the_function_that_builds_it(self):
        at = AppTest.from_file(str(APP), default_timeout=TIMEOUT)
        at.run()
        _box(at, BARRIERS["decoding"]).check()
        _box(at, BARRIERS["writing_length"]).check()
        at.run()
        shown = [c.value for c in at.code]
        assert barrier_instructions(("decoding", "writing_length")) in shown

    def test_each_ticked_barrier_says_what_this_kind_of_sheet_does_about_it(self):
        at = AppTest.from_file(str(APP), default_timeout=TIMEOUT)
        at.run()
        _box(at, BARRIERS["working_independently"]).check()
        at.run()
        said = " ".join(c.value for c in at.caption if isinstance(c.value, str))
        # The default sheet type on load is the first English type.
        _, sentence = what_this_sheet_does("working_independently", "cloze")
        assert sentence in said

    def test_nothing_is_shown_when_nothing_is_ticked(self, app):
        assert not [c for c in app.code if "WHAT IS GETTING IN THE WAY" in c.value]


class TestTheTaskBox:
    def test_a_short_task_is_fine(self):
        assert task_box_problem("Sort the rocks into two groups.") is None

    def test_a_pasted_text_is_sent_to_the_right_box(self):
        """A 2,000-word "task" is her pasting the children's text into the wrong
        box -- detectable, unlike a task that contradicts the objective."""
        problem = task_box_problem("word " * (TASK_LIMIT // 4))
        assert problem is not None
        assert "own text" in problem.lower()

    @pytest.mark.parametrize("task", [
        "Answer six questions about Mary.",
        "Write 3 sentences about the rocks.",
        "Ten questions on the story",
    ])
    def test_a_task_that_sets_a_number_is_told_the_levels_decide(self, task):
        """Measured live 2026-10-03: a number in her words flattened the three
        levels into one. Whatever the prompt does about it, she is told."""
        problem = task_box_problem(task)
        assert problem is not None and "three levels" in problem

    @pytest.mark.parametrize("task,sent", [
        ("Answer six questions about Mary.", "Answer questions about Mary."),
        ("Write 3 sentences about the rocks.", "Write sentences about the rocks."),
        ("Ten questions on the story", "questions on the story"),
        ("Sort the rocks into two piles.", "Sort the rocks into two piles."),
    ])
    def test_the_number_is_taken_out_before_it_is_sent(self, task, sent):
        """MEASURED LIVE 2026-10-03, twice more after rewording the prompt:
        6/6/6 and 5/6/6. No instruction beats her explicit number, so it is not
        sent -- and the screen shows her what is."""
        assert task_as_sent(task) == sent

    def test_the_screen_shows_the_task_as_it_is_sent(self):
        at = AppTest.from_file(str(APP), default_timeout=TIMEOUT)
        at.run()
        box = next(t for t in at.text_area if t.label == "What should pupils actually do on this worksheet?")
        box.input("Answer six questions about Mary.")
        at.run()
        shown = " ".join(str(i.value) for i in at.info)
        assert "They will:** Answer questions about Mary." in shown
        assert any("three levels" in str(w.value) for w in at.warning)

    @pytest.mark.parametrize("task", [
        "Sort the rocks into two piles.",
        "Find three clues that Mary is unhappy.",
        "Label the parts of the plant.",
    ])
    def test_a_task_with_a_number_that_is_not_a_count_of_questions_is_left_alone(self, task):
        """A guard that refuses correct work is worse than no guard."""
        assert task_box_problem(task) is None

    def test_a_task_that_announces_a_different_goal_is_flagged(self):
        problem = task_box_problem("Pupils only need to copy the words, a different objective.")
        assert problem is not None

    def test_a_pasted_text_in_the_task_box_is_not_sent(self):
        """Found by the mutation run, 2026-10-02: the refusal was computed and
        the text sent anyway, and nothing noticed."""
        at = AppTest.from_file(str(APP), default_timeout=TIMEOUT)
        at.run()
        box = next(t for t in at.text_area if t.label == "What should pupils actually do on this worksheet?")
        box.input("Mary was a thin child. " * 40)
        at.run()
        assert any("longer than a task" in str(w.value) for w in at.warning)
        # Not sent means not shown as what they will do, either.
        assert not any("They will:" in str(i.value) for i in at.info)

    def test_the_objective_and_the_task_are_shown_side_by_side(self):
        at = AppTest.from_file(str(APP), default_timeout=TIMEOUT)
        at.run()
        box = next(t for t in at.text_area if t.label == "What should pupils actually do on this worksheet?")
        box.input("Sort the rocks into two groups.")
        at.run()
        said = " ".join(
            str(e.value) for e in list(at.info) + list(at.markdown) + list(at.caption)
        )
        assert "They will:" in said and "Sort the rocks into two groups." in said


class TestTheLessonPageIsNotSilent:
    """The lesson page prints sheets for children by a second, independent path
    that these boxes do not reach in this slice. Silence there would be the
    'nothing changes silently' failure."""

    def test_the_lesson_page_says_the_two_boxes_do_not_apply_there(self):
        # ⚠️ Parsed, not grepped: the import line also names NOT_ON_THIS_PAGE,
        # so a bare `in source` passed with the sentence deleted (mutation run,
        # 2026-10-02).
        tree = ast.parse(LESSON_PAGE.read_text(encoding="utf-8"))
        worksheet_section = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_the_worksheet_for"
        )
        shown = [
            node for node in ast.walk(worksheet_section)
            if isinstance(node, ast.Call)
            and getattr(node.func, "attr", "") == "caption"
            and any(isinstance(a, ast.Name) and a.id == "NOT_ON_THIS_PAGE" for a in node.args)
        ]
        assert shown, "the worksheet section of the lesson page never shows the sentence"
        from support_panel import NOT_ON_THIS_PAGE

        assert "worksheet screen" in NOT_ON_THIS_PAGE
        assert "getting in the way" in NOT_ON_THIS_PAGE


class TestTheWiringInApp:
    """`app.py` is read as text: pressing Generate calls the live API."""

    def _block(self):
        source = APP.read_text(encoding="utf-8")
        start = source.index("if generate_btn or _regenerating:")
        return source[start:source.index("# Phase 2", start)]

    def test_both_boxes_travel_with_the_prompt(self):
        block = self._block()
        call = block[block.index("get_prompt("):]
        call = call[: call.index(")\n")]
        assert "task=params.get('task')" in call
        assert "barriers=params.get('barriers')" in call

    def test_the_barriers_are_answered_after_her_text_is_in_place_and_before_the_names(self):
        block = self._block()
        source_step = block.index("with_the_source_in_place(")
        barrier_step = block.index("with_the_barriers_answered(")
        names_step = block.index("with_the_names_checked(")
        assert source_step < barrier_step < names_step

    def test_her_task_counts_as_something_she_supplied(self):
        """Forget it and every sheet warns about her own wording, she learns to
        ignore the warnings, and the next real spoiler walks through."""
        block = self._block()
        call = block[block.index("with_the_names_checked("):]
        call = call[: call.index("st.session_state.source_outcomes")]
        assert "params.get('task'" in call

    def test_the_sheet_kept_is_the_one_with_the_barriers_answered(self):
        """Found by the mutation run, 2026-10-02: drop the line that carries
        the edited sheet forward and every barrier is worked out, described on
        screen, and never printed."""
        block = self._block()
        carried = "outcome = dataclasses.replace(outcome, content=support.content)"
        assert carried in block
        assert block.index("with_the_barriers_answered(") < block.index(carried) < block.index(
            "content = outcome.content"
        )

    def test_what_the_barriers_did_is_kept_for_the_preview(self):
        assert "st.session_state.support_outcomes[level]" in self._block()

    def test_the_documents_are_built_with_the_barriers_print_switches(self):
        source = APP.read_text(encoding="utf-8")
        build = source[source.index("def build_and_download"):source.index("# ─── Generation Flow")]
        assert "print_switches(params.get('barriers'" in build
        # Found by the mutation run, 2026-10-02: the switches were computed and
        # the documents built from her own two ticks alone.
        assert "extra_spacing = params['extra_spacing'] or barrier_spacing" in build
        assert "eal_glossary = params['eal_glossary'] or barrier_glossary" in build
        assert "params['extra_spacing'], params['eal_glossary']" not in build
        assert build.count("extra_spacing, eal_glossary,") == 2
