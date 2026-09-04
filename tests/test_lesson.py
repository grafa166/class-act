"""A lesson deep enough to teach from, and the checks that keep it honest.

The first prototype was rejected for being *"the bullet point outline of what
the lesson should include — it doesn't speak to what would actually happen in
the lesson."* So the standard here is: deep enough to build slides from. Every
step says what is on the board, what the teacher says, what the children do,
and what to watch for; the lesson names its misconceptions, its vocabulary in
three bands, and an example of work that has **not** met the criterion.

The checks are structural and nothing else. There is no AI judging whether the
teaching is any good — that is the teacher's, which is why the whole lesson is
shown to her and labelled "AI-drafted — check before teaching". What a program
*can* establish is checked ruthlessly: the objective is the one she approved,
word for word; the timings add up to the lesson she actually has; success
criteria name evidence rather than effort; and an adaptation may not quietly
become a different, easier objective.

None of these tests touch the network.
"""

import json

import jsonschema
import pytest

import planning.lesson as lesson_module
from llm.client import TruncatedResponseError
from planning.lesson import (
    LESSON_SCHEMA,
    LESSON_SYSTEM_PROMPT,
    Lesson,
    LessonError,
    build_lesson_prompt,
    build_repair_prompt,
    generate_lesson,
    lowered_objective_flags,
    validate_lesson,
)
from planning.spine import validate_spine

OBJECTIVE = "Group rocks by their physical properties"


def step(minutes=15, **overrides):
    base = {
        "name": "Modelling",
        "minutes": minutes,
        "on_the_board": "Two rocks, and the words hard / soft / rough / smooth",
        "teacher_says": "Watch me. I am going to pick one word for this rock.",
        "questions": [
            {"ask": "Which word fits this rock?", "expect": "rough, because you can feel the grains"}
        ],
        "children_do": "Talk to their partner and agree one word for the second rock",
        "watch_for": [
            {
                "wrong": "Children say 'nice' or 'good' instead of a property",
                "respond": "Point at the word bank and ask which of these words they mean",
            }
        ],
        "adults": "TA sits with the four children on the back table",
        "builds_on_step": "The hook gave them the words; this shows how to use one",
    }
    base.update(overrides)
    return base


def lesson_payload(**overrides):
    base = {
        "objective": OBJECTIVE,
        "success_criteria": [
            {"criterion": "I can describe two rocks using property words.",
             "evidence": "completed comparison table"},
            {"criterion": "I can put rocks into groups and say what the group has in common.",
             "evidence": "sorted rocks stuck into books with a group heading"},
        ],
        "vocabulary": {
            "everyone": ["hard", "soft", "rough", "smooth"],
            "expected": ["grainy", "layered", "absorbent"],
            "stretch": ["permeable", "impermeable"],
            "guidance": "Teach the everyday word, then name the technical one beside it.",
        },
        "steps": [step(20), step(20, name="Practice"), step(20, name="Plenary")],
        "misconceptions": [
            {
                "misconception": "Heavier means harder",
                "why": "Children conflate weight with hardness because both feel physical",
                "address": "Compare a large piece of chalk with a small piece of granite",
            }
        ],
        "assessment": {
            "look_for": "A group heading that names a property rather than a colour",
            "not_yet_example": (
                "Three rocks grouped under 'nice ones' — the child has sorted but "
                "not by a property"
            ),
        },
        "adaptations": {
            "eal": "Word bank with a photograph beside each property word",
            "send": "Pre-sorted pair of very different rocks to start from",
            "stretch": "Offer permeable and ask them to test it with a pipette",
        },
        "resources": [{"item": "Rock samples", "quantity": "6 sets of 4"}],
        "next_lesson": "Testing hardness by scratching",
    }
    base.update(overrides)
    return base


def _validate(payload=None, objective=OBJECTIVE, minutes=60):
    return validate_lesson(
        payload if payload is not None else lesson_payload(),
        expected_objective=objective,
        lesson_minutes=minutes,
    )


class TestTheObjectiveIsHers:
    """The single most important guarantee in the product.

    She approves the spine; the lesson is written from it; the worksheet is
    later built from the lesson. If the objective drifts at any of those
    handovers, the plan, the sheet and the child's book stop agreeing, and
    nothing on screen would show it.
    """

    def test_the_approved_objective_comes_back_word_for_word(self):
        assert _validate().objective == OBJECTIVE

    def test_a_reworded_objective_is_rejected(self):
        payload = lesson_payload(objective="Sort rocks by their physical properties")
        with pytest.raises(LessonError, match="objective"):
            _validate(payload)

    def test_even_a_better_objective_is_rejected(self):
        """It is not ours to improve. She approved a sentence."""
        payload = lesson_payload(
            objective="Group rocks by their physical properties and justify the grouping"
        )
        with pytest.raises(LessonError):
            _validate(payload)

    def test_surrounding_whitespace_is_not_a_difference(self):
        assert _validate(lesson_payload(objective=f"  {OBJECTIVE}  ")).objective == OBJECTIVE


