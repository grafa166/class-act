"""Actually running app.py.

Until now nothing in this suite executed `app.py`. `test_smoke.py` reads it as
text with the AST module and deliberately avoids importing it, because
importing a Streamlit script runs it. So the file holding the entire user
interface had no coverage at all: it could render nothing, lose every widget,
or crash on load, and 221 tests would still pass.

Streamlit ships `AppTest` for exactly this. These tests are deliberately shallow
-- they load the app and check the controls exist. That is enough to catch the
class of failure the suite could not see before, and it is the safety net for
adding a second mode alongside the worksheet flow.

No network: the Anthropic call only happens on a button press, and nothing here
presses it.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app.py"
TIMEOUT = 30


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(str(APP), default_timeout=TIMEOUT)
    at.run()
    return at


def test_the_app_loads_without_raising(app):
    """The check that did not exist. A syntax or import error fails here."""
    assert not app.exception, f"app.py raised on load: {app.exception}"


def test_the_sidebar_controls_are_present(app):
    labels = " ".join(s.label for s in app.selectbox)
    for expected in ("Subject", "Year Group", "Strand", "Topic"):
        assert expected in labels, f"the {expected} control disappeared"


def test_the_learning_objective_is_now_a_choice(app):
    """The fix: the objective is chosen, not silently taken as the first one."""
    labels = [s.label for s in app.selectbox]
    assert any("Learning Objective" in l for l in labels), (
        "the objective picker is missing -- the app is back to guessing"
    )


def test_the_objective_picker_offers_the_whole_strand(app):
    """Not one objective. The old code exposed exactly one, always the first."""
    picker = next(s for s in app.selectbox if "Learning Objective" in s.label)
    assert len(picker.options) > 1, (
        "only one objective offered; the rest of the strand is unreachable again"
    )


def test_changing_subject_keeps_the_app_alive():
    """Subject drives year groups, strands and objectives -- a cascade worth checking."""
    at = AppTest.from_file(str(APP), default_timeout=TIMEOUT)
    at.run()
    subject = next(s for s in at.selectbox if "Subject" in s.label)
    subject.set_value("Science").run()
    assert not at.exception
    picker = next(s for s in at.selectbox if "Learning Objective" in s.label)
    assert picker.options, "no objectives after switching subject"


def test_switching_strand_reloads_its_own_objectives():
    """Guards the wrong-objective bug: objectives must follow the chosen strand."""
    at = AppTest.from_file(str(APP), default_timeout=TIMEOUT)
    at.run()
    next(s for s in at.selectbox if "Subject" in s.label).set_value("Science").run()

    strand = next(s for s in at.selectbox if s.label.endswith("Strand"))
    seen = {}
    for option in list(strand.options)[:3]:
        strand = next(s for s in at.selectbox if s.label.endswith("Strand"))
        strand.set_value(option).run()
        assert not at.exception
        picker = next(s for s in at.selectbox if "Learning Objective" in s.label)
        seen[option] = tuple(picker.options)

    assert len(set(seen.values())) > 1, (
        "every strand offered the same objectives -- they are not following the strand"
    )
