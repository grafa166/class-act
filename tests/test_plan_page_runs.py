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
from planning.scheme_intake import SchemePlanError

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


def test_the_generate_button_is_not_pretending_to_work(page):
    """A shell must not look finished."""
    plan_it = [b for b in page.button if b.label == "Plan it"]
    assert plan_it and plan_it[0].disabled


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

    def test_maths_asks_for_the_small_step_instead_of_offering_objectives(self):
        at = self._on_maths()
        assert any("small step" in t.label.lower() for t in at.text_input), (
            "the White Rose small step input is missing"
        )
        assert not any(
            "Objectives this unit covers" in m.label for m in at.multiselect
        ), "maths is offering curriculum objectives — it must use the scheme's step"

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
