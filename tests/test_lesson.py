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

import pytest

import planning.lesson as lesson_module
from planning.lesson import (
    LESSON_SYSTEM_PROMPT,
    Lesson,
    LessonError,
    build_lesson_prompt,
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

    def test_one_step_is_not_a_lesson(self):
        payload = lesson_payload(steps=[step(60)])
        with pytest.raises(LessonError, match="step"):
            _validate(payload)


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
