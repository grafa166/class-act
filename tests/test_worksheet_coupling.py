"""The worksheet is built from the lesson, and has to evidence it.

This is the headline feature and the last handover in the chain. The spine's
objective is checked verbatim into the lesson; the lesson's objective is checked
verbatim into the worksheet; so the plan, the sheet and the child's book agree,
and no step in between is allowed to reword anything.

Two guarantees, both structural:

**Nothing is re-derived.** The objective and the success criteria are the
teacher's, word for word. Not similar, not improved, not a second AI's
paraphrase. A criterion that came back reworded is rejected, as is one that went
missing and one that was invented.

**Every criterion is actually evidenced.** The sheet must name, for each
criterion, the part of it that produces the evidence — and must *quote the
instruction*, which is then checked against the worksheet itself. That check is
the one with teeth. A claim is cheap: the same shape of defect already shipped
once on the unit spine, where coverage was attached to a lesson that never
taught it. A quote can be verified against the artefact, and a quote that
appears nowhere but in the claim is exactly the fabrication being caught.

None of these tests touch the network.
"""

import pytest

import planning.worksheet as worksheet_module
from llm.validation import WorksheetContentError
from planning.lesson import validate_lesson
from planning.worksheet import (
    WORKSHEET_SYSTEM_PROMPT,
    CoupledWorksheet,
    WorksheetCouplingError,
    build_worksheet_prompt,
    generate_worksheet_for_lesson,
    repeated_task_shapes,
    validate_coupled_worksheet,
)

OBJECTIVE = "Group rocks by their physical properties"

CRITERION_ONE = "I can describe two rocks using property words."
CRITERION_TWO = "I can put rocks into groups and say what the group has in common."

INSTRUCTION_ONE = "Write two property words for each rock in the table."
INSTRUCTION_TWO = "Sort the six rocks into groups and write a heading for each group."


def step(minutes=20, **overrides):
    base = {
        "name": "Modelling",
        "minutes": minutes,
        "on_the_board": "Two rocks, and the words hard / soft / rough / smooth",
        "teacher_says": "Watch me. I am going to pick one word for this rock.",
        "questions": [
            {"ask": "Which word fits this rock?", "expect": "rough — you can feel the grains"}
        ],
        "children_do": "Talk to their partner and agree one word for the second rock",
        "watch_for": [
            {"wrong": "Children say 'nice' instead of a property", "respond": "Point at the word bank"}
        ],
        "adults": "TA sits with the four children on the back table",
        "builds_on_step": "The hook gave them the words; this shows how to use one",
    }
    base.update(overrides)
    return base


def a_lesson(**overrides):
    """A checked lesson, since a worksheet is only ever built from one."""
    payload = {
        "objective": OBJECTIVE,
        "success_criteria": [
            {"criterion": CRITERION_ONE, "evidence": "completed comparison table"},
            {"criterion": CRITERION_TWO, "evidence": "sorted rocks stuck in with a heading"},
        ],
        "vocabulary": {
            "everyone": ["hard", "soft", "rough", "smooth"],
            "expected": ["grainy", "layered", "absorbent"],
            "stretch": ["permeable", "impermeable"],
            "guidance": "Teach the everyday word, then name the technical one beside it.",
        },
        "steps": [step(20), step(20, name="Practice"), step(20, name="Plenary")],
        "misconceptions": [
            {"misconception": "Heavier means harder", "why": "Both feel physical", "address": "Chalk vs granite"}
        ],
        "assessment": {
            "look_for": "A group heading that names a property rather than a colour",
            "not_yet_example": "Three rocks grouped under 'nice ones'",
        },
        "adaptations": {
            "eal": "Word bank with a photograph beside each property word",
            "send": "Pre-sorted pair of very different rocks to start from",
            "stretch": "Offer permeable and ask them to test it with a pipette",
        },
        "resources": [{"item": "Rock samples", "quantity": "6 sets of 4"}],
        "next_lesson": "Testing hardness by scratching",
    }
    payload.update(overrides)
    return validate_lesson(payload, expected_objective=payload["objective"], lesson_minutes=60)


