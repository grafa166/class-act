"""Where a lesson comes from, per subject.

The teacher does not plan in a vacuum, and she does not follow a scheme blindly
either -- it depends on the subject. White Rose is mandated by the school and
its sequence must never be second-guessed; deviating from it would put methods
and vocabulary out of order against the school's calculation policy. Everything
else is hers to build, using whatever scheme exists as a reference rather than
a script.

These tests pin that distinction down, because getting it wrong for maths is
the one failure in this product that could actively harm a child's learning
rather than merely waste the teacher's time.
"""

import pytest

from curriculum import SUBJECT_REGISTRY
from planning.anchors import (
    LOCKED,
    OWN_BUILD,
    anchor_for,
    is_locked,
    suggest_lesson_count,
)


class TestLocking:
    def test_maths_is_locked(self):
        assert is_locked("Maths")

    def test_maths_names_white_rose(self):
        assert anchor_for("Maths").scheme == "White Rose"

    def test_maths_is_the_only_locked_subject(self):
        locked = [s for s in SUBJECT_REGISTRY if is_locked(s)]
        assert locked == ["Maths"], (
            f"only maths is mandated; these were also locked: {locked}"
        )

    @pytest.mark.parametrize(
        "subject", ["Science", "History", "Geography", "Computing"]
    )
    def test_the_boost_subjects_are_hers_to_build(self, subject):
        anchor = anchor_for(subject)
        assert anchor.mode == OWN_BUILD
        assert anchor.scheme == "Boost"

    def test_re_follows_lighting_the_path_but_is_still_hers(self):
        anchor = anchor_for("RE")
        assert anchor.scheme == "Lighting the Path"
        assert anchor.mode == OWN_BUILD

    def test_english_has_no_published_scheme(self):
        anchor = anchor_for("English")
        assert anchor.mode == OWN_BUILD
        assert anchor.scheme is None

    def test_every_subject_in_the_app_has_an_anchor(self):
        for subject in SUBJECT_REGISTRY:
            assert anchor_for(subject) is not None, f"{subject} has no anchor"

    def test_an_unknown_subject_defaults_to_build_not_locked(self):
        """Failing open to 'locked' would block work; failing to 'build' is safe."""
        anchor = anchor_for("Latin")
        assert anchor.mode == OWN_BUILD
        assert anchor.scheme is None

    def test_a_locked_anchor_forbids_resequencing(self):
        assert anchor_for("Maths").may_resequence is False

    def test_a_build_anchor_permits_resequencing(self):
        assert anchor_for("Science").may_resequence is True

    def test_publisher_schemes_are_never_reproduced(self):
        """Copyright boundary: the teacher supplies the text, we never ship it."""
        for subject in SUBJECT_REGISTRY:
            anchor = anchor_for(subject)
            if anchor.scheme:
                assert anchor.teacher_supplies_content, (
                    f"{subject} names {anchor.scheme} but does not require the "
                    "teacher to supply its content"
                )


class TestLessonCount:
    def test_it_suggests_something_sensible_for_a_half_term(self):
        assert 4 <= suggest_lesson_count(weeks=6, objectives=5) <= 8

    def test_fewer_weeks_means_fewer_lessons(self):
        assert suggest_lesson_count(weeks=4, objectives=5) < suggest_lesson_count(
            weeks=8, objectives=5
        )

    def test_it_never_suggests_fewer_lessons_than_there_are_objectives(self):
        """Six is a suggestion, not a rule -- but coverage still has to fit."""
        assert suggest_lesson_count(weeks=3, objectives=6) >= 6

    def test_it_always_suggests_at_least_one(self):
        assert suggest_lesson_count(weeks=0, objectives=0) >= 1

    def test_it_is_a_suggestion_not_a_cap(self):
        """Documented behaviour: callers may override. Nothing here enforces it."""
        assert isinstance(suggest_lesson_count(weeks=6, objectives=5), int)