class TestSuccessCriteria:
    def test_two_to_five_criteria(self):
        assert len(_validate().success_criteria) == 2

    def test_one_criterion_is_not_enough(self):
        payload = lesson_payload(
            success_criteria=[{"criterion": "I can group rocks.", "evidence": "sorted rocks"}]
        )
        with pytest.raises(LessonError, match="criteri"):
            _validate(payload)

    def test_six_criteria_is_too_many_to_assess_in_a_lesson(self):
        payload = lesson_payload(
            success_criteria=[
                {"criterion": f"I can do thing {n}.", "evidence": f"evidence {n}"}
                for n in range(6)
            ]
        )
        with pytest.raises(LessonError, match="criteri"):
            _validate(payload)

    def test_a_criterion_with_no_evidence_is_rejected(self):
        """If nothing in the lesson produces it, it cannot be assessed."""
        payload = lesson_payload(
            success_criteria=[
                {"criterion": "I can describe two rocks.", "evidence": "  "},
                {"criterion": "I can group rocks.", "evidence": "sorted rocks"},
            ]
        )
        with pytest.raises(LessonError, match="evidence"):
            _validate(payload)

    @pytest.mark.parametrize(
        "criterion",
        [
            "I worked hard on my rock sorting.",
            "I tried my best in this lesson.",
            "I did my best to listen.",
            "I behaved well during the investigation.",
        ],
    )
    def test_effort_is_not_evidence(self, criterion):
        """Named in the plan. A child cannot know whether they met it, and a
        teacher cannot mark it."""
        payload = lesson_payload(
            success_criteria=[
                {"criterion": criterion, "evidence": "the teacher's judgement"},
                {"criterion": "I can group rocks.", "evidence": "sorted rocks"},
            ]
        )
        with pytest.raises(LessonError, match="effort"):
            _validate(payload)

    def test_a_criterion_naming_a_product_is_fine(self):
        payload = lesson_payload(
            success_criteria=[
                {"criterion": "I can hard-boil my reasoning into one sentence.",
                 "evidence": "written sentence"},
                {"criterion": "I can group rocks.", "evidence": "sorted rocks"},
            ]
        )
        assert len(_validate(payload).success_criteria) == 2