def worksheet_payload(**overrides):
    """What Claude sends back for a cloze sheet built from that lesson."""
    base = {
        "title": "Rock Detectives",
        "objective": OBJECTIVE,
        "success_criteria": [CRITERION_ONE, CRITERION_TWO],
        "sections": [
            {
                "title": "Part 1 — Describing",
                "instructions": INSTRUCTION_ONE,
                "sentences": [
                    {
                        "pieces": [
                            {"type": "text", "text": "Granite feels "},
                            {"type": "blank", "answer": "rough", "hint": "not smooth"},
                            {"type": "text", "text": " when you touch it."},
                        ]
                    }
                ],
            },
            {
                "title": "Part 2 — Grouping",
                "instructions": INSTRUCTION_TWO,
                "sentences": [
                    {
                        "pieces": [
                            {"type": "text", "text": "My group is called "},
                            {"type": "blank", "answer": "rough rocks", "hint": "a property"},
                            {"type": "text", "text": "."},
                        ]
                    }
                ],
            },
        ],
        "word_bank": {"words": ["hard", "soft", "rough", "smooth", "grainy"]},
        "evidence": [
            {
                "criterion": CRITERION_ONE,
                "where": "Part 1 — Describing",
                "quote": INSTRUCTION_ONE,
                "pupil_writes": "Two property words in each row of the table",
            },
            {
                "criterion": CRITERION_TWO,
                "where": "Part 2 — Grouping",
                "quote": INSTRUCTION_TWO,
                "pupil_writes": "A heading naming the property each group shares",
            },
        ],
    }
    base.update(overrides)
    return base


def _validate(payload=None, lesson=None, worksheet_type="cloze"):
    return validate_coupled_worksheet(
        payload if payload is not None else worksheet_payload(),
        lesson=lesson if lesson is not None else a_lesson(),
        worksheet_type=worksheet_type,
    )


# ── The objective ────────────────────────────────────────────────────────────


class TestTheObjectiveIsTheLessons:
    """The whole product rests on this one string surviving three handovers."""

    def test_the_lessons_objective_comes_back_word_for_word(self):
        assert _validate().objective == OBJECTIVE

    def test_a_reworded_objective_is_rejected(self):
        payload = worksheet_payload(objective="Sort rocks by their physical properties")
        with pytest.raises(WorksheetCouplingError, match="objective"):
            _validate(payload)

    def test_even_a_better_objective_is_rejected(self):
        payload = worksheet_payload(
            objective="Group rocks by their physical properties and explain why"
        )
        with pytest.raises(WorksheetCouplingError, match="objective"):
            _validate(payload)

    def test_a_missing_objective_is_rejected(self):
        payload = worksheet_payload()
        del payload["objective"]
        with pytest.raises(WorksheetCouplingError, match="objective"):
            _validate(payload)

    def test_surrounding_whitespace_is_not_a_difference(self):
        assert _validate(worksheet_payload(objective=f"  {OBJECTIVE}  ")).objective == OBJECTIVE


# ── The success criteria ─────────────────────────────────────────────────────


class TestTheCriteriaAreTheLessons:
    def test_they_come_back_word_for_word(self):
        sheet = _validate()
        assert [c.criterion for c in sheet.success_criteria] == [CRITERION_ONE, CRITERION_TWO]

    def test_a_reworded_criterion_is_rejected(self):
        payload = worksheet_payload(
            success_criteria=["I can describe two rocks using describing words.", CRITERION_TWO]
        )
        with pytest.raises(WorksheetCouplingError, match="criteri"):
            _validate(payload)

    def test_a_dropped_criterion_is_rejected(self):
        payload = worksheet_payload(success_criteria=[CRITERION_ONE])
        with pytest.raises(WorksheetCouplingError, match="criteri"):
            _validate(payload)

    def test_the_sheet_prints_hers_even_if_it_did_not_echo_them_back(self):
        """Three times live, a word-bank sheet came back with no success
        criteria at all. They are hers, and the sheet prints hers — so the
        echo is worth checking when it is offered and worth nothing when it
        is not. What the sheet was actually built to is checked by the
        evidence, below, which came back every time.
        """
        payload = worksheet_payload()
        del payload["success_criteria"]
        sheet = _validate(payload)
        assert [c.criterion for c in sheet.success_criteria] == [
            CRITERION_ONE, CRITERION_TWO
        ]
        assert sheet.content["success_criteria"] == [CRITERION_ONE, CRITERION_TWO]

    def test_a_criterion_still_has_to_be_evidenced_when_the_echo_is_missing(self):
        """The guard that actually protects the child's book."""
        payload = worksheet_payload(evidence=[worksheet_payload()["evidence"][0]])
        del payload["success_criteria"]
        with pytest.raises(WorksheetCouplingError, match="[Nn]othing on the sheet"):
            _validate(payload)

    def test_a_reworded_criterion_in_the_evidence_is_rejected_either_way(self):
        payload = worksheet_payload()
        del payload["success_criteria"]
        payload["evidence"][0]["criterion"] = "I can describe rocks with good words."
        with pytest.raises(WorksheetCouplingError, match="not one of"):
            _validate(payload)

    def test_an_invented_criterion_is_rejected(self):
        """An extra one is not a bonus. She approved a list."""
        payload = worksheet_payload(
            success_criteria=[CRITERION_ONE, CRITERION_TWO, "I can name three types of rock."]
        )
        with pytest.raises(WorksheetCouplingError, match="criteri"):
            _validate(payload)

    def test_reordering_is_not_a_rewording_and_her_order_is_restored(self):
        """The sheet prints them in the order she approved, whatever came back."""
        payload = worksheet_payload(success_criteria=[CRITERION_TWO, CRITERION_ONE])
        sheet = _validate(payload)
        assert [c.criterion for c in sheet.success_criteria] == [CRITERION_ONE, CRITERION_TWO]
        assert sheet.content["success_criteria"] == [CRITERION_ONE, CRITERION_TWO]

    def test_the_evidence_each_criterion_names_is_carried_across(self):
        sheet = _validate()
        assert sheet.success_criteria[0].evidence == "completed comparison table"


