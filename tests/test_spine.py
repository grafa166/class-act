"""The unit spine — the chain of objectives, before any lesson is written.

The spine is small, fast and the part worth the teacher's judgement, so she
approves or edits it before anything longer is generated. It is also where the
sequence can be checked by a program rather than by an opinion: a lesson cannot
build on a lesson that comes after it, a six-lesson unit cannot come back with
five, and a unit cannot claim to cover something the school's scheme never
mentioned.

Maths never reaches the model at all. White Rose is mandated, its order is tied
to the school's calculation policy, and the safest way to guarantee it is not
re-sequenced is to have nothing capable of re-sequencing it in the path.

None of these tests touch the network.
"""

import pytest

import planning.spine as spine_module
from planning.spine import (
    SPINE_SYSTEM_PROMPT,
    SpineError,
    UnitSpine,
    build_locked_spine,
    build_spine_prompt,
    coverage_map,
    coverage_never_taught,
    generate_spine,
    validate_spine,
)

OUTCOME = "Children group unknown rocks by their properties and justify each grouping."

COVERAGE = [
    "compare and group together different kinds of rocks",
    "describe in simple terms how fossils are formed",
    "recognise that soils are made from rocks and organic matter",
]


def lesson(number, objective=None, builds_on=None, reason=None, covers=None, outcome=False):
    return {
        "number": number,
        "objective": objective or f"Objective for lesson {number}",
        "builds_on": builds_on if builds_on is not None else (None if number == 1 else number - 1),
        "builds_on_reason": (
            reason
            if reason is not None
            else ("Starting point." if number == 1 else f"Needs lesson {number - 1}.")
        ),
        "covers": covers if covers is not None else [],
        "assesses_outcome": outcome,
    }


def spine_of(count, overrides=None):
    lessons = [lesson(n, outcome=(n == count)) for n in range(1, count + 1)]
    for number, fields in (overrides or {}).items():
        lessons[number - 1].update(fields)
    return {"lessons": lessons}


def _validate(payload, count=3, coverage=()):
    return validate_spine(payload, expected_count=count, coverage=coverage)


class TestTheShapeOfIt:
    def test_a_good_spine_validates(self):
        result = _validate(spine_of(3))
        assert isinstance(result, UnitSpine)
        assert [lsn.number for lsn in result.lessons] == [1, 2, 3]

    def test_the_objective_survives_word_for_word(self):
        """Everything downstream inherits this string. It is never re-derived."""
        payload = spine_of(3, {2: {"objective": "Group rocks by their properties"}})
        assert _validate(payload).lessons[1].objective == "Group rocks by their properties"

    def test_asking_for_six_and_getting_five_is_rejected(self):
        """Named in the plan. A short unit renders as if it were the whole one."""
        with pytest.raises(SpineError, match="6"):
            _validate(spine_of(5), count=6)

    def test_a_missing_lesson_number_is_rejected(self):
        with pytest.raises(SpineError):
            _validate(spine_of(3, {2: {"number": 4}}))

    def test_a_repeated_lesson_number_is_rejected(self):
        with pytest.raises(SpineError):
            _validate(spine_of(3, {3: {"number": 2}}))

    def test_an_empty_objective_is_rejected(self):
        with pytest.raises(SpineError, match="objective"):
            _validate(spine_of(3, {2: {"objective": "   "}}))

    def test_the_same_objective_twice_is_rejected(self):
        """Six lessons teaching the same thing is a sequence in name only."""
        with pytest.raises(SpineError, match="twice|same"):
            _validate(spine_of(3, {3: {"objective": "Objective for lesson 2"}}))

    def test_a_payload_that_is_not_a_spine_is_rejected(self):
        with pytest.raises(SpineError):
            _validate({"lessons": "six of them"})

    def test_no_lessons_at_all_is_rejected(self):
        with pytest.raises(SpineError):
            _validate({"lessons": []}, count=0)


