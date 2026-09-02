"""Actually running the Plan mode page.

Same reasoning as `test_app_runs.py`: a Streamlit screen with no test that
executes it can break completely while the suite stays green.

The assertion that matters most here is the maths one. If the locked flag ever
stops reaching the screen, the app would start offering to build a maths
sequence alongside White Rose -- putting methods and prerequisites out of order
against the school's calculation policy. That is the one failure in this
product that damages a child's learning rather than the teacher's afternoon,
and it would look completely normal on screen.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import planning.scheme_intake as scheme_intake
import planning.lesson as lesson_module
import planning.spine as spine_module
from planning.scheme_intake import SchemePlanError
from planning.lesson import LessonError
from planning.spine import SpineError

APP = Path(__file__).resolve().parent.parent / "app.py"
PAGE = "pages/2_Lesson_Plans.py"
TIMEOUT = 30


def _page():
    """Reach the plan page the way the teacher does — through the running app.

    Loading the page file on its own also works right up until the sidebar
    links, which need the other pages registered; a page opened in isolation
    has no siblings. Driving it through app.py is both closer to production and
    the only way the navigation is exercised at all.
    """
    at = AppTest.from_file(str(APP), default_timeout=TIMEOUT)
    at.run()
    at.switch_page(PAGE)
    at.run()
    return at


@pytest.fixture(scope="module")
def page():
    return _page()


def test_the_page_loads_without_raising(page):
    assert not page.exception, f"the plan page raised on load: {page.exception}"


def test_it_asks_where_the_lesson_comes_from(page):
    labels = " ".join(s.label for s in page.selectbox)
    assert "Subject" in labels and "Year group" in labels and "Strand" in labels


def test_it_collects_what_to_build_on(page):
    """The teacher's steer -- the feature she asked for by name."""
    assert any("Anything else" in t.label for t in page.text_area)


def test_it_warns_against_pupil_names(page):
    """The claim 'no pupil data' is only honest if the screen says so."""
    warnings = " ".join(w.value for w in page.warning)
    assert "No names" in warnings


def test_the_sequence_can_actually_be_planned(page):
    """It was a disabled shell until the spine was wired in."""
    plan_it = [b for b in page.button if b.label == "Plan the sequence"]
    assert plan_it and not plan_it[0].disabled


class TestMathsIsProtected:
    """The one case where the app must not think for itself."""

    def _on_maths(self):
        at = _page()
        next(s for s in at.selectbox if s.label == "Subject").set_value("Maths").run()
        return at

    def test_maths_shows_a_locked_warning(self):
        at = self._on_maths()
        assert not at.exception
        assert any("locked" in e.value.lower() for e in at.error), (
            "maths did not announce that White Rose is locked"
        )

    def test_maths_asks_for_the_small_steps_instead_of_offering_objectives(self):
        at = self._on_maths()
        assert any("small step" in t.label.lower() for t in at.text_area), (
            "the White Rose small steps input is missing"
        )
        assert not any(
            "Objectives this unit covers" in m.label for m in at.multiselect
        ), "maths is offering curriculum objectives — it must use the scheme's steps"

    def test_maths_is_not_asked_to_paste_a_scheme_plan(self):
        """White Rose is followed step by step; there is no plan to rebuild."""
        at = self._on_maths()
        assert not any("covers" in t.label for t in at.text_area if "Boost" in t.label)


class TestBuildSubjects:
    def test_science_offers_the_whole_strand_of_objectives(self):
        at = _page()
        next(s for s in at.selectbox if s.label == "Subject").set_value("Science").run()
        picker = next(
            m for m in at.multiselect if "Objectives this unit covers" in m.label
        )
        assert len(picker.options) > 1

    def test_science_asks_for_the_boost_plan(self):
        at = _page()
        next(s for s in at.selectbox if s.label == "Subject").set_value("Science").run()
        assert any("Boost" in t.label for t in at.text_area), (
            "the bring-your-own-scheme box is missing for a Boost subject"
        )

    def test_english_has_no_scheme_box(self):
        """English runs off the school's own plan; there is no publisher scheme."""
        at = _page()
        next(s for s in at.selectbox if s.label == "Subject").set_value("English").run()
        assert not any("Boost" in t.label for t in at.text_area)