# ── The evidence ─────────────────────────────────────────────────────────────


class TestEveryCriterionIsEvidenced:
    """A worksheet that produces no evidence for a criterion is rejected."""

    def test_each_criterion_names_the_part_that_evidences_it(self):
        sheet = _validate()
        assert {claim.criterion for claim in sheet.evidence} == {CRITERION_ONE, CRITERION_TWO}

    def test_a_criterion_nothing_evidences_is_rejected(self):
        payload = worksheet_payload(evidence=[worksheet_payload()["evidence"][0]])
        with pytest.raises(WorksheetCouplingError, match="[Nn]othing on the sheet"):
            _validate(payload)

    def test_no_evidence_at_all_is_rejected(self):
        payload = worksheet_payload(evidence=[])
        with pytest.raises(WorksheetCouplingError):
            _validate(payload)

    def test_evidence_for_a_criterion_the_lesson_never_set_is_rejected(self):
        claims = worksheet_payload()["evidence"]
        claims.append(
            {
                "criterion": "I can name three types of rock.",
                "where": "Part 1 — Describing",
                "quote": INSTRUCTION_ONE,
                "pupil_writes": "The three names",
            }
        )
        with pytest.raises(WorksheetCouplingError, match="not one of"):
            _validate(worksheet_payload(evidence=claims))

    def test_a_criterion_the_child_records_nothing_for_is_rejected(self):
        """Reading something is not evidence of having met a criterion."""
        claims = worksheet_payload()["evidence"]
        claims[1]["pupil_writes"] = ""
        with pytest.raises(WorksheetCouplingError, match="records nothing"):
            _validate(worksheet_payload(evidence=claims))