class TestTheChain:
    def test_lesson_one_starts_the_unit(self):
        assert _validate(spine_of(3)).lessons[0].builds_on is None

    def test_a_lesson_may_not_build_on_one_that_comes_later(self):
        """Named in the plan: lesson 4 declaring builds_on 9. It reads as a
        sequence and teaches in an order nothing supports."""
        with pytest.raises(SpineError, match="later|after"):
            _validate(spine_of(4, {2: {"builds_on": 3}}), count=4)

    def test_a_lesson_may_not_build_on_itself(self):
        with pytest.raises(SpineError):
            _validate(spine_of(3, {2: {"builds_on": 2}}))

    def test_a_lesson_may_not_build_on_one_that_does_not_exist(self):
        with pytest.raises(SpineError):
            _validate(spine_of(4, {4: {"builds_on": 9}}), count=4)

    def test_lesson_one_may_not_build_on_anything(self):
        with pytest.raises(SpineError):
            _validate(spine_of(3, {1: {"builds_on": 1}}))

    def test_a_later_lesson_must_build_on_something(self):
        """A unit of unconnected lessons is what the teacher already has."""
        with pytest.raises(SpineError, match="builds on nothing|build on"):
            _validate(spine_of(3, {3: {"builds_on": None}}))

    def test_saying_which_lesson_is_not_enough_without_saying_why(self):
        """'Builds on L2' is a link. 'Grouping must be secure before it can be
        justified' is the thing she is actually judging."""
        with pytest.raises(SpineError, match="why|reason"):
            _validate(spine_of(3, {2: {"builds_on_reason": "  "}}))

    def test_a_lesson_may_build_on_one_further_back_than_the_last(self):
        assert _validate(spine_of(4, {4: {"builds_on": 2}}), count=4).lessons[3].builds_on == 2


class TestTheEndOfUnitOutcome:
    def test_the_last_lesson_assesses_it(self):
        assert _validate(spine_of(3)).lessons[-1].assesses_outcome

    def test_a_unit_that_never_assesses_its_outcome_is_rejected(self):
        with pytest.raises(SpineError, match="outcome"):
            _validate(spine_of(3, {3: {"assesses_outcome": False}}))

    def test_assessing_it_in_the_middle_is_rejected(self):
        """The outcome is what the unit ends on, not something passed on the way."""
        with pytest.raises(SpineError, match="outcome"):
            _validate(spine_of(3, {1: {"assesses_outcome": True}}))


class TestWhatTheUnitCovers:
    def test_a_lesson_may_not_invent_coverage_the_scheme_never_had(self):
        """The coverage record is her evidence to the subject leader. A line
        added here would be read as the school's own plan."""
        payload = spine_of(3, {2: {"covers": ["build a volcano"]}})
        with pytest.raises(SpineError, match="not in the"):
            _validate(payload, coverage=COVERAGE)

    def test_coverage_taken_from_the_scheme_is_kept(self):
        payload = spine_of(3, {2: {"covers": [COVERAGE[0]]}})
        assert _validate(payload, coverage=COVERAGE).lessons[1].covers == [COVERAGE[0]]

    def test_nothing_is_checked_when_there_is_no_scheme_to_check_against(self):
        """English and RE have no publisher coverage list to be held to."""
        payload = spine_of(3, {2: {"covers": ["anything at all"]}})
        assert _validate(payload).lessons[1].covers == ["anything at all"]

    def test_the_map_says_which_lesson_teaches_each_line(self):
        payload = spine_of(3, {1: {"covers": [COVERAGE[0]]}, 2: {"covers": [COVERAGE[0], COVERAGE[1]]}})
        spine = _validate(payload, coverage=COVERAGE)
        assert coverage_map(spine, COVERAGE)[COVERAGE[0]] == [1, 2]

    def test_a_line_no_lesson_teaches_comes_back_empty_not_missing(self):
        """The gap has to be visible. A coverage map with a line quietly absent
        is the same failure as dropping it."""
        spine = _validate(spine_of(3, {1: {"covers": [COVERAGE[0]]}}), coverage=COVERAGE)
        mapping = coverage_map(spine, COVERAGE)
        assert mapping[COVERAGE[2]] == []
        assert set(mapping) == set(COVERAGE)

    def test_a_gap_does_not_reject_the_spine(self):
        """Shown, never enforced -- she may be teaching it elsewhere, and the
        tool does not get to overrule her on what her class has covered."""
        assert _validate(spine_of(3), coverage=COVERAGE).lessons