class TestReadingTheSchemePlan:
    """The intake, wired to the screen.

    No network: the model call is replaced, so these test the screen's
    behaviour -- what it shows, what it keeps, and what it says when the read
    fails -- not Anthropic's.
    """

    PAYLOAD = {
        "unit_title": "Rocks and Soils",
        "coverage": [
            "compare and group rocks by their physical properties",
            "properties",
        ],
        "assessment": ["end of unit quiz"],
        "activities": ["rock sorting"],
    }

    def _on_science(self, monkeypatch, outcome):
        """A Boost subject, with the model call replaced by `outcome`.

        `outcome` is a mutable dict so a test can change what the next read
        returns without rebuilding the page and losing its session state.
        """

        def fake_generate(content, system_prompt, **kwargs):
            if outcome.get("error") is not None:
                raise outcome["error"]
            return outcome.get("payload") or self.PAYLOAD

        monkeypatch.setattr(scheme_intake, "generate_structured_content", fake_generate)
        at = _page()
        next(s for s in at.selectbox if s.label == "Subject").set_value("Science").run()
        return at

    def _paste(self, at, text):
        next(t for t in at.text_area if "Boost" in t.label).set_value(text).run()

    def _click_read(self, at):
        next(b for b in at.button if b.label == "Read my plan").click().run()

    def _read_on_science(self, monkeypatch, payload=None, error=None, pasted="Boost Y3"):
        at = self._on_science(monkeypatch, {"payload": payload, "error": error})
        self._paste(at, pasted)
        self._click_read(at)
        return at

    def _body(self, at):
        return " ".join(m.value for m in at.markdown)

    def test_a_boost_subject_offers_to_read_the_plan(self):
        at = _page()
        next(s for s in at.selectbox if s.label == "Subject").set_value("Science").run()
        assert any(b.label == "Read my plan" for b in at.button)

    def test_maths_is_never_offered_a_plan_to_read(self):
        """White Rose is followed step by step; there is nothing to rebuild."""
        at = _page()
        next(s for s in at.selectbox if s.label == "Subject").set_value("Maths").run()
        assert not any(b.label == "Read my plan" for b in at.button)

    def test_reading_shows_the_coverage_she_will_be_held_to(self, monkeypatch):
        at = self._read_on_science(monkeypatch)
        assert not at.exception
        assert "compare and group rocks by their physical properties" in self._body(at)

    def test_reading_names_the_unit_it_read(self, monkeypatch):
        at = self._read_on_science(monkeypatch)
        shown = self._body(at) + " ".join(s.value for s in at.success)
        assert "Rocks and Soils" in shown

    def test_it_says_which_lines_are_not_teachable_as_written(self, monkeypatch):
        """Flagged, with the reason, never quietly rewritten."""
        at = self._read_on_science(monkeypatch)
        shown = self._body(at) + " ".join(w.value for w in at.warning)
        assert "properties" in shown
        assert "cannot be taught" in shown or "nothing to observe" in shown

    def test_a_line_left_out_of_the_coverage_is_named_not_lost(self, monkeypatch):
        """Measured against the live API: Claude moved a vague line out of the
        coverage. Whatever the cause, she has to see that it happened."""
        at = self._read_on_science(
            monkeypatch,
            payload={
                **self.PAYLOAD,
                "vague": ["Children know that rocks have different properties"],
            },
        )
        shown = self._body(at) + " ".join(w.value for w in at.warning)
        assert "Children know that rocks have different properties" in shown

    def test_the_coverage_is_kept_for_the_rest_of_the_planning(self, monkeypatch):
        """The spine, the coverage map and the gap list all read this."""
        at = self._read_on_science(monkeypatch)
        assert at.session_state["plan_scheme_plan"].unit_title == "Rocks and Soils"

    def test_a_rejected_plan_says_so_instead_of_showing_nothing(self, monkeypatch):
        at = self._read_on_science(
            monkeypatch, error=SchemePlanError("The plan lists no coverage.")
        )
        assert not at.exception
        assert any("no coverage" in e.value for e in at.error)

    def test_a_failed_read_wipes_the_plan_it_replaces(self, monkeypatch):
        """A coverage list still on screen beside an error would be read as the
        plan that was just accepted."""
        outcome = {}
        at = self._on_science(monkeypatch, outcome)

        self._paste(at, "Boost Y3 Autumn 1")
        self._click_read(at)
        assert at.session_state["plan_scheme_plan"], "the first read never landed"

        outcome["error"] = SchemePlanError("The plan lists no coverage.")
        self._paste(at, "a different page entirely")
        self._click_read(at)

        assert "plan_scheme_plan" not in at.session_state
        assert "compare and group rocks" not in self._body(at), (
            "the old unit's coverage is still on screen under the error"
        )

    def test_an_empty_box_is_told_what_to_do_not_sent(self, monkeypatch):
        at = self._read_on_science(monkeypatch, pasted="   ")
        assert not at.exception
        assert any("aste" in e.value for e in at.error), "no instruction to paste"

    def test_editing_the_plan_afterwards_warns_the_record_is_stale(self, monkeypatch):
        """The coverage list is what she would hand a subject leader. It must
        not silently describe a page she has since changed."""
        at = self._read_on_science(monkeypatch)
        next(t for t in at.text_area if "Boost" in t.label).set_value("different").run()
        assert any("older version" in w.value.lower() for w in at.warning)

    def test_an_unchanged_plan_is_not_called_stale(self, monkeypatch):
        at = self._read_on_science(monkeypatch)
        assert not any("older version" in w.value.lower() for w in at.warning)