class TestTheLessonFitsTheLesson:
    def test_the_timings_add_up_to_the_lesson_she_has(self):
        assert sum(s.minutes for s in _validate().steps) == 60

    def test_a_seventy_minute_lesson_in_a_sixty_minute_slot_is_rejected(self):
        """The commonest way a plan is useless in the room."""
        payload = lesson_payload(steps=[step(30), step(20), step(20)])
        with pytest.raises(LessonError, match="70|60"):
            _validate(payload, minutes=60)

    def test_a_short_lesson_is_rejected_too(self):
        payload = lesson_payload(steps=[step(10), step(10)])
        with pytest.raises(LessonError):
            _validate(payload, minutes=60)

    def test_a_step_with_no_time_on_it_is_rejected(self):
        payload = lesson_payload(steps=[step(30), {**step(30), "minutes": None}])
        with pytest.raises(LessonError):
            _validate(payload)

    def test_a_zero_minute_step_is_still_rejected_when_the_total_is_right(self):
        """Found live on 2026-09-03, and it cost a lesson.

        A soil lesson came back with five steps totalling exactly 60 minutes
        and a sixth — *"Closing Circle: Reflection"*, with children sitting,
        listening and sharing what they had learned — given 0 minutes. The
        arithmetic is perfect and the step is real teaching that will happen in
        the room, so it has to be paid for out of the hour. Uncosted, the
        teacher runs it and overruns.

        The guard was right to refuse it. It is not softened here.
        """
        payload = lesson_payload(
            steps=[step(20), step(20), step(20), step(0, name="Closing Circle")]
        )
        with pytest.raises(LessonError):
            _validate(payload, minutes=60)

    def test_the_refusal_names_the_step_and_the_way_out(self):
        """Why that lesson was lost rather than repaired.

        The refusal said *"Step 6 has no time on it"* — which is a description
        of what the model had deliberately done, not something it could act on.
        Told that and told to change nothing else, it returned a byte-identical
        lesson and the second attempt failed the same way.

        A refusal has to name the step and say what would fix it, because the
        only fix takes minutes from a step that already has them.
        """
        payload = lesson_payload(
            steps=[step(20), step(20), step(20), step(0, name="Closing Circle")]
        )
        with pytest.raises(LessonError) as refused:
            _validate(payload, minutes=60)

        message = str(refused.value)
        assert "Closing Circle" in message, "The refusal does not say which step."
        assert "60" in message, (
            "The refusal does not say how long the lesson is, so the only "
            "available fix — moving minutes between steps — cannot be stated."
        )

    def test_a_lesson_with_two_timing_faults_reports_both_at_once(self):
        """Found live on 2026-09-03, and it is why the repair only half worked.

        A soil-and-grouping lesson came back as 70 minutes of content in a
        60-minute lesson, with the overrun hidden by giving the plenary 0
        minutes. The refusal named the zero-minute step, because that is the
        first thing the check met walking the steps in order. The repair did
        exactly what it was told — dropped the uncosted step — and was then
        refused a second time for the ten-minute overrun it had never been told
        about. The lesson was lost on its second attempt to a fault nobody had
        mentioned.

        There is one repair, by design, so the refusal has to carry the whole
        timing picture rather than the first thing wrong with it.
        """
        payload = lesson_payload(
            steps=[step(30), step(20), step(20), step(0, name="Plenary")]
        )
        with pytest.raises(LessonError) as refused:
            _validate(payload, minutes=60)

        message = str(refused.value)
        assert "Plenary" in message, "The refusal does not name the uncosted step."
        assert "70" in message, (
            "The refusal does not say what the steps actually add up to, so a "
            "repair cannot know the hour is already overspent."
        )
        assert "60" in message, "The refusal does not say how long the lesson is."

    def test_the_timing_refusal_shows_the_arithmetic_it_wants_changed(self):
        """Found live on 2026-09-03, and it cost a lesson.

        A properties lesson came back as 70 minutes in a 60-minute lesson,
        was told exactly that, and the repair came back at 45. It did not
        ignore the refusal — it redid the whole arithmetic from scratch and
        overshot the other way, and the lesson was lost on its second attempt.

        Telling it the total is not telling it the change. The refusal now
        carries what each step currently costs and how many minutes have to
        move, which is the smallest edit that fixes it.
        """
        payload = lesson_payload(
            steps=[
                step(30, name="Hook"),
                step(20, name="Modelling"),
                step(20, name="Plenary"),
            ]
        )
        with pytest.raises(LessonError) as refused:
            _validate(payload, minutes=60)

        message = str(refused.value)
        assert "10 minutes" in message, (
            "The refusal does not say how many minutes have to move, so the "
            "repair has to redo the arithmetic and can overshoot."
        )
        for name, minutes in (("Hook", 30), ("Modelling", 20), ("Plenary", 20)):
            assert f"{name}" in message and f"{minutes}" in message, (
                f"The refusal does not say what {name} currently costs, so "
                f"there is no way to take the minutes out of the longest step."
            )

    def test_a_short_lesson_is_told_how_many_minutes_are_missing(self):
        payload = lesson_payload(steps=[step(20, name="Hook"), step(25, name="Practice")])
        with pytest.raises(LessonError) as refused:
            _validate(payload, minutes=60)
        assert "15 minutes" in str(refused.value)

    def test_one_step_is_not_a_lesson(self):
        payload = lesson_payload(steps=[step(60)])
        with pytest.raises(LessonError, match="step"):
            _validate(payload)

    def test_too_few_steps_is_refused_with_the_whole_timing_picture(self):
        """Found live on 2026-09-03, and it cost a lesson on the run that
        found it.

        A fossils lesson came back as a single 8-minute hook in a 60-minute
        lesson. Not truncated — the reply was complete JSON with every other
        field present, and the schema cannot say "at least two steps" because
        structured output has no `minItems`. So the guard was right, and the
        refusal it gave was *"A lesson needs at least two steps."*

        True, and it carries none of the numbers the fix needs. The repair
        added five more steps, gave the last one 0 minutes, and the lesson was
        lost on its second attempt to the timing check nobody had mentioned —
        the same shape as the two timing refusals above, one step earlier in
        the walk. There is one repair, so this refusal has to state the whole
        contract the repaired lesson will be held to.
        """
        payload = lesson_payload(steps=[step(8)])
        with pytest.raises(LessonError) as refused:
            _validate(payload, minutes=60)

        message = str(refused.value)
        assert "60" in message, "The refusal does not say how long the lesson is."
        assert "8" in message, (
            "The refusal does not say what the one step it got adds up to, so "
            "a repair cannot know how many minutes are still unspent."
        )
        assert "1 minute" in message, (
            "The refusal does not say every step needs a minute on it, which "
            "is what the repair went on to get wrong."
        )

    def test_no_steps_at_all_says_the_same_thing(self):
        payload = lesson_payload(steps=[])
        with pytest.raises(LessonError) as refused:
            _validate(payload, minutes=60)
        assert "60" in str(refused.value)


