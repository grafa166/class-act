"""Choosing which curriculum objective a worksheet or lesson is built on.

Written before `curriculum/selection.py` existed. The bug these tests pin down:
`app.py` took `objectives[0]` for whatever topic was chosen, and topics and
objectives are two independent lists that drifted apart. Choosing the topic
"How Fossils Are Formed" produced the objective about comparing and grouping
rocks — silently, and on every worksheet built from a non-first topic.

The fix is not to pair them by position; measured across the curriculum, that
pairing is wrong too. The fix is to stop guessing and let the teacher choose.
"""

import pytest

from curriculum.selection import (
    UnknownStrandError,
    list_objectives,
    list_topics,
    resolve_objective,
)

SCI = ("Science", "Year 3", "Rocks")

FOSSILS = "Describe in simple terms how fossils are formed"
COMPARE = "Compare and group together different kinds of rocks"


class TestListing:
    def test_returns_every_objective_not_just_the_first(self):
        objectives = list_objectives(*SCI)
        assert len(objectives) == 5, "the whole strand must reach the caller"

    def test_the_fossils_objective_is_reachable(self):
        """The objective that the old code could never produce for its topic."""
        assert any(o.startswith(FOSSILS) for o in list_objectives(*SCI))

    def test_topics_are_listed_separately(self):
        topics = list_topics(*SCI)
        assert "How Fossils Are Formed" in topics

    def test_unknown_strand_raises_rather_than_returning_empty(self):
        with pytest.raises(UnknownStrandError):
            list_objectives("Science", "Year 3", "Volcanoes")

    def test_unknown_year_raises(self):
        with pytest.raises(UnknownStrandError):
            list_objectives("Science", "Year 9", "Rocks")

    def test_unknown_subject_raises(self):
        with pytest.raises(UnknownStrandError):
            list_objectives("Latin", "Year 3", "Rocks")

    def test_every_strand_in_the_curriculum_can_be_listed(self):
        """Guards against a subject whose data shape differs from the rest."""
        from curriculum import SUBJECT_REGISTRY

        for subject, cfg in SUBJECT_REGISTRY.items():
            for year, strands in cfg["curriculum"].items():
                for strand in strands:
                    assert list_objectives(subject, year, strand), (
                        f"{subject} / {year} / {strand} produced no objectives"
                    )


class TestResolving:
    def test_a_chosen_objective_is_returned(self):
        chosen = [o for o in list_objectives(*SCI) if o.startswith(FOSSILS)][0]
        assert resolve_objective(*SCI, chosen=chosen) == chosen

    def test_choosing_fossils_does_not_return_the_rocks_objective(self):
        """The regression this module exists for."""
        chosen = [o for o in list_objectives(*SCI) if o.startswith(FOSSILS)][0]
        assert not resolve_objective(*SCI, chosen=chosen).startswith(COMPARE)

    def test_a_custom_objective_wins_over_a_chosen_one(self):
        chosen = list_objectives(*SCI)[0]
        out = resolve_objective(*SCI, chosen=chosen, custom="  My own objective  ")
        assert out == "My own objective"

    def test_blank_custom_is_ignored(self):
        chosen = list_objectives(*SCI)[1]
        assert resolve_objective(*SCI, chosen=chosen, custom="   ") == chosen

    def test_choosing_nothing_falls_back_to_the_first_objective(self):
        """Preserves today's behaviour rather than changing it silently."""
        assert resolve_objective(*SCI) == list_objectives(*SCI)[0]

    def test_an_objective_from_another_strand_is_rejected(self):
        with pytest.raises(ValueError):
            resolve_objective(*SCI, chosen="Identify and name a variety of plants")

    def test_resolved_objective_is_never_blank(self):
        from curriculum import SUBJECT_REGISTRY

        for subject, cfg in SUBJECT_REGISTRY.items():
            for year, strands in cfg["curriculum"].items():
                for strand in strands:
                    assert resolve_objective(subject, year, strand).strip()
