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

import json

import pytest

import planning.worksheet as worksheet_module
from llm.client import TruncatedResponseError
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
from planning.worksheet_schema import get_worksheet_schema

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

    def test_a_quote_welding_two_neighbouring_fields_is_rejected(self):
        """The control on the search being per task rather than per sheet.

        Every other stitching test here is rejected because of the order the
        pieces happen to come out in, not because each is searched on its own
        — a positive control on 2026-09-03 showed that searching the whole
        sheet as one blob left all of them passing. These two fields are
        genuinely adjacent, so this is the one that pins it.
        """
        payload = {
            "title": "Soil detectives",
            "objective": OBJECTIVE,
            "success_criteria": [CRITERION_ONE, CRITERION_TWO],
            "investigation": {
                "question": "What can we find in a handful of soil?",
                "prediction": "Write what you think you will find in the soil.",
            },
            "evidence": [
                {
                    "criterion": criterion,
                    "where": "Investigation",
                    "quote": (
                        "What can we find in a handful of soil? "
                        "Write what you think you will find in the soil."
                    ),
                    "pupil_writes": "Their prediction",
                }
                for criterion in (CRITERION_ONE, CRITERION_TWO)
            ],
        }
        with pytest.raises(WorksheetCouplingError, match="does not appear"):
            _validate(payload, worksheet_type="investigation")


class TestASentenceAboutTheSheetIsNotAQuoteOfIt:
    """The fourth guard-refuses-correct-work, reproduced from the artefact.

    `live-runs/2026-09-03-010849/10-reply.txt`. An investigation sheet had a
    results-table column headed *"Bits from dead plants and animals we found
    (describe what they look like)"*, the child records in it, and the
    criterion is genuinely evidenced. The quote came back as a sentence
    *about* the column. The guard was right, the sheet was right, and the
    sheet was thrown away.

    Both halves are pinned here. The paraphrase stays refused, because a
    search loose enough to accept it also accepts the fabrication this check
    was built for — a cloze sheet claiming a task sentence that existed
    nowhere but inside its own claim. The column's own heading is accepted,
    because it is what is printed on the sheet. What changes is that the
    refusal now says which of the two to write, and the sheet gets one more
    go rather than being lost.
    """

    HEADING = (
        "Bits from dead plants and animals we found (describe what they look like)"
    )

    def _payload(self, quote):
        return {
            "title": "Soil investigation",
            "objective": OBJECTIVE,
            "success_criteria": [CRITERION_ONE, CRITERION_TWO],
            "method": ["Sort the soil into piles using tweezers."],
            "results_table": {
                "columns": ["Location", self.HEADING],
                "rows": 3,
            },
            "conclusion_prompts": [
                "Explain where the broken rock pieces in soil come from.",
            ],
            "evidence": [
                {
                    "criterion": CRITERION_ONE,
                    "where": "Results table",
                    "quote": quote,
                    "pupil_writes": "What the bits look like",
                },
                {
                    "criterion": CRITERION_TWO,
                    "where": "Conclusion",
                    "quote": "Explain where the broken rock pieces in soil come from.",
                    "pupil_writes": "Their explanation",
                },
            ],
        }

    def test_a_sentence_about_the_column_is_refused(self):
        payload = self._payload(
            "In the 'Bits from dead plants and animals we found' column, "
            "record what these look like."
        )
        with pytest.raises(WorksheetCouplingError, match="does not appear"):
            _validate(payload, worksheet_type="investigation")

    def test_the_columns_own_heading_is_accepted(self):
        """The conforming move, and it was always available — the guard has
        seen this column all along. Measured 2026-09-03."""
        sheet = _validate(self._payload(self.HEADING), worksheet_type="investigation")
        assert sheet.evidence[0].quote == self.HEADING

    def test_the_refusal_names_the_move_that_would_have_worked(self):
        payload = self._payload(
            "In the 'Bits from dead plants and animals we found' column, "
            "record what these look like."
        )
        with pytest.raises(WorksheetCouplingError) as refused:
            _validate(payload, worksheet_type="investigation")
        assert "column heading" in str(refused.value).lower()


# ── What counts as the sheet ─────────────────────────────────────────────────


