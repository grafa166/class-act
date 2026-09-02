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