class TestCoverageAssessedButNeverTaught:
    """Found on the first live run, 2026-09-02.

    Told that every coverage line must be taught by at least one lesson, the
    draft attached "recognise that soils are made from rocks" to the final
    lesson -- whose objective was grouping unknown rocks by property, and which
    plainly did not teach soil. The line was dropped in substance while the
    coverage map vouched for it, which is worse than an honest gap: the map is
    the artefact she would show a subject leader.

    Nothing here reads an objective and decides whether it teaches a thing --
    that is a judgement, and this project does not have AI judging AI. This is
    structural: a line whose only lesson is the one that assesses the outcome
    was assessed without ever being taught.
    """

    def test_a_line_only_in_the_final_assessment_is_flagged(self):
        spine = _validate(
            spine_of(3, {3: {"covers": [COVERAGE[2]]}}), coverage=COVERAGE
        )
        assert coverage_never_taught(spine, COVERAGE) == [COVERAGE[2]]

    def test_a_line_taught_earlier_and_assessed_at_the_end_is_fine(self):
        spine = _validate(
            spine_of(3, {2: {"covers": [COVERAGE[2]]}, 3: {"covers": [COVERAGE[2]]}}),
            coverage=COVERAGE,
        )
        assert coverage_never_taught(spine, COVERAGE) == []

    def test_a_line_no_lesson_claims_at_all_is_a_gap_not_this(self):
        """An honest gap is already reported by the coverage map. This is only
        for the case that looks covered and is not."""
        spine = _validate(spine_of(3), coverage=COVERAGE)
        assert coverage_never_taught(spine, COVERAGE) == []

    def test_a_one_lesson_unit_cannot_trip_it(self):
        """The only lesson is also the assessment. Flagging everything there
        would be noise, not a finding."""
        spine = _validate(spine_of(1, {1: {"covers": [COVERAGE[0]]}}), count=1, coverage=COVERAGE)
        assert coverage_never_taught(spine, COVERAGE) == []


class TestMathsIsNeverResequenced:
    """White Rose is mandated and tied to the school's calculation policy.

    Nothing here asks a model for an order, because the only guarantee that an
    order cannot be invented is that nothing in the path is capable of
    inventing one.
    """

    STEPS = [
        "Represent numbers to 1,000",
        "Partition numbers to 1,000",
        "Compare numbers to 1,000",
    ]

    def test_the_steps_become_the_objectives_word_for_word(self):
        spine = build_locked_spine(self.STEPS, outcome=OUTCOME, scheme="White Rose")
        assert [lsn.objective for lsn in spine.lessons] == self.STEPS

    def test_her_order_is_kept(self):
        """Deliberately neither alphabetical nor reverse-alphabetical: an
        earlier version of this test used a reversed list that happened to be
        in alphabetical order, so it passed against a sort."""
        hers = [self.STEPS[2], self.STEPS[0], self.STEPS[1]]
        spine = build_locked_spine(hers, outcome=OUTCOME, scheme="White Rose")
        assert [lsn.objective for lsn in spine.lessons] == hers

    def test_it_survives_the_same_validation_as_a_drafted_one(self):
        spine = build_locked_spine(self.STEPS, outcome=OUTCOME, scheme="White Rose")
        assert spine.lessons[0].builds_on is None
        assert all(lsn.builds_on == lsn.number - 1 for lsn in spine.lessons[1:])
        assert spine.lessons[-1].assesses_outcome

    def test_the_reason_given_is_the_scheme_not_invented_pedagogy(self):
        """We know the school teaches these in this order. We do not know why,
        and saying so would be putting words in the scheme's mouth."""
        spine = build_locked_spine(self.STEPS, outcome=OUTCOME, scheme="White Rose")
        assert "White Rose" in spine.lessons[1].builds_on_reason

    def test_it_says_the_order_is_the_schemes(self):
        spine = build_locked_spine(self.STEPS, outcome=OUTCOME, scheme="White Rose")
        assert "White Rose" in spine.source

    def test_blank_lines_between_steps_are_not_lessons(self):
        spine = build_locked_spine(
            ["Represent numbers to 1,000", "   ", "Partition numbers to 1,000"],
            outcome=OUTCOME,
            scheme="White Rose",
        )
        assert len(spine.lessons) == 2

    def test_no_steps_at_all_is_refused(self):
        with pytest.raises(SpineError, match="step"):
            build_locked_spine(["  "], outcome=OUTCOME, scheme="White Rose")

    def test_the_same_step_twice_is_refused(self):
        with pytest.raises(SpineError):
            build_locked_spine(
                ["Represent numbers to 1,000", "Represent numbers to 1,000"],
                outcome=OUTCOME,
                scheme="White Rose",
            )