class TestTheSheetSearchedIsTheTasks:
    """The quote is checked against the tasks, not against the header.

    The claims are already left out, because searching them would let every
    quote match itself. The objective, the criteria and the title are the same
    hole one step further out: they are printed at the top of the sheet, none
    of them is something a child does, and a quote that matches nothing but one
    of them proves nothing about whether the sheet produces any evidence.

    Found reading the code on 2026-09-03 while confirming a different
    diagnosis, not live. It tightens the check; it does not loosen it.
    """

    def test_a_quote_matching_only_a_printed_criterion_is_rejected(self):
        """A criterion is what the child has to show, not a task that shows it."""
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = CRITERION_TWO
        with pytest.raises(WorksheetCouplingError, match="does not appear"):
            _validate(worksheet_payload(evidence=claims))

    def test_a_quote_matching_only_the_objective_is_rejected(self):
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = OBJECTIVE
        with pytest.raises(WorksheetCouplingError, match="does not appear"):
            _validate(worksheet_payload(evidence=claims))

    def test_a_quote_matching_only_the_title_is_rejected(self):
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "Rock Detectives: A Sorting Challenge"
        with pytest.raises(WorksheetCouplingError, match="does not appear"):
            _validate(
                worksheet_payload(
                    title="Rock Detectives: A Sorting Challenge", evidence=claims
                )
            )

    def test_a_criterion_printed_inside_a_task_is_still_the_sheet(self):
        """The control on the two above, and the thing they must not break.

        What is left out is the header field, never the words. A sheet whose
        last section asks the child to tick a criterion off has really printed
        that instruction, and quoting it is quoting the sheet.
        """
        instruction = f"Tick the box when you can say: {CRITERION_ONE}"
        payload = worksheet_payload()
        payload["sections"].append(
            {
                "title": "Check yourself",
                "instructions": instruction,
                "sentences": [
                    {
                        "pieces": [
                            {"type": "text", "text": "I can do this "},
                            {"type": "blank", "answer": "yes", "hint": "yes or not yet"},
                            {"type": "text", "text": "."},
                        ]
                    }
                ],
            }
        )
        payload["evidence"][0]["quote"] = instruction
        assert _validate(payload).evidence[0].quote == instruction