class TestPlanningTheSequence:
    """The spine on the screen.

    The maths tests here are the important ones. If the locked route ever stops
    being taken, the app starts inventing an order alongside White Rose, and it
    would look completely normal.
    """

    SPINE = {
        "lessons": [
            {
                "number": 1,
                "objective": "Identify and name rocks by their appearance",
                "builds_on": None,
                "builds_on_reason": "Starting point.",
                "covers": ["compare and group rocks by their physical properties"],
                "assesses_outcome": False,
            },
            {
                "number": 2,
                "objective": "Group rocks by their physical properties",
                "builds_on": 1,
                "builds_on_reason": "needs the naming vocabulary first",
                "covers": [],
                "assesses_outcome": True,
            },
        ]
    }

    def _science(self, monkeypatch, payload=None, error=None, lessons=2):
        calls = []

        def fake_generate(content, system_prompt, **kwargs):
            calls.append(content)
            if error is not None:
                raise error
            return payload if payload is not None else self.SPINE

        monkeypatch.setattr(spine_module, "generate_structured_content", fake_generate)
        at = _page()
        next(s for s in at.selectbox if s.label == "Subject").set_value("Science").run()
        # Changing subject empties the objectives box, so choose one the way she
        # does. Without this the sequence has nothing to build from.
        picker = next(
            m for m in at.multiselect if "Objectives this unit covers" in m.label
        )
        picker.set_value(picker.options[:1]).run()
        next(n for n in at.number_input if n.label == "Lessons").set_value(lessons).run()
        next(b for b in at.button if b.label == "Plan the sequence").click().run()
        return at, calls

    def _maths(self, monkeypatch, steps):
        calls = []

        def fake_generate(content, system_prompt, **kwargs):
            calls.append(content)
            raise AssertionError("maths must never reach the model")

        monkeypatch.setattr(spine_module, "generate_structured_content", fake_generate)
        at = _page()
        next(s for s in at.selectbox if s.label == "Subject").set_value("Maths").run()
        next(t for t in at.text_area if "small step" in t.label.lower()).set_value(steps).run()
        next(b for b in at.button if b.label == "Plan the sequence").click().run()
        return at, calls

    def _body(self, at):
        return " ".join(m.value for m in at.markdown)

    def _objectives(self, at):
        return [t.value for t in at.text_input if t.label.startswith("Objective for lesson")]

    # ── the drafted route ────────────────────────────────────────────────────

    def test_the_chain_of_objectives_appears(self, monkeypatch):
        at, _ = self._science(monkeypatch)
        assert not at.exception
        assert "Identify and name rocks by their appearance" in self._objectives(at)

    def test_it_says_why_each_lesson_needs_the_one_before(self, monkeypatch):
        """The link is not the point. The reason is what she is judging."""
        at, _ = self._science(monkeypatch)
        captions = " ".join(c.value for c in at.caption)
        assert "needs the naming vocabulary first" in captions

    def test_the_objectives_are_hers_to_change(self, monkeypatch):
        at, _ = self._science(monkeypatch)
        assert self._objectives(at), "the objectives are not editable"

    def test_the_lessons_can_be_written_from_it(self, monkeypatch):
        at, _ = self._science(monkeypatch)
        write = [b for b in at.button if b.label == "Write all the lessons"]
        assert write and not write[0].disabled

    def test_a_rejected_sequence_says_so_and_shows_nothing(self, monkeypatch):
        at, _ = self._science(
            monkeypatch, error=SpineError("Lesson 3 builds on lesson 9.")
        )
        assert not at.exception
        assert any("lesson 9" in e.value.lower() for e in at.error)
        assert "plan_spine" not in at.session_state

    def test_asking_for_more_lessons_than_came_back_is_caught(self, monkeypatch):
        """The validator, reached through the screen rather than directly."""
        at, _ = self._science(monkeypatch, lessons=6)
        assert not at.exception
        assert any("6" in e.value for e in at.error)

    def test_what_the_class_struggled_with_reaches_the_request(self, monkeypatch):
        at, calls = self._science(monkeypatch)
        assert calls, "nothing was sent"

    # ── maths ────────────────────────────────────────────────────────────────

    def test_maths_never_reaches_the_model(self, monkeypatch):
        at, calls = self._maths(
            monkeypatch, "Represent numbers to 1,000\nPartition numbers to 1,000"
        )
        assert not at.exception
        assert calls == [], "a maths sequence was sent off to be invented"

    def test_the_small_steps_become_the_objectives_word_for_word(self, monkeypatch):
        at, _ = self._maths(
            monkeypatch, "Compare numbers to 1,000\nRepresent numbers to 1,000"
        )
        assert self._objectives(at) == [
            "Compare numbers to 1,000",
            "Represent numbers to 1,000",
        ]

    def test_maths_with_no_steps_typed_says_what_to_do(self, monkeypatch):
        at, _ = self._maths(monkeypatch, "   ")
        assert not at.exception
        assert any("step" in e.value.lower() for e in at.error)

    # ── the coverage map ─────────────────────────────────────────────────────

    def test_a_scheme_line_no_lesson_teaches_is_shown_as_a_gap(self, monkeypatch):
        """Her evidence to the subject leader that nothing was dropped."""
        outcome = {}
        at = TestReadingTheSchemePlan()._on_science(monkeypatch, outcome)
        TestReadingTheSchemePlan()._paste(at, "Boost Y3")
        TestReadingTheSchemePlan()._click_read(at)

        monkeypatch.setattr(
            spine_module,
            "generate_structured_content",
            lambda content, system_prompt, **kw: {
                "lessons": [
                    {
                        "number": 1,
                        "objective": "Identify and name rocks",
                        "builds_on": None,
                        "builds_on_reason": "Starting point.",
                        "covers": [
                            "compare and group rocks by their physical properties"
                        ],
                        "assesses_outcome": False,
                    },
                    {
                        "number": 2,
                        "objective": "Group rocks by property",
                        "builds_on": 1,
                        "builds_on_reason": "needs the naming vocabulary",
                        "covers": [],
                        "assesses_outcome": True,
                    },
                ]
            },
        )
        next(n for n in at.number_input if n.label == "Lessons").set_value(2).run()
        next(b for b in at.button if b.label == "Plan the sequence").click().run()

        assert not at.exception
        body = self._body(at)
        assert "no lesson teaches this" in body, "a dropped coverage line is invisible"
        assert any("not taught by any lesson" in w.value for w in at.warning)