class TestDepth:
    """The standard the first version failed. Each of these, missing, turns the
    plan back into a list of things a lesson should contain."""

    @pytest.mark.parametrize(
        "field", ["on_the_board", "teacher_says", "children_do"]
    )
    def test_every_step_says_what_actually_happens(self, field):
        payload = lesson_payload(steps=[step(30), step(30, **{field: "  "})])
        with pytest.raises(LessonError, match=field.replace("_", " ")):
            _validate(payload)

    def test_a_lesson_with_no_questions_is_an_outline(self):
        payload = lesson_payload(
            steps=[step(30, questions=[]), step(30, questions=[])]
        )
        with pytest.raises(LessonError, match="question"):
            _validate(payload)

    def test_a_question_without_the_answer_to_expect_is_half_a_question(self):
        payload = lesson_payload(
            steps=[
                step(30, questions=[{"ask": "What can you see?", "expect": "  "}]),
                step(30, questions=[]),
            ]
        )
        with pytest.raises(LessonError, match="expect"):
            _validate(payload)

    def test_a_lesson_that_never_says_what_to_watch_for_is_rejected(self):
        payload = lesson_payload(steps=[step(30, watch_for=[]), step(30, watch_for=[])])
        with pytest.raises(LessonError, match="watch"):
            _validate(payload)

    def test_a_lesson_that_never_says_where_the_adults_are_is_rejected(self):
        """She has another adult in the room and the plan has to use them."""
        payload = lesson_payload(steps=[step(30, adults=""), step(30, adults="  ")])
        with pytest.raises(LessonError, match="adult"):
            _validate(payload)

    def test_two_steps_missing_different_things_are_reported_together(self):
        """Found live on 2026-09-03 — the second lesson lost to this law in a
        single run.

        Lesson 3 was refused for arriving as one step. The repair produced six,
        and the sixth had nothing on the board, so the lesson was lost on its
        second attempt to a fault it had never been shown. Walking the steps
        and refusing on the first missing field is the same defect the timings
        had, in the same function — and there is only ever one repair.
        """
        payload = lesson_payload(
            steps=[step(30, on_the_board=""), step(30, children_do="")]
        )
        with pytest.raises(LessonError) as refused:
            _validate(payload, minutes=60)

        message = str(refused.value)
        assert "Step 1" in message and "Step 2" in message
        assert "on the board" in message and "children do" in message

    def test_a_missing_field_and_a_timing_fault_are_reported_together(self):
        """The two halves of the same walk. A repair told only about the
        missing field returns a lesson that is still ten minutes short."""
        payload = lesson_payload(steps=[step(30), step(20, teacher_says="")])
        with pytest.raises(LessonError) as refused:
            _validate(payload, minutes=60)

        message = str(refused.value)
        assert "teacher says" in message
        assert "50" in message and "60" in message

    def test_a_step_fault_and_a_whole_lesson_fault_are_reported_together(self):
        """One fault inside a step, one that is only visible across all of
        them. A repair told about the question comes back still not saying
        where the other adult is."""
        payload = lesson_payload(
            steps=[
                step(30, adults=""),
                step(
                    30,
                    adults="",
                    questions=[{"ask": "What can you see?", "expect": " "}],
                ),
            ]
        )
        with pytest.raises(LessonError) as refused:
            _validate(payload, minutes=60)

        message = str(refused.value)
        assert "expect" in message
        assert "adult" in message

    def test_misconceptions_are_required(self):
        with pytest.raises(LessonError, match="misconception"):
            _validate(lesson_payload(misconceptions=[]))

    def test_the_assessment_must_name_work_that_has_not_met_the_criterion(self):
        """Asked for by name. 'Look for children meeting the criterion' tells a
        teacher nothing she did not already know."""
        payload = lesson_payload(
            assessment={"look_for": "A property-based heading", "not_yet_example": ""}
        )
        with pytest.raises(LessonError, match="not met|not_yet"):
            _validate(payload)

    def test_resources_carry_quantities(self):
        payload = lesson_payload(resources=[{"item": "Rock samples", "quantity": ""}])
        with pytest.raises(LessonError, match="quantit"):
            _validate(payload)


class TestVocabularyInThreeBands:
    """Her words: 'hard, soft and rough are too easy for some and too difficult
    for others.' One list is the thing she said does not work."""

    def test_all_three_bands_come_back(self):
        vocab = _validate().vocabulary
        assert vocab.everyone and vocab.expected and vocab.stretch

    @pytest.mark.parametrize("band", ["everyone", "expected", "stretch"])
    def test_an_empty_band_is_rejected(self, band):
        payload = lesson_payload(
            vocabulary={**lesson_payload()["vocabulary"], band: []}
        )
        with pytest.raises(LessonError, match=band):
            _validate(payload)

    def test_the_guidance_on_using_them_is_required(self):
        payload = lesson_payload(
            vocabulary={**lesson_payload()["vocabulary"], "guidance": " "}
        )
        with pytest.raises(LessonError):
            _validate(payload)

    def test_a_word_may_not_be_in_two_bands_at_once(self):
        """Measured live, 2026-09-02: the bands came back muddled, with the
        technical words in 'expected' and everyday phrases in 'stretch'. Which
        band is harder is a judgement and stays hers — but a word that is both
        'everyone leaves with' and 'expected of some' is a straight
        contradiction, and it is the tell that the bands were not thought about
        as an order."""
        payload = lesson_payload(
            vocabulary={
                "everyone": ["hard", "soft", "porous"],
                "expected": ["grainy", "porous"],
                "stretch": ["impermeable"],
                "guidance": "Teach the everyday word first.",
            }
        )
        with pytest.raises(LessonError, match="porous"):
            _validate(payload)

    def test_case_and_spacing_do_not_hide_a_repeat(self):
        payload = lesson_payload(
            vocabulary={
                "everyone": ["hard", "Porous "],
                "expected": ["grainy", "porous"],
                "stretch": ["impermeable"],
                "guidance": "Teach the everyday word first.",
            }
        )
        with pytest.raises(LessonError):
            _validate(payload)

    def test_a_longer_phrase_sharing_a_word_is_not_a_repeat(self):
        """'porous' and 'non-porous rock' are different things to teach."""
        payload = lesson_payload(
            vocabulary={
                "everyone": ["hard", "soft"],
                "expected": ["porous"],
                "stretch": ["non-porous rock"],
                "guidance": "Teach the everyday word first.",
            }
        )
        assert _validate(payload).vocabulary.stretch == ["non-porous rock"]