class TestTheSheetSearchedIsTheSheetTheChildGets:
    """A quote has to be on the page, not merely in the reply.

    Found on 2026-09-03 by reading every worksheet reply ever saved, while
    working out what a schema for this path should say. Of 87 evidence claims,
    **six quoted text that no generator prints.** Both investigation sheets on
    the 11:51 run answered all three of their criteria out of
    `sorting_section`, `job_section` and `explanation_section` — keys the
    investigation prompt never asks for and the investigation generator has
    never heard of. The coupling check passed them and the run recorded the
    worksheet as made. The sheet the child would have been handed had none of
    it on it.

    It is the same class of hole as the header fields above and closed the same
    way: what is searched is what reaches the document. The generator is the
    only authority on that, so `RENDERED_KEYS` is re-derived from the generator
    source below rather than trusted.

    This tightens the check. Measured against every saved reply before
    shipping: the 78 claims that pointed at something a child would see all
    still pass, and only those six stop passing.
    """

    def _sheet_with_the_quote_in(self, key):
        instruction = "Sort your rocks into groups and label each group."
        payload = worksheet_payload()
        payload[key] = {
            "task": "Grouping",
            "instruction": instruction,
            "grouping_space": "___",
        }
        payload["evidence"][0]["quote"] = instruction
        return payload, instruction

    def test_a_quote_found_only_in_a_key_no_generator_prints_is_refused(self):
        payload, _ = self._sheet_with_the_quote_in("sorting_section")
        with pytest.raises(WorksheetCouplingError, match="does not appear"):
            _validate(payload, worksheet_type="cloze")

    def test_the_same_words_in_a_part_that_is_printed_are_accepted(self):
        """The control. It is the key that is wrong, never the words — put the
        same instruction where the sheet actually prints it and it passes."""
        payload, instruction = self._sheet_with_the_quote_in("sorting_section")
        del payload["sorting_section"]
        payload["sections"].append(
            {"title": "Grouping", "instructions": instruction, "sentences": []}
        )
        assert _validate(payload).evidence[0].quote == instruction

    def test_a_type_with_no_map_entry_still_searches_the_whole_sheet(self):
        """An unknown type is a programming mistake, not bad model output.
        Searching nothing would refuse every criterion on a sheet that is
        probably fine — the failure this repo has paid for four times."""
        payload, instruction = self._sheet_with_the_quote_in("sorting_section")
        assert (
            _validate(payload, worksheet_type="a_type_that_does_not_exist")
            .evidence[0]
            .quote
            == instruction
        )

    def test_a_sheet_with_nothing_printable_says_so_rather_than_blaming_the_quote(
        self,
    ):
        """A refusal the model will read is an instruction, not a description —
        the law this lane earned three times over on 2026-09-03.

        A sheet in the wrong kind's shape has nowhere at all for a quote to be
        found, and telling it "your quote is not on the sheet" once per
        criterion is true, useless and unactionable: every quote really is on
        the thing it returned. It has to be told the sheet is not that kind of
        sheet. Reachable because three types — investigation, times tables and
        fractions practice — need nothing but a title to get this far.
        """
        payload = worksheet_payload()
        with pytest.raises(WorksheetCouplingError) as refused:
            _validate(payload, worksheet_type="investigation")
        assert "investigation" in str(refused.value)
        assert str(refused.value).count("does not appear") == 0

    def test_the_rendered_keys_are_the_ones_the_generator_reads(self):
        """Re-derived from the source, so the map cannot drift away from the
        generators the way a hand-kept list would. A generator that starts
        printing a new key fails here until the map is told."""
        import re
        from pathlib import Path

        from planning.worksheet_schema import RENDERED_KEYS

        root = Path(worksheet_module.__file__).resolve().parent.parent
        for worksheet_type, mapped in RENDERED_KEYS.items():
            source = (root / "generators" / f"{worksheet_type}.py").read_text()
            read = set(re.findall(r"content(?:\.get\(|\[)['\"]([a-z_]+)['\"]", source))
            assert read == mapped, (
                f"The {worksheet_type} generator reads {sorted(read)}; the map "
                f"says {sorted(mapped)}."
            )


# ── One refusal, naming everything wrong ─────────────────────────────────────


class TestEveryFaultIsReportedTogether:
    """A refusal that names one fault gets that one fixed and loses the rest.

    Earned on the lesson lane on 2026-09-03 and inherited here the moment a
    refused worksheet started being asked for a second time. There is exactly
    one repair, so a refusal naming the first fault it met sends back a sheet
    that fixes it and is then refused for the second — a sheet lost to a fault
    it was never shown.
    """

    def test_two_quotes_that_are_not_on_the_sheet_are_both_named(self):
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "Draw a picture of each rock and label it carefully."
        claims[1]["quote"] = "Colour in the rocks using your favourite colours."
        with pytest.raises(WorksheetCouplingError) as refused:
            _validate(worksheet_payload(evidence=claims))
        assert "Draw a picture" in str(refused.value)
        assert "Colour in the rocks" in str(refused.value)

    def test_a_bad_quote_and_an_unevidenced_criterion_are_reported_together(self):
        claims = [worksheet_payload()["evidence"][0]]
        claims[0]["quote"] = "Draw a picture of each rock and label it carefully."
        with pytest.raises(WorksheetCouplingError) as refused:
            _validate(worksheet_payload(evidence=claims))
        message = str(refused.value)
        assert "Draw a picture" in message
        assert CRITERION_TWO in message

    def test_a_short_quote_and_a_missing_record_are_reported_together(self):
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "the"
        claims[1]["pupil_writes"] = ""
        with pytest.raises(WorksheetCouplingError) as refused:
            _validate(worksheet_payload(evidence=claims))
        message = str(refused.value)
        assert "too short" in message
        assert "records nothing" in message

    def test_a_criterion_is_not_reported_twice_over(self):
        """Once for the quote that missed, and again as unevidenced."""
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "Draw a picture of each rock and label it carefully."
        with pytest.raises(WorksheetCouplingError) as refused:
            _validate(worksheet_payload(evidence=claims))
        assert str(refused.value).count(CRITERION_ONE) == 1