def _lesson_payload(objective, minutes=60):
    """The smallest lesson that passes every check, for a given objective."""
    def step(mins):
        return {
            "name": "Modelling",
            "minutes": mins,
            "on_the_board": "Two rocks and the property words",
            "teacher_says": "Watch me pick one word for this rock.",
            "questions": [{"ask": "Which word fits?", "expect": "rough"}],
            "children_do": "Talk to a partner and agree a word",
            "watch_for": [{"wrong": "They say 'nice'", "respond": "Point at the word bank"}],
            "adults": "TA on the back table",
        }

    half = minutes // 2
    return {
        "objective": objective,
        "success_criteria": [
            {"criterion": "I can describe two rocks.", "evidence": "comparison table"},
            {"criterion": "I can group rocks.", "evidence": "sorted rocks in books"},
        ],
        "vocabulary": {
            "everyone": ["hard", "soft"],
            "expected": ["grainy"],
            "stretch": ["permeable"],
            "guidance": "Teach the everyday word, then name the technical one.",
        },
        "steps": [step(half), step(minutes - half)],
        "misconceptions": [
            {"misconception": "Heavier means harder", "why": "both feel physical",
             "address": "Compare chalk with granite"}
        ],
        "assessment": {
            "look_for": "A heading naming a property",
            "not_yet_example": "Rocks grouped under 'nice ones'",
        },
        "adaptations": {
            "eal": "Word bank with photographs",
            "send": "Start from two very different rocks",
            "stretch": "Test permeability with a pipette",
        },
        "resources": [{"item": "Rock samples", "quantity": "6 sets of 4"}],
        "next_lesson": "Testing hardness",
    }