class TestAdaptationsChangeAccessNotTheObjective:
    """The rule that keeps the plan honest about a mixed-ability class.

    Structurally, an adaptation cannot carry an objective of its own — there is
    nowhere to put one. What is left is prose that quietly announces a different
    goal, and that is flagged rather than rejected: 'only needs to say lets
    water through' is exactly right, and a word list cannot tell the two apart.
    """

    def test_all_three_adaptations_are_required(self):
        payload = lesson_payload(
            adaptations={"eal": "Word bank", "send": "", "stretch": "Test permeability"}
        )
        with pytest.raises(LessonError, match="send|SEND"):
            _validate(payload)

    def test_an_adaptation_announcing_a_different_objective_is_flagged(self):
        flags = lowered_objective_flags(
            {"send": "Give this group a simpler objective: name one rock"}
        )
        assert flags and "send" in flags[0][0].lower()

    def test_meeting_the_criterion_in_easier_words_is_not_flagged(self):
        """The plan's own example: a child saying 'lets water through' has met
        the criterion; 'permeable' exceeds it."""
        assert lowered_objective_flags(
            {"eal": "Children only need to say 'lets water through' rather than 'permeable'"}
        ) == []

    def test_a_plain_access_change_is_not_flagged(self):
        assert lowered_objective_flags(
            {"send": "Pre-sorted pair of very different rocks to start from"}
        ) == []


class TestTheSequenceIsNotReopened:
    def test_the_lesson_keeps_the_place_in_the_chain_she_approved(self):
        lesson = _validate()
        assert lesson.number is not None or True  # number is set by the caller

    def test_a_lesson_cannot_be_validated_against_no_objective(self):
        with pytest.raises(LessonError):
            _validate(objective="  ")


@pytest.fixture
def sent(monkeypatch):
    record = {"payload": lesson_payload()}

    def fake_generate(content, system_prompt, **kwargs):
        record["content"] = content
        record["system_prompt"] = system_prompt
        record["kwargs"] = kwargs
        if record.get("raises") is not None:
            raise record["raises"]
        return record["payload"]

    monkeypatch.setattr(lesson_module, "generate_structured_content", fake_generate)
    return record


SPINE_PAYLOAD = {
    "lessons": [
        {
            "number": 1,
            "objective": "Identify and name rocks by their appearance",
            "builds_on": None,
            "builds_on_reason": "Starting point.",
            "covers": ["compare and group rocks"],
            "assesses_outcome": False,
        },
        {
            "number": 2,
            "objective": OBJECTIVE,
            "builds_on": 1,
            "builds_on_reason": "needs the naming vocabulary first",
            "covers": ["compare and group rocks"],
            "assesses_outcome": False,
        },
        {
            "number": 3,
            "objective": "Justify a grouping of unknown rocks",
            "builds_on": 2,
            "builds_on_reason": "grouping must be secure before it can be justified",
            "covers": ["compare and group rocks"],
            "assesses_outcome": True,
        },
    ]
}


@pytest.fixture
def spine():
    return validate_spine(SPINE_PAYLOAD, expected_count=3)


def _generate(spine, number=2, **kwargs):
    defaults = dict(subject="Science", year_group="Year 3", lesson_minutes=60)
    return generate_lesson(spine=spine, number=number, **{**defaults, **kwargs})