class TestTheQuoteIsCheckedAgainstTheSheet:
    """The claim is cheap; the quote is the part a program can verify.

    Coverage attached to a lesson that never taught it is the same defect one
    layer up, and it was found live rather than by a test. Here the claim names
    a quote, and the quote has to be in the worksheet.
    """

    def test_a_quote_that_is_really_on_the_sheet_passes(self):
        assert _validate().evidence[0].quote == INSTRUCTION_ONE

    def test_a_quote_that_appears_nowhere_on_the_sheet_is_rejected(self):
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "Draw a picture of each rock and label it carefully."
        with pytest.raises(WorksheetCouplingError, match="does not appear"):
            _validate(worksheet_payload(evidence=claims))

    def test_a_quote_only_in_the_claim_itself_is_rejected(self):
        """The control on the check.

        If the sheet were searched with the claims still in it, every quote
        would match itself and the check would assert nothing at all.
        """
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "Invent a brand new instruction that is not on the sheet."
        claims[0]["where"] = "Invent a brand new instruction that is not on the sheet."
        with pytest.raises(WorksheetCouplingError, match="does not appear"):
            _validate(worksheet_payload(evidence=claims))

    def test_a_quote_too_short_to_be_a_task_is_rejected(self):
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "the"
        with pytest.raises(WorksheetCouplingError, match="too short"):
            _validate(worksheet_payload(evidence=claims))

    def test_a_missing_quote_is_rejected(self):
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = ""
        with pytest.raises(WorksheetCouplingError):
            _validate(worksheet_payload(evidence=claims))

    def test_a_sentence_assembled_from_pieces_can_be_quoted(self):
        """Found live, 2026-09-02, and it refused correct work.

        A cloze, word-bank or sentence-builder sheet stores a sentence as
        fragments with the gaps between them. The child reads the whole
        sentence, so quoting the whole sentence is quoting the sheet — but
        no single fragment contains it.
        """
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "Granite feels rough when you touch it."
        assert _validate(worksheet_payload(evidence=claims)).evidence[0].quote

    def test_the_same_sentence_can_be_quoted_with_the_gaps_left_blank(self):
        """The other way it came back live: blanks written as underscores."""
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "Granite feels ___ when you touch it."
        assert _validate(worksheet_payload(evidence=claims)).evidence[0].quote

    def test_how_wide_the_gap_is_drawn_is_not_a_difference(self):
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "Granite feels _________ when you touch it."
        assert _validate(worksheet_payload(evidence=claims)).evidence[0].quote

    def test_assembling_the_pieces_does_not_invent_a_sentence_across_two_tasks(self):
        """The end of one task and the start of the next is not a sentence."""
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "when you touch it. My group is called rough rocks."
        with pytest.raises(WorksheetCouplingError, match="does not appear"):
            _validate(worksheet_payload(evidence=claims))

    def test_a_quote_spanning_two_prompts_printed_together_is_accepted(self):
        """Found live, 2026-09-02, and it refused correct work.

        An investigation sheet prints its conclusion prompts one under the
        other, and the model quoted two of them the way the child meets them.
        Both are really on the sheet, so the sheet really does produce the
        evidence.
        """
        payload = {
            "title": "Sorting unknown rocks",
            "objective": OBJECTIVE,
            "success_criteria": [CRITERION_ONE, CRITERION_TWO],
            "conclusion_prompts": [
                "The property I chose to sort by was ___ because...",
                "The rocks in my first group are all ___ and I know because...",
            ],
            "evidence": [
                {
                    "criterion": CRITERION_ONE,
                    "where": "Conclusion",
                    "quote": "The property I chose to sort by was ___ because...",
                    "pupil_writes": "The property and the reason",
                },
                {
                    "criterion": CRITERION_TWO,
                    "where": "Conclusion",
                    "quote": (
                        "The property I chose to sort by was ___ because... "
                        "The rocks in my first group are all ___ and I know because..."
                    ),
                    "pupil_writes": "The shared property of the group",
                },
            ],
        }
        sheet = _validate(payload, worksheet_type="investigation")
        assert len(sheet.evidence) == 2

    def test_a_quote_stitched_from_two_unrelated_parts_is_still_rejected(self):
        """Two prompts printed together is one thing; the end of one task
        welded to the start of an unrelated one is a fabrication."""
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "Rock Detectives Write two property words for each rock"
        with pytest.raises(WorksheetCouplingError, match="does not appear"):
            _validate(worksheet_payload(evidence=claims))

    def test_a_sentence_in_a_cloze_paragraph_can_be_quoted(self):
        """Found live, 2026-09-02, and it refused correct work.

        A cloze passage is stored as `paragraphs` — a list of lists of pieces,
        with no `pieces` key to recognise it by. Every quote on a correct sheet
        was refused because none of it was ever assembled.
        """
        payload = {
            "title": "Planet Terra",
            "objective": OBJECTIVE,
            "success_criteria": [CRITERION_ONE, CRITERION_TWO],
            "word_bank": {"words": ["soil", "rough"]},
            "sections": [
                {
                    "title": "Touchdown",
                    "paragraphs": [
                        [
                            {"type": "text", "text": "The ground is covered in "},
                            {"type": "blank", "answer": "soil", "hint": "brown stuff"},
                            {"type": "text", "text": " and the pieces feel rough."},
                        ]
                    ],
                }
            ],
            "evidence": [
                {
                    "criterion": criterion,
                    "where": "Touchdown",
                    "quote": "The ground is covered in ___ and the pieces feel rough.",
                    "pupil_writes": "The missing property word",
                }
                for criterion in (CRITERION_ONE, CRITERION_TWO)
            ],
        }
        assert len(_validate(payload).evidence) == 2

    def test_a_gap_drawn_as_a_list_of_choices_is_still_a_gap(self):
        """Found live: the model drew a blank as the choices a child picks
        between. How a gap is drawn is not what the sentence says."""
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "Granite feels [rough/smooth/shiny] when you touch it."
        assert _validate(worksheet_payload(evidence=claims)).evidence[0].quote

    def test_a_quote_that_is_almost_all_gaps_is_rejected(self):
        """The teeth. Blanks match anything, so a quote made mostly of them
        would make the check assert nothing."""
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "___ [a word] ___ [another word] ___ [and another]"
        with pytest.raises(WorksheetCouplingError, match="too short"):
            _validate(worksheet_payload(evidence=claims))

    def test_gaps_do_not_let_a_sentence_be_quoted_back_to_front(self):
        """Both stretches are on the sheet, in that one task — but in the other
        order, so the quote is not what the sheet says."""
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "when you touch it. ___ Granite feels"
        with pytest.raises(WorksheetCouplingError, match="does not appear"):
            _validate(worksheet_payload(evidence=claims))

    def test_gaps_do_not_let_two_unrelated_tasks_be_welded_together(self):
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "My group is called ___ Granite feels ___ when you touch it."
        with pytest.raises(WorksheetCouplingError, match="does not appear"):
            _validate(worksheet_payload(evidence=claims))

    def test_spacing_and_case_do_not_hide_a_real_match(self):
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "  write TWO property words   for each rock in the table.  "
        assert _validate(worksheet_payload(evidence=claims)).evidence[0].criterion