class TestWritingTheLessons:
    """The lessons themselves, written from the sequence she approved.

    The test that matters most is the edited-objective one. If a lesson is
    written from the drafted objective rather than the one she changed, the
    approval step is decoration and the plan, the worksheet and the child's book
    stop agreeing — with nothing on screen showing it.
    """

    def _fake_writer(self, failures=None, calls=None):
        """Echoes back whatever objective the prompt asked for.

        Which is itself the assertion: if the prompt stopped carrying the
        objective, this could not answer, and every test here would fail.
        """
        failures = failures or {}

        def fake(content, system_prompt, **kwargs):
            text = content if isinstance(content, str) else str(content)
            objective = text.split("improve it:\n  ", 1)[1].split("\n", 1)[0]
            if calls is not None:
                calls.append(objective)
            number = len(calls or []) or 1
            if number in failures:
                raise failures[number]
            return _lesson_payload(objective)

        return fake

    def _written(self, monkeypatch, edits=None, failures=None, calls=None):
        at, _ = TestPlanningTheSequence()._science(monkeypatch)
        monkeypatch.setattr(
            lesson_module,
            "generate_structured_content",
            self._fake_writer(failures=failures, calls=calls),
        )
        for number, text in (edits or {}).items():
            next(
                t for t in at.text_input
                if t.label == f"Objective for lesson {number}"
            ).set_value(text).run()
        next(b for b in at.button if b.label == "Write all the lessons").click().run()
        return at

    def _body(self, at):
        return " ".join(m.value for m in at.markdown)

    def test_the_lessons_are_written(self, monkeypatch):
        at = self._written(monkeypatch)
        assert not at.exception
        assert len(at.session_state["plan_written_lessons"]) == 2

    def test_the_lesson_shows_what_actually_happens(self, monkeypatch):
        """Not an outline. The words, the questions, the wrong answer."""
        body = self._body(self._written(monkeypatch))
        assert "Watch me pick one word for this rock." in body
        assert "expect: rough" in body
        assert "Point at the word bank" in body

    def test_the_three_vocabulary_bands_are_shown(self, monkeypatch):
        body = self._body(self._written(monkeypatch))
        assert "Everyone leaves with" in body and "Stretch" in body

    def test_it_shows_work_that_has_not_met_the_criterion(self, monkeypatch):
        body = self._body(self._written(monkeypatch))
        assert "nice ones" in body

    def test_it_is_labelled_as_a_draft_not_as_verified(self, monkeypatch):
        at = self._written(monkeypatch)
        captions = " ".join(c.value for c in at.caption)
        assert "AI-drafted" in captions
        assert "verified" not in captions.lower()

    def test_the_objective_she_edited_is_the_one_written_from(self, monkeypatch):
        """The whole point of the approval step."""
        calls = []
        self._written(
            monkeypatch,
            edits={1: "Name rocks by how they feel"},
            calls=calls,
        )
        assert calls[0] == "Name rocks by how they feel"

    def test_an_objective_edited_to_nothing_stops_before_any_writing(self, monkeypatch):
        calls = []
        at = self._written(monkeypatch, edits={1: "   "}, calls=calls)
        assert not at.exception
        assert calls == []
        assert any("objective" in e.value.lower() for e in at.error)

    def test_a_failure_part_way_keeps_what_was_written_and_says_what_is_missing(
        self, monkeypatch
    ):
        """Three good lessons are worth having. A unit that looks complete and
        is not is the failure this screen exists to avoid."""
        at = self._written(
            monkeypatch,
            failures={2: LessonError("The lesson came back with a different objective")},
            calls=[],
        )
        assert not at.exception
        assert len(at.session_state["plan_written_lessons"]) == 1
        assert any("lesson 2" in w.value.lower() for w in at.warning)

    def test_replanning_the_sequence_drops_lessons_from_the_old_one(self, monkeypatch):
        """They belong to objectives that no longer exist."""
        at = self._written(monkeypatch)
        assert at.session_state["plan_written_lessons"]
        next(b for b in at.button if b.label == "Plan the sequence").click().run()
        assert "plan_written_lessons" not in at.session_state