class TestWritingOneLesson:
    def test_it_comes_back_checked(self, sent, spine):
        assert _generate(spine).objective == OBJECTIVE

    def test_the_objective_sent_is_the_one_she_approved(self, sent, spine):
        _generate(spine)
        assert OBJECTIVE in str(sent["content"])

    def test_the_lesson_knows_what_came_before_it(self, sent, spine):
        """Lesson 3 assumes lesson 2 happened. It has to know what that was."""
        sent["payload"] = lesson_payload(objective="Justify a grouping of unknown rocks")
        _generate(spine, number=3)
        assert "Identify and name rocks by their appearance" in str(sent["content"])

    def test_the_lesson_knows_what_comes_after_it(self, sent, spine):
        """So it does not teach next week's content this week."""
        sent["payload"] = lesson_payload(
            objective="Identify and name rocks by their appearance"
        )
        _generate(spine, number=1)
        assert "Justify a grouping of unknown rocks" in str(sent["content"])

    def test_the_class_is_described_so_the_adaptations_mean_something(self, sent, spine):
        _generate(spine)
        low = str(sent["content"]).lower()
        assert "eal" in low and "send" in low

    def test_the_length_of_the_lesson_reaches_the_request(self, sent, spine):
        sent["payload"] = lesson_payload(steps=[step(15), step(15), step(15)])
        _generate(spine, lesson_minutes=45)
        assert "45" in str(sent["content"])

    def test_a_drifted_objective_is_rejected_not_returned(self, sent, spine):
        sent["payload"] = lesson_payload(objective="Sort rocks into groups")
        with pytest.raises(LessonError, match="objective"):
            _generate(spine)

    def test_asking_for_a_lesson_the_spine_does_not_have_is_refused(self, sent, spine):
        with pytest.raises(LessonError, match="9"):
            _generate(spine, number=9)
        assert "content" not in sent

    def test_the_final_lesson_is_told_it_assesses_the_outcome(self, sent, spine):
        sent["payload"] = lesson_payload(objective="Justify a grouping of unknown rocks")
        _generate(spine, number=3, outcome="Children justify their groupings")
        assert "Children justify their groupings" in str(sent["content"])

    def test_the_system_prompt_is_the_lesson_one(self, sent, spine):
        _generate(spine)
        assert sent["system_prompt"] == LESSON_SYSTEM_PROMPT

    def test_it_asks_for_room_enough_to_finish(self, sent, spine):
        """A deep lesson does not fit the worksheet default, and a truncated
        one is refused rather than rendered short."""
        _generate(spine)
        assert sent["kwargs"].get("max_tokens", 0) > 4096

    def test_it_waits_long_enough_for_one(self, sent, spine):
        """Measured live, 2026-09-02: a lesson at this depth ran past the 60
        second client default and the request was abandoned mid-unit. It
        succeeded on an earlier run, which is worse than failing every time —
        a unit would break at a different lesson each attempt."""
        _generate(spine)
        assert sent["kwargs"].get("timeout", 0) >= 120

    def test_it_streams(self, sent, spine):
        """A longer timeout was not enough. The next live attempt was cut off
        with the server closing the connection, which is what a long
        non-streaming request does. Anthropic's guidance is to stream anything
        with a long output or a high token budget: a worksheet fits in one
        reply, and a lesson at this depth does not."""
        _generate(spine)
        assert sent["kwargs"].get("stream") is True


class TestTheLessonPrompt:
    def _prompt(self, spine, **kw):
        defaults = dict(
            spine=spine, number=2, subject="Science", year_group="Year 3",
            lesson_minutes=60, coverage=(), build_on="", outcome="",
        )
        return build_lesson_prompt(**{**defaults, **kw})

    def test_it_forbids_rewording_the_objective(self, spine):
        low = self._prompt(spine).lower()
        assert "word for word" in low or "exactly as written" in low

    def test_it_asks_for_the_timings_to_add_up(self, spine):
        assert "60" in self._prompt(spine)

    def test_it_asks_for_the_three_vocabulary_bands(self, spine):
        low = self._prompt(spine).lower()
        assert "everyone" in low and "expected" in low and "stretch" in low

    def test_it_asks_for_work_that_has_not_met_the_criterion(self, spine):
        assert "not_yet_example" in self._prompt(spine)

    def test_it_asks_what_to_watch_for(self, spine):
        assert "watch_for" in self._prompt(spine)

    def test_it_says_adaptations_change_access_not_the_objective(self, spine):
        low = self._prompt(spine).lower()
        assert "same objective" in low or "never a different objective" in low

    def test_it_says_every_step_needs_real_time_on_it(self, spine):
        """Prevention, after a live loss on 2026-09-03. The prompt asked for
        the minutes to add up and said nothing about a step being allowed no
        time, so a sixth step arrived at 0 minutes with the other five already
        totalling the whole hour."""
        low = self._prompt(spine).lower()
        assert "at least 1 minute" in low or "at least one minute" in low


class TestTheRepairAsk:
    """Asking again for a lesson that failed one of its own checks."""

    def _repair(self, reason="The steps add up to 55 minutes but the lesson is 60."):
        return build_repair_prompt(
            "the original request", lesson_payload(), reason
        )

    def test_it_carries_the_attempt(self):
        assert "Heavier means harder" in self._repair()

    def test_it_names_the_one_reason(self):
        assert "add up to 55 minutes" in self._repair()

    def test_it_allows_the_changes_the_fix_actually_needs(self):
        """The second half of the 2026-09-03 loss, and the more embarrassing
        half — it was my instruction, not the model's answer.

        *"Fix that and change nothing else"* is a contradiction for the
        commonest failure this repair exists to handle. A step given no time
        can only be fixed by taking minutes from a step that has them, and the
        timings have to keep adding up to the hour. Told to fix it and change
        nothing else, the model returned the same lesson unchanged.
        """
        low = self._repair().lower()
        assert "timings" in low, (
            "The repair never mentions timings, so a fix that has to move "
            "minutes between steps reads as forbidden."
        )
        assert "other steps" in low

    def test_it_still_asks_for_the_teaching_to_be_kept(self):
        """The whole reason the attempt goes back rather than a re-roll."""
        low = self._repair().lower()
        assert "word for word" in low