# ── The sheet still has to render ────────────────────────────────────────────


class TestTheSheetStillRenders:
    def test_a_sheet_the_generator_cannot_build_is_rejected(self):
        payload = worksheet_payload()
        del payload["sections"]
        with pytest.raises(WorksheetContentError):
            _validate(payload)

    def test_the_content_handed_on_is_the_generators_shape(self):
        sheet = _validate()
        assert sheet.content["title"] == "Rock Detectives"
        assert sheet.worksheet_type == "cloze"


# ── The prompt ───────────────────────────────────────────────────────────────


class TestTheWorksheetPrompt:
    def _prompt(self, **kwargs):
        defaults = dict(
            lesson=a_lesson(),
            worksheet_type="cloze",
            subject="Science",
            year_group="Year 3",
        )
        return build_worksheet_prompt(**{**defaults, **kwargs})

    def test_it_carries_the_objective_word_for_word(self):
        assert OBJECTIVE in self._prompt()

    def test_it_forbids_rewording_the_objective(self):
        assert "word for word" in self._prompt().lower()

    def test_it_carries_every_criterion_word_for_word(self):
        prompt = self._prompt()
        assert CRITERION_ONE in prompt and CRITERION_TWO in prompt

    def test_it_carries_the_evidence_each_criterion_names(self):
        assert "completed comparison table" in self._prompt()

    def test_it_forbids_writing_new_criteria(self):
        assert "do not write your own" in self._prompt().lower()

    def test_it_hands_over_the_criteria_as_json_to_copy(self):
        """Found live, 2026-09-02: a word-bank sheet came back with no success
        criteria at all. Described in prose they can be dropped; handed over as
        the literal JSON to copy across, there is nothing to compose.
        """
        prompt = self._prompt()
        assert '"success_criteria": [' in prompt
        assert f'    "{CRITERION_ONE}",' in prompt
        assert f'    "{CRITERION_TWO}"' in prompt

    def test_it_hands_over_the_objective_as_json_to_copy(self):
        assert f'"objective": "{OBJECTIVE}",' in self._prompt()

    def test_the_fields_to_copy_are_the_last_thing_it_says(self):
        """Twice live, a word-bank sheet came back with no success criteria at
        all. They were asked for in the middle, with a paragraph after them
        saying not to put something else in the JSON — so the last word on the
        subject was a prohibition. They go last now, and on their own.
        """
        # `rindex` because the worksheet template above has its own
        # `success_criteria` in the schema it asks for.
        prompt = self._prompt()
        assert prompt.rindex('"success_criteria": [') > prompt.rindex('"evidence": [')

    def test_it_ends_with_a_check_that_nothing_was_left_out(self):
        prompt = self._prompt().lower()
        assert "before you finish" in prompt
        assert prompt.rindex("success_criteria") > prompt.rindex("before you finish")

    def test_it_asks_for_a_quote_from_the_sheet(self):
        assert "quote" in self._prompt().lower()

    def test_it_asks_for_one_part_of_the_sheet_not_a_summary_of_several(self):
        """Found live, 2026-09-02: asked to quote the task, the model summarised
        three sections of a passage into one sentence, silently dropping the
        headings between them. Every sentence was real; the sentence was not.
        """
        prompt = self._prompt().lower()
        assert "one part of the sheet" in prompt
        assert "summar" in prompt

    def test_it_says_reading_is_not_evidence(self):
        assert "record" in self._prompt().lower()

    def test_it_says_to_change_the_sheet_rather_than_the_criterion(self):
        assert "change the sheet" in self._prompt().lower()

    def test_it_carries_what_earlier_lessons_established(self):
        """So the sheet assumes only what has actually been taught."""
        prompt = self._prompt(earlier_objectives=["Identify and name rocks by their appearance"])
        assert "Identify and name rocks by their appearance" in prompt

    def test_the_first_lesson_of_a_unit_assumes_nothing(self):
        assert "assume nothing" in self._prompt().lower()