@pytest.fixture
def sent(monkeypatch):
    record = {"payload": spine_of(3)}

    def fake_generate(content, system_prompt, **kwargs):
        record["content"] = content
        record["system_prompt"] = system_prompt
        if record.get("raises") is not None:
            raise record["raises"]
        return record["payload"]

    monkeypatch.setattr(spine_module, "generate_structured_content", fake_generate)
    return record


def _generate(**kwargs):
    defaults = dict(
        subject="Science",
        year_group="Year 3",
        lesson_count=3,
        outcome=OUTCOME,
        objectives=["compare and group rocks"],
    )
    return generate_spine(**{**defaults, **kwargs})


class TestAskingForASpine:
    def test_it_comes_back_validated(self, sent):
        assert len(_generate().lessons) == 3

    def test_a_short_spine_is_rejected_not_returned(self, sent):
        sent["payload"] = spine_of(2)
        with pytest.raises(SpineError):
            _generate(lesson_count=3)

    def test_the_prompt_carries_the_outcome_the_unit_ends_on(self, sent):
        _generate()
        assert OUTCOME in str(sent["content"])

    def test_the_prompt_carries_the_schemes_coverage(self, sent):
        _generate(coverage=COVERAGE, scheme="Boost", unit_title="Rocks and Soils")
        text = str(sent["content"])
        assert all(line in text for line in COVERAGE)
        assert "Rocks and Soils" in text

    def test_what_the_class_struggled_with_reaches_the_request(self, sent):
        """The feature she asked for by name. If it does not reach the model it
        is decoration."""
        _generate(build_on="permeability confused everyone")
        assert "permeability confused everyone" in str(sent["content"])

    def test_the_lesson_count_is_asked_for_explicitly(self, sent):
        _generate(lesson_count=3)
        assert "3" in str(sent["content"])

    def test_the_system_prompt_is_the_planning_one(self, sent):
        _generate()
        assert sent["system_prompt"] == SPINE_SYSTEM_PROMPT

    def test_maths_never_gets_here(self, sent):
        """Belt and braces: the screen routes maths to the locked builder, and
        this refuses it even if a future caller forgets."""
        with pytest.raises(SpineError, match="White Rose|locked"):
            _generate(subject="Maths")
        assert "content" not in sent, "a maths spine was sent to be invented"

    def test_nothing_to_build_from_is_refused_before_the_call(self, sent):
        with pytest.raises(SpineError):
            _generate(objectives=[], coverage=[])
        assert "content" not in sent


class TestTheSpinePrompt:
    def _prompt(self, **kw):
        defaults = dict(
            subject="Science",
            year_group="Year 3",
            lesson_count=6,
            outcome=OUTCOME,
            objectives=["compare and group rocks"],
            coverage=COVERAGE,
            scheme="Boost",
            unit_title="Rocks and Soils",
            build_on="",
        )
        return build_spine_prompt(**{**defaults, **kw})

    def test_it_asks_for_each_lesson_to_need_the_one_before(self):
        low = self._prompt().lower()
        assert "builds_on" in low and "before" in low

    def test_it_asks_why_not_just_which(self):
        assert "why" in self._prompt().lower()

    def test_it_forbids_covering_anything_the_scheme_did_not_name(self):
        low = self._prompt().lower()
        assert "only" in low and "coverage" in low

    def test_it_would_rather_leave_a_gap_than_fake_the_coverage(self):
        """Measured live: told every line must be taught, the draft attached a
        line about soil to a lesson about grouping rocks. An honest gap is a
        far better outcome than a coverage map that vouches for nothing."""
        low = self._prompt().lower()
        assert "gap" in low and ("does not teach" in low or "do not attach" in low)

    def test_it_requires_the_last_lesson_to_assess_the_outcome(self):
        assert "assesses_outcome" in self._prompt()

    def test_it_asks_for_json_only(self):
        assert "json" in self._prompt().lower()