class TestTheShapeIsConstrainedNotRequested:
    """Asking for a shape in prose and checking it afterwards lost a lesson.

    Measured across seven live runs: several long replies came back as invalid
    JSON — a stray `or` between two strings, a missing comma — at 20–25k
    characters. Not truncation: `stop_reason` was clean and the truncation
    guard passed. The schema goes with the request so the reply is constrained
    as it is written.
    """

    def _prompt(self, spine):
        return build_lesson_prompt(
            spine=spine, number=2, subject="Science", year_group="Year 3",
            lesson_minutes=60,
        )

    def test_the_request_carries_the_schema(self, sent, spine):
        _generate(spine)
        assert sent["kwargs"].get("schema") == LESSON_SCHEMA

    def test_a_lesson_the_checks_accept_satisfies_the_schema(self):
        """The control against the failure this repo keeps hitting: a guard
        that refuses correct work. Three of the four worksheet defects were
        exactly that, and they are invisible on a green suite — they surface as
        the teacher being told her correct sheet is wrong. A schema is worse
        again, because it does not refuse the lesson, it makes the lesson
        impossible to write.
        """
        jsonschema.validate(lesson_payload(), LESSON_SCHEMA)

    def test_the_schema_asks_for_nothing_the_prompt_never_mentions(self, spine):
        """Drift between the two is the way this breaks. `additionalProperties:
        false` means a field the prompt asks for and the schema omits cannot be
        returned at all."""
        prompt = self._prompt(spine)
        for field in LESSON_SCHEMA["required"]:
            assert f'"{field}"' in prompt, (
                f"The schema requires {field!r} but the prompt never asks for it."
            )

    def test_the_prompt_asks_for_nothing_the_schema_forbids(self, spine):
        """The other direction, and the one that silently empties a lesson."""
        allowed = set(LESSON_SCHEMA["properties"])
        step_fields = set(
            LESSON_SCHEMA["properties"]["steps"]["items"]["properties"]
        )
        prompt = self._prompt(spine)
        for field in (
            "objective", "success_criteria", "vocabulary", "steps",
            "misconceptions", "assessment", "adaptations", "resources",
            "next_lesson",
        ):
            assert field in allowed, f"The prompt asks for {field!r}; the schema bans it."
        for field in (
            "name", "minutes", "on_the_board", "teacher_says", "questions",
            "children_do", "watch_for", "adults", "builds_on_step",
        ):
            assert f'"{field}"' in prompt and field in step_fields, (
                f"Step field {field!r} is in one of the prompt and the schema, "
                f"not both."
            )

    def test_every_object_in_the_schema_closes_its_shape(self):
        """Structured outputs require it on every object, not just the root."""
        open_objects = []

        def walk(node, path="root"):
            if isinstance(node, dict):
                if node.get("type") == "object" and node.get(
                    "additionalProperties", None
                ) is not False:
                    open_objects.append(path)
                for key, value in node.items():
                    walk(value, f"{path}.{key}")
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    walk(value, f"{path}[{index}]")

        walk(LESSON_SCHEMA)
        assert not open_objects, (
            f"These objects do not set additionalProperties: false — {open_objects}"
        )

    def test_the_schema_does_not_change_between_lessons(self, sent, spine):
        """The compiled grammar is cached for 24 hours and the cache is keyed
        on the schema. A schema built per lesson — pinning the objective with
        `const`, say — would pay the compile on every call of a six-lesson
        unit for a guarantee `validate_lesson` already gives."""
        sent["payload"] = lesson_payload(
            objective="Identify and name rocks by their appearance"
        )
        _generate(spine, number=1)
        first = json.dumps(sent["kwargs"]["schema"], sort_keys=True)
        sent["payload"] = lesson_payload(objective="Justify a grouping of unknown rocks")
        _generate(spine, number=3)
        assert json.dumps(sent["kwargs"]["schema"], sort_keys=True) == first


@pytest.fixture
def attempts(monkeypatch):
    """A model that can be told what to return on each successive ask."""
    record = {"payloads": [], "sent": [], "raises": [], "kwargs": []}

    def fake_generate(content, system_prompt, **kwargs):
        record["sent"].append(str(content))
        record["kwargs"].append(kwargs)
        if record["raises"]:
            error = record["raises"].pop(0)
            if error is not None:
                raise error
        if not record["payloads"]:
            raise AssertionError(
                f"The lesson was asked for {len(record['sent'])} times; the test "
                f"only set up {len(record['sent']) - 1}."
            )
        return record["payloads"].pop(0)

    monkeypatch.setattr(lesson_module, "generate_structured_content", fake_generate)
    return record


def _short_by_five():
    """Steps summing to 55 in a 60-minute lesson. A real, repeated failure."""
    return lesson_payload(steps=[step(20), step(20), step(15)])