class TestTheRefusalIsAnInstruction:
    """A refusal the model will read is an instruction, not a description.

    *"The quote does not appear on the sheet"* is true and useless: it
    describes exactly what the model chose to do, so the repair returns the
    same thing. The fourth guard-refuses-correct-work was this shape — an
    investigation sheet with a results-table column the child writes in, and a
    quote that was a sentence *about* the column rather than the column's own
    words. The sheet was right and was thrown away.
    """

    def test_it_says_to_copy_the_sheets_own_words(self):
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "In the first column, record two property words."
        with pytest.raises(WorksheetCouplingError) as refused:
            _validate(worksheet_payload(evidence=claims))
        message = str(refused.value).lower()
        assert "copy" in message
        assert "column heading" in message

    def test_an_unevidenced_criterion_is_told_to_add_a_task(self):
        claims = [worksheet_payload()["evidence"][0]]
        with pytest.raises(WorksheetCouplingError) as refused:
            _validate(worksheet_payload(evidence=claims))
        assert "add a task" in str(refused.value).lower()

    @pytest.mark.parametrize(
        "fault,change",
        [
            ("a quote that is not on the sheet", {"quote": "Colour the rocks in."}),
            ("a quote that is mostly blanks", {"quote": "This ___ is ___ because ___."}),
            ("a part where the child records nothing", {"pupil_writes": ""}),
            ("a criterion the lesson never set", {"criterion": "I can name a rock."}),
        ],
    )
    def test_every_refusal_says_what_would_fix_it(self, fault, change):
        """The law as a rule rather than as four cases.

        Every one of these reaches two readers: the model, in the repair,
        which can only act on an instruction — and the teacher, if the second
        attempt fails too. "To fix it" is the marker between the two, so she
        can stop reading where the sheet stops being the subject.

        The blanks case is not hypothetical. It fired live on 2026-09-03 on
        *"This _____ is _____ because _____."* — a sentence frame that is
        genuinely on the sheet and that the child genuinely writes in, and
        whose own words are too few to say which part of the sheet is meant.
        """
        claims = worksheet_payload()["evidence"]
        claims[0].update(change)
        with pytest.raises(WorksheetCouplingError) as refused:
            _validate(worksheet_payload(evidence=claims))
        assert "To fix it:" in str(refused.value), (
            f"The refusal for {fault} describes it without saying what would "
            f"fix it, so a repair gets the same reply back."
        )