# ── Making one ───────────────────────────────────────────────────────────────


@pytest.fixture
def sent(monkeypatch):
    record = {"payload": worksheet_payload()}

    def fake_generate(content, system_prompt, **kwargs):
        record["content"] = content
        record["system_prompt"] = system_prompt
        record["kwargs"] = kwargs
        return record["payload"]

    monkeypatch.setattr(worksheet_module, "generate_structured_content", fake_generate)
    return record


def _make(**kwargs):
    defaults = dict(
        lesson=a_lesson(),
        worksheet_type="cloze",
        subject="Science",
        year_group="Year 3",
    )
    return generate_worksheet_for_lesson(**{**defaults, **kwargs})


class TestMakingTheWorksheet:
    def test_it_comes_back_checked(self, sent):
        assert isinstance(_make(), CoupledWorksheet)

    def test_the_objective_sent_is_the_lessons(self, sent):
        _make()
        assert OBJECTIVE in str(sent["content"])

    def test_a_drifted_objective_is_rejected_not_returned(self, sent):
        sent["payload"] = worksheet_payload(objective="Sort rocks into groups")
        with pytest.raises(WorksheetCouplingError, match="objective"):
            _make()

    def test_a_faked_evidence_claim_is_rejected_not_returned(self, sent):
        claims = worksheet_payload()["evidence"]
        claims[1]["quote"] = "Colour in the rocks using your favourite colours."
        sent["payload"] = worksheet_payload(evidence=claims)
        with pytest.raises(WorksheetCouplingError, match="does not appear"):
            _make()

    def test_the_system_prompt_is_the_coupled_one(self, sent):
        _make()
        assert sent["system_prompt"] == WORKSHEET_SYSTEM_PROMPT

    def test_it_asks_for_room_enough_to_finish(self, sent):
        """The sheet now carries an evidence block as well as the tasks, and a
        truncated reply is refused rather than rendered short."""
        _make()
        assert sent["kwargs"].get("max_tokens", 0) > 4096

    def test_it_streams(self, sent):
        """Anthropic's guidance is to stream anything with a long output or a
        high token budget. The lesson path learned this live."""
        _make()
        assert sent["kwargs"].get("stream") is True

    def test_the_lesson_number_is_kept(self, sent):
        sheet = _make(lesson=a_lesson())
        assert sheet.lesson_number == a_lesson().number

    def test_it_is_labelled_a_draft(self, sent):
        assert "check before teaching" in _make().source.lower()


# ── Across a unit ────────────────────────────────────────────────────────────


class TestTheUnitDoesNotRepeatOneTaskShape:
    """A unit's worksheets must not be the same task six times."""

    def _sheet(self, worksheet_type):
        sheet = _validate()
        return CoupledWorksheet(
            objective=sheet.objective,
            success_criteria=sheet.success_criteria,
            evidence=sheet.evidence,
            content=sheet.content,
            worksheet_type=worksheet_type,
        )

    def test_three_of_the_same_shape_is_flagged(self):
        sheets = [self._sheet("cloze") for _ in range(3)]
        assert repeated_task_shapes(sheets)

    def test_a_mixed_unit_is_not_flagged(self):
        sheets = [self._sheet("cloze"), self._sheet("matching"), self._sheet("cloze")]
        assert not repeated_task_shapes(sheets)

    def test_two_the_same_is_not_yet_a_pattern(self):
        assert not repeated_task_shapes([self._sheet("cloze"), self._sheet("cloze")])

    def test_the_flag_names_the_shape(self):
        (flag,) = repeated_task_shapes([self._sheet("cloze") for _ in range(4)])
        assert "cloze" in flag.lower()