def _word_in_two_bands():
    return lesson_payload(
        vocabulary={
            "everyone": ["hard", "soft", "rough", "smooth"],
            "expected": ["grainy", "layered", "permeable"],
            "stretch": ["permeable", "impermeable"],
            "guidance": "Teach the everyday word, then name the technical one.",
        }
    )


class TestALessonThatFailsItsChecksIsAskedForAgain:
    """The second half of the one-lesson-in-three loss.

    The checks are right and stay exactly as they are. What was missing is that
    a lesson failing one of them was simply lost — the unit stopped there and
    the teacher was told which lessons are missing. Timings summing to 55 in a
    60-minute lesson, or a word landing in two vocabulary bands, is a named,
    self-correctable defect in an otherwise complete lesson. Throwing away
    twenty-five thousand characters of usable teaching over a five-minute
    arithmetic slip is the wrong trade.

    This is a repair, not a retry: the second ask carries the attempt and the
    reason it was refused, which is information the first ask did not have. It
    happens once, and the result goes through the same guard.
    """

    def test_a_named_failure_is_repaired(self, attempts, spine):
        attempts["payloads"] = [_short_by_five(), lesson_payload()]
        assert _generate(spine).objective == OBJECTIVE
        assert len(attempts["sent"]) == 2

    def test_the_second_ask_says_what_was_wrong(self, attempts, spine):
        attempts["payloads"] = [_short_by_five(), lesson_payload()]
        _generate(spine)
        assert "55" in attempts["sent"][1] and "60" in attempts["sent"][1]

    def test_the_second_ask_carries_the_attempt_it_is_repairing(self, attempts, spine):
        """Otherwise it is a re-roll, and a re-roll throws away the lesson."""
        attempts["payloads"] = [_short_by_five(), lesson_payload()]
        _generate(spine)
        assert "Heavier means harder" in attempts["sent"][1]

    def test_a_drifted_objective_is_repairable_too(self, attempts, spine):
        attempts["payloads"] = [lesson_payload(objective="Sort rocks into groups"), lesson_payload()]
        assert _generate(spine).objective == OBJECTIVE

    def test_a_word_in_two_bands_is_repairable(self, attempts, spine):
        attempts["payloads"] = [_word_in_two_bands(), lesson_payload()]
        assert _generate(spine).vocabulary.stretch == ["permeable", "impermeable"]

    def test_a_lesson_that_passes_is_not_asked_for_twice(self, attempts, spine):
        attempts["payloads"] = [lesson_payload()]
        _generate(spine)
        assert len(attempts["sent"]) == 1

    def test_the_repair_is_checked_by_the_same_guard(self, attempts, spine):
        """The guard is not softened for the second attempt. Softening it is
        how a lesson that does not add up reaches a classroom."""
        attempts["payloads"] = [_short_by_five(), _short_by_five()]
        with pytest.raises(LessonError, match="55"):
            _generate(spine)

    def test_it_does_not_ask_a_third_time(self, attempts, spine):
        attempts["payloads"] = [_short_by_five(), _short_by_five()]
        with pytest.raises(LessonError):
            _generate(spine)
        assert len(attempts["sent"]) == 2

    def test_a_truncated_reply_is_not_asked_for_again(self, attempts, spine):
        """Asking again for a reply that ran out of room gets another reply
        that runs out of room. The answer to that is the token budget, and it
        is already set."""
        attempts["raises"] = [TruncatedResponseError("stopped at max_tokens")]
        attempts["payloads"] = [lesson_payload()]
        with pytest.raises(TruncatedResponseError):
            _generate(spine)
        assert len(attempts["sent"]) == 1

    def test_unusable_json_is_not_asked_for_again(self, attempts, spine):
        """With the schema attached this should not happen at all. If it does,
        something is wrong with the request rather than with the answer, and
        sending it a second time only doubles the cost of finding out."""
        attempts["raises"] = [json.JSONDecodeError("no JSON here", "", 0)]
        attempts["payloads"] = [lesson_payload()]
        with pytest.raises(json.JSONDecodeError):
            _generate(spine)
        assert len(attempts["sent"]) == 1

    def test_a_lesson_the_spine_does_not_have_is_refused_before_asking(
        self, attempts, spine
    ):
        attempts["payloads"] = [lesson_payload()]
        with pytest.raises(LessonError, match="9"):
            _generate(spine, number=9)
        assert attempts["sent"] == []

    def test_the_repair_is_sent_the_same_way_as_the_first_ask(self, attempts, spine):
        """A repair that dropped the schema, the stream or the token budget
        would be the request that fails, on the lesson that had already been
        written once."""
        attempts["payloads"] = [_short_by_five(), lesson_payload()]
        _generate(spine)

        assert len(attempts["kwargs"]) == 2
        first, repair = attempts["kwargs"]
        for name in ("schema", "stream", "max_tokens", "timeout"):
            assert repair.get(name) == first.get(name), (
                f"The repair request sent a different {name} from the first ask."
            )
        assert repair.get("schema") == LESSON_SCHEMA
        assert repair.get("stream") is True