class TestTheRefusalHandsBackTheSheetsOwnWords:
    """Naming the move is not the same as making it findable.

    Two sheets were lost this way on the evening of 2026-09-03, both read off
    the artefacts rather than guessed at.

    A word-bank sheet quoted `'Rock 1 name:'` and was told to quote *"the
    instruction or question the child reads before writing"*. An instruction
    doing exactly that — *"For each rock, write its name in the box"* — was on
    the very same activity. It quoted the label again, and the repair came back
    **shorter** than the first attempt.
    (`live-runs/2026-09-03-195830/07-reply.txt`, `08-reply.txt`.)

    A cloze sheet quoted its fossil-formation passage as one sentence, when the
    sheet prints that passage as four separate paragraphs. It was told to copy
    *"that part's own words"* without ever being told which parts there were.
    (`live-runs/2026-09-03-200559/08-reply.txt`.)

    So the refusal named the right move both times and left the model to find
    it. The guard does not move — a recorded control says a search loose enough
    to accept either of those also accepts the fabrication it exists to catch.
    What changes is that the refusal now carries the sheet's own lines where
    the quote appears, printed one per line, so the conforming move is on the
    page rather than described.

    ⚠️ The control that keeps this honest is the last two tests. A quote that
    appears nowhere is offered **nothing** — a fabrication does not get a menu
    to pick a passing line out of — and every line that is offered has to
    survive the real check when it is quoted back.
    """

    def _refusal(self, payload):
        with pytest.raises(WorksheetCouplingError) as refused:
            _validate(payload)
        return str(refused.value)

    # The cloze sheet from the 20:05 run, cut down to the two paragraphs the
    # model welded into one quote.
    FIRST = "First, a sea creature died and sank to the seabed. It became "
    SECOND = "Over thousands of years the layers pressed down and turned into hard "

    def _fossil_sheet(self, quote):
        return worksheet_payload(
            sections=[
                {
                    "title": "How the fossil formed",
                    "paragraphs": [
                        [
                            {"type": "text", "text": self.FIRST},
                            {"type": "blank", "answer": "trapped", "hint": "stuck"},
                            {"type": "text", "text": " under layers of mud and sand."},
                        ],
                        [
                            {"type": "text", "text": self.SECOND},
                            {"type": "blank", "answer": "rock", "hint": "solid"},
                            {"type": "text", "text": "."},
                        ],
                    ],
                }
            ],
            evidence=[
                {
                    "criterion": CRITERION_ONE,
                    "where": "How the fossil formed",
                    "quote": quote,
                    "pupil_writes": "The missing word in each paragraph",
                },
                {
                    "criterion": CRITERION_TWO,
                    "where": "How the fossil formed",
                    "quote": f"{self.SECOND}___.",
                    "pupil_writes": "The missing word",
                },
            ],
        )

    WELDED = (
        "First, a sea creature died and sank to the seabed. It became trapped "
        "under layers of mud and sand. Over thousands of years the layers "
        "pressed down and turned into hard rock."
    )

    def test_a_short_quote_is_shown_the_whole_line_it_sits_in(self):
        """The word-bank case. The label really is on the sheet — it is the
        rest of the line that says which part of the sheet is meant."""
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "Granite feels"
        message = self._refusal(worksheet_payload(evidence=claims))
        assert "too short" in message
        assert "Granite feels ___ when you touch it." in message

    def test_a_quote_welded_across_paragraphs_is_shown_them_one_at_a_time(self):
        """The cloze case. The passage is contiguous on the page and the sheet
        stores it as separate paragraphs, so the legal move is to quote one."""
        message = self._refusal(self._fossil_sheet(self.WELDED))
        assert "does not appear" in message
        assert f"{self.FIRST}___ under layers of mud and sand." in message
        assert f"{self.SECOND}___." in message

    def test_it_says_to_copy_one_of_them_rather_than_join_them(self):
        """A list with no instruction on it is an invitation to weld."""
        message = self._refusal(self._fossil_sheet(self.WELDED)).lower()
        assert "copy one of them" in message

    def test_a_fabricated_quote_is_offered_nothing(self):
        """⚠️ The control, and the reason this is not a menu.

        The check exists because a cloze sheet once claimed a task sentence
        that appeared nowhere but inside its own claim. Handing that sheet a
        list of lines it could quote instead would let it pick any passing line
        and evidence a criterion with a task that does not produce it — a false
        pass, which is worse than the refusal, because a refusal is visible and
        gets a second attempt.
        """
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "Dead plants and insects decay in the soil over many years."
        message = self._refusal(worksheet_payload(evidence=claims))
        assert "does not appear" in message
        assert "Granite feels" not in message
        assert INSTRUCTION_TWO not in message

    def test_a_half_sentence_is_never_offered(self):
        """The fragments a sentence is stored in are quotable and are not
        lines. *"First, a sea creature died and sank to the seabed. It became"*
        is a real searchable piece of the sheet and it stops mid-clause, so
        handing it back is worse advice than handing back nothing."""
        offered = worksheet_module._lines_to_copy(
            self.WELDED, self._fossil_sheet(self.WELDED), "cloze"
        )
        assert offered
        assert not any(line.endswith("It became") for line in offered), (
            "a fragment that ends mid-sentence was offered as a line to copy"
        )

    def test_a_capped_list_says_it_was_capped(self):
        """A list that quietly stops short reads as all of them."""
        lines = [f"Write the name of rock number {n} in the box." for n in range(6)]
        block = worksheet_module._copy_one_of_these(lines)
        assert lines[0] in block
        assert "more" in block

    def test_a_line_too_short_to_be_a_quote_is_never_offered(self):
        """Offering a line that would be refused for length reproduces the very
        fault being reported."""
        payload = worksheet_payload(
            sections=[
                {
                    "title": "Rocks",
                    "instructions": "Rock 1 name:",
                    "sentences": [
                        {
                            "pieces": [
                                {"type": "text", "text": "Rock 1 name: "},
                                {"type": "blank", "answer": "granite", "hint": "hard"},
                            ]
                        }
                    ],
                }
            ],
            evidence=[
                {
                    "criterion": criterion,
                    "where": "Rocks",
                    "quote": "Rock 1 name:",
                    "pupil_writes": "The name of the rock",
                }
                for criterion in (CRITERION_ONE, CRITERION_TWO)
            ],
        )
        message = self._refusal(payload)
        assert "too short" in message
        assert "Copy ONE of them" not in message

    @pytest.mark.parametrize(
        "quote",
        [
            "Granite feels",  # a sentence stored as fragments
            "Sort the six rocks",  # a plain instruction
            WELDED,  # welded across two paragraphs
        ],
    )
    def test_every_line_offered_is_accepted_when_it_is_quoted(self, quote):
        """⚠️ The guarantee, and the control on two walks of the sheet.

        The lines handed back come from a narrower walk than the one the check
        searches — it leaves out the fragments a sentence is stored in, the
        hints beside its gaps, and two adjacent prompts run together, none of
        which is something to tell a model to copy. Two walks can drift, so
        every line offered is quoted back through the real check here: one this
        offers that the check would refuse fails the suite rather than a
        teacher.
        """
        payload = (
            self._fossil_sheet(quote)
            if quote == self.WELDED
            else worksheet_payload(
                evidence=[
                    dict(worksheet_payload()["evidence"][0], quote=quote),
                    worksheet_payload()["evidence"][1],
                ]
            )
        )
        offered = worksheet_module._lines_to_copy(
            quote, payload, "cloze"
        )
        assert offered, "nothing was offered, so this proves nothing"
        for line in offered:
            claims = [dict(payload["evidence"][0], quote=line)] + payload["evidence"][1:]
            sheet = _validate(dict(payload, evidence=claims))
            assert sheet.evidence[0].quote == line


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

    def test_it_says_where_an_added_task_has_to_go(self):
        """The conforming move for the instruction one line above it.

        The sheet is told to add a task rather than touch a criterion, and
        since 2026-09-03 the reply is constrained to the fields its own kind of
        worksheet has — so "add a task" has exactly one legal form and the
        prompt has to say which. It is the same shape of gap as the table
        column: an instruction with no conforming move gets a refusal the model
        cannot act on, and the sheet is lost on the second attempt too.

        It is also what the model actually did wrong. On the 11:51 run it
        added three sections of its own invention, evidenced every criterion in
        them, and none of it would have been printed.
        """
        prompt = self._prompt().lower()
        assert "invent" in prompt
        assert "not printed" in prompt or "is not printed" in prompt

    def test_it_says_a_table_column_is_quoted_by_its_heading(self):
        """Found live, 2026-09-03, and it refused correct work.

        An investigation sheet evidenced a criterion in a results-table column
        the child writes in. Asked for "one sentence, question or instruction",
        the model had no conforming move — a column heading is none of those —
        so it wrote a sentence about the column, and the whole correct sheet
        was thrown away. The prompt now says what to quote when the child
        writes in a table.
        """
        prompt = self._prompt().lower()
        assert "column heading" in prompt

    def test_it_shows_a_description_beside_the_quote_it_should_have_been(self):
        """The prohibition on its own had already been tried and had already
        failed — the prompt said a summary is rejected, in those words, and the
        model summarised anyway. What it did not have was the conforming move
        shown next to the one that gets refused."""
        prompt = self._prompt()
        assert "In the 'What we found' column, record what it looks like." in prompt
        assert "What we found (describe what it looks like)" in prompt
        assert "this is a description, and it is refused" in prompt

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


class TestTheRequestCarriesTheShapeOfTheSheet:
    """One schema per type, and the reason it is per type rather than one.

    A single closed schema across all ten was the thing the handover ruled out,
    and rightly: three of the four worksheet defects were legitimate shapes the
    guard could not read, and `additionalProperties: false` across all of them
    would have made those shapes impossible to write rather than merely
    refused. Per type there is no clash — `paragraphs` is what a cloze sheet is,
    and it does not have to be legal on a times-tables sheet.

    Every schema is checked in `tests/test_worksheet_schema.py` against content
    the generators already render, which is where a schema that forbids working
    work would be caught.
    """

    def test_the_request_carries_the_schema_for_that_type(self, sent):
        _make(worksheet_type="cloze")
        assert sent["kwargs"].get("schema") == get_worksheet_schema("cloze")

    def test_a_different_type_gets_its_own_shape(self, sent):
        """The whole reason there are ten rather than one. A word-bank sheet
        asked for under the cloze schema could not write one of its sentences.

        The sheet that comes back here is a cloze one and is refused, which is
        not what is being tested — the assertion is on the request, and the
        request is made before any of that.
        """
        with pytest.raises(WorksheetContentError):
            _make(worksheet_type="matching")
        assert sent["kwargs"].get("schema") == get_worksheet_schema("matching")
        assert get_worksheet_schema("matching") != get_worksheet_schema("cloze")


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


# ── Asked for a second time, never let through ───────────────────────────────


@pytest.fixture
def attempts(monkeypatch):
    """Several replies in order, so the repair can be watched."""
    record = {"payloads": [], "raises": [], "sent": [], "kwargs": []}

    def fake_generate(content, system_prompt, **kwargs):
        record["sent"].append(content)
        record["kwargs"].append(kwargs)
        if record["raises"]:
            error = record["raises"].pop(0)
            if error is not None:
                raise error
        if not record["payloads"]:
            raise AssertionError(
                f"The worksheet was asked for {len(record['sent'])} times; the "
                f"test only set up {len(record['sent']) - 1}."
            )
        return record["payloads"].pop(0)

    monkeypatch.setattr(worksheet_module, "generate_structured_content", fake_generate)
    return record


def _pointer_off_the_sheet():
    """The live shape: the task is there, the quote describes it instead.

    Taken from `live-runs/2026-09-03-010849/10-reply.txt`, where a criterion
    was evidenced by a results-table column the child writes in and the quote
    came back as a sentence about that column.
    """
    claims = worksheet_payload()["evidence"]
    claims[1]["quote"] = (
        "In the 'My groups' column, record the heading you chose for each group."
    )
    return worksheet_payload(evidence=claims)


class TestAWorksheetThatFailsItsChecksIsAskedForAgain:
    """The fourth guard-refuses-correct-work, and the answer to all four.

    Three of the four were the search being blind to a shape the sheet
    legitimately comes back in, and each was fixed by teaching the search that
    shape. The fourth is not that: the guard is right, the quote genuinely is
    not on the sheet, and the sheet is right too. What was wrong is that a
    correct worksheet was thrown away over a mis-copied pointer.

    So the guard does not move. The sheet is asked for once more, carrying the
    attempt and every reason it was refused, and the second reply goes through
    the same checks. Softening the search is how the fabrication it caught —
    a cloze sheet claiming a task sentence that existed nowhere but inside its
    own claim — gets back in.
    """

    def test_a_named_failure_is_repaired(self, attempts):
        attempts["payloads"] = [_pointer_off_the_sheet(), worksheet_payload()]
        assert _make().objective == OBJECTIVE
        assert len(attempts["sent"]) == 2

    def test_the_second_ask_says_what_was_wrong(self, attempts):
        """The refusal itself, not just the original ask repeated. A repair
        that carries only the first request is a re-roll with extra steps."""
        attempts["payloads"] = [_pointer_off_the_sheet(), worksheet_payload()]
        _make()
        second = attempts["sent"][1]
        assert "In the 'My groups' column" in second
        assert "does not appear anywhere on the worksheet" in second

    def test_the_second_ask_carries_the_attempt_it_is_repairing(self, attempts):
        """Otherwise it is a re-roll, and a re-roll throws away the sheet."""
        attempts["payloads"] = [_pointer_off_the_sheet(), worksheet_payload()]
        _make()
        assert "Granite feels " in attempts["sent"][1]
        assert INSTRUCTION_ONE in attempts["sent"][1]

    def test_a_worksheet_that_passes_is_not_asked_for_twice(self, attempts):
        attempts["payloads"] = [worksheet_payload()]
        _make()
        assert len(attempts["sent"]) == 1

    def test_the_repair_is_checked_by_the_same_guard(self, attempts):
        """The check is not relaxed for the second attempt. Relaxing it is how
        a sheet that evidences nothing reaches a child's book."""
        attempts["payloads"] = [_pointer_off_the_sheet(), _pointer_off_the_sheet()]
        with pytest.raises(WorksheetCouplingError, match="does not appear"):
            _make()

    def test_it_does_not_ask_a_third_time(self, attempts):
        attempts["payloads"] = [_pointer_off_the_sheet(), _pointer_off_the_sheet()]
        with pytest.raises(WorksheetCouplingError):
            _make()
        assert len(attempts["sent"]) == 2

    def test_the_second_refusal_says_it_was_the_second(self, attempts):
        attempts["payloads"] = [_pointer_off_the_sheet(), _pointer_off_the_sheet()]
        with pytest.raises(WorksheetCouplingError, match="second attempt"):
            _make()

    def test_a_fabricated_task_is_still_refused_after_two_attempts(self, attempts):
        """The one this check was built for, and the reason it is not softened.

        A cloze sheet claimed a task sentence that appears nowhere except
        inside its own claim. It is refused, asked again, and refused again.
        """
        claims = worksheet_payload()["evidence"]
        claims[0]["quote"] = "Dead plants and insects decay in the soil over time."
        faked = worksheet_payload(evidence=claims)
        attempts["payloads"] = [faked, faked]
        with pytest.raises(WorksheetCouplingError, match="does not appear"):
            _make()

    def test_a_drifted_objective_is_repairable_too(self, attempts):
        attempts["payloads"] = [
            worksheet_payload(objective="Sort rocks into groups"),
            worksheet_payload(),
        ]
        assert _make().objective == OBJECTIVE

    def test_a_truncated_reply_is_not_asked_for_again(self, attempts):
        """Asking again for a reply that ran out of room gets another reply
        that runs out of room. The answer to that is the token budget."""
        attempts["raises"] = [TruncatedResponseError("stopped at max_tokens")]
        attempts["payloads"] = [worksheet_payload()]
        with pytest.raises(TruncatedResponseError):
            _make()
        assert len(attempts["sent"]) == 1

    def test_unusable_json_is_not_asked_for_again(self, attempts):
        attempts["raises"] = [json.JSONDecodeError("no JSON here", "", 0)]
        attempts["payloads"] = [worksheet_payload()]
        with pytest.raises(json.JSONDecodeError):
            _make()
        assert len(attempts["sent"]) == 1

    def test_a_sheet_the_generator_cannot_build_is_not_asked_for_again(self, attempts):
        """A different class of failure, and one with no live instance behind
        it. It is refused as it always was rather than given an untested
        second attempt."""
        broken = worksheet_payload()
        del broken["sections"]
        attempts["payloads"] = [broken, worksheet_payload()]
        with pytest.raises(WorksheetContentError):
            _make()
        assert len(attempts["sent"]) == 1

    def test_the_repair_is_sent_the_same_way_as_the_first_ask(self, attempts):
        """A repair that dropped the stream or the token budget would be the
        request that fails, on the sheet that had already been made once."""
        attempts["payloads"] = [_pointer_off_the_sheet(), worksheet_payload()]
        _make()

        assert len(attempts["kwargs"]) == 2
        first, repair = attempts["kwargs"]
        for name in ("stream", "max_tokens", "timeout"):
            assert repair.get(name) == first.get(name), (
                f"The repair request sent a different {name} from the first ask."
            )
        assert repair.get("stream") is True
        # The same schema both times, and it matters more on the repair than on
        # the first ask: the repair carries the whole refused sheet back in its
        # prompt, so it is the longer request and the likelier one to come home
        # as unparseable JSON. A repair sent without the schema would also be
        # free to answer in a shape the first ask was not allowed to use.
        assert repair.get("schema") == first.get("schema") == get_worksheet_schema("cloze")


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
