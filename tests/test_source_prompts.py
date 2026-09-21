"""What the prompt says when she has supplied a text of her own.

The ten worksheet templates were written on the assumption that Claude invents
its own passage, and they say so in numbered rules: the passage must be
self-contained and answer every question (rule 11), the vocabulary must come
from it (rule 3), the vocabulary questions must ask about words in it (rule
12), and it must be themed (rule 10).

Overwriting the passage afterwards and leaving those rules standing prints her
story above eight questions about a story that no longer exists. An adversarial
pass caught that before it was built; `scripts/probe_source_types.py` then
measured the fix against the real API on 2026-09-15 -- passage word for word,
six of six vocabulary words from her text, eight of eight questions on it.

So the rules are overridden by number from an appended block, and **no template
constant is edited** -- which is why the no-source prompt is still provably the
string it has always been.
"""

import pytest

from llm.prompts import get_prompt, list_worksheet_types, source_instructions
from planning.source_material import (
    SOURCE_CAPABILITY,
    PRINTS_THE_SOURCE,
    WORKSHEET_ACTIONS,
    source_from_text,
)

EXTRACT = (
    "When Mary Lennox was sent to Misselthwaite Manor to live with her uncle "
    "everybody said she was the most disagreeable-looking child ever seen.\n\n"
    "She had a little thin face and a little thin body, thin light hair and a "
    "sour expression."
)

COMMON = dict(
    year_group="Year 3",
    topic="A story opening",
    objective="retrieve and record information from a text",
    age_range="7-8",
    theme_name="Space Explorer",
    theme_icon="\U0001F680",
    level="expected",
    subject="English",
)


@pytest.fixture
def source():
    return source_from_text(EXTRACT, origin="the text you pasted")


class TestNothingChangesWhenThereIsNoSource:
    """The regression guard for the app she is using right now."""

    @pytest.mark.parametrize("worksheet_type", list_worksheet_types())
    def test_a_prompt_with_no_source_is_the_string_it_has_always_been(self, worksheet_type):
        before = get_prompt(worksheet_type=worksheet_type, **COMMON)
        after = get_prompt(worksheet_type=worksheet_type, source_material=None, **COMMON)
        assert before == after

    @pytest.mark.parametrize("worksheet_type", list_worksheet_types())
    def test_no_source_means_no_source_wording_anywhere(self, worksheet_type):
        prompt = get_prompt(worksheet_type=worksheet_type, **COMMON)
        assert "SOURCE" not in prompt
        assert "the text between the markers" not in prompt.lower()


class TestHerTextComesFirst:
    def test_the_source_appears_before_the_worksheet_instructions(self, source):
        prompt = get_prompt(
            worksheet_type="reading_comprehension",
            source_material=source,
            source_action="use_exactly",
            **COMMON,
        )
        assert prompt.index("Misselthwaite") < prompt.index("YOUR TASK")

    def test_the_source_is_reproduced_character_for_character(self, source):
        prompt = get_prompt(
            worksheet_type="reading_comprehension",
            source_material=source,
            source_action="use_exactly",
            **COMMON,
        )
        assert source.text in prompt

    def test_a_source_with_curly_braces_does_not_break_the_template(self):
        awkward = source_from_text("The sign said {KEEP OUT} and she read it twice.", origin="x")
        prompt = get_prompt(
            worksheet_type="reading_comprehension",
            source_material=awkward,
            source_action="use_exactly",
            **COMMON,
        )
        assert "{KEEP OUT}" in prompt, "the source is appended after format(), never through it"


class TestTheTemplatesOwnRulesAreOverridden:
    """The defect the adversarial pass found, as a test."""

    @pytest.mark.parametrize("action", sorted(WORKSHEET_ACTIONS))
    def test_the_vocabulary_is_tied_to_her_text_not_an_invented_passage(self, source, action):
        prompt = get_prompt(
            worksheet_type="reading_comprehension",
            source_material=source,
            source_action=action,
            **COMMON,
        )
        tail = prompt[prompt.index("OVERRIDE"):].lower()
        assert "vocabulary" in tail and "between the markers" in tail

    @pytest.mark.parametrize("action", sorted(WORKSHEET_ACTIONS))
    def test_every_question_is_tied_to_her_text(self, source, action):
        prompt = get_prompt(
            worksheet_type="reading_comprehension",
            source_material=source,
            source_action=action,
            **COMMON,
        )
        tail = prompt[prompt.index("OVERRIDE"):].lower()
        assert "question" in tail and "answerable" in tail

    def test_the_theme_is_told_it_decorates_the_page_and_never_the_text(self, source):
        prompt = get_prompt(
            worksheet_type="reading_comprehension",
            source_material=source,
            source_action="use_exactly",
            **COMMON,
        )
        assert "decorates the page" in prompt.lower()

    def test_using_the_source_exactly_says_word_for_word(self, source):
        prompt = get_prompt(
            worksheet_type="reading_comprehension",
            source_material=source,
            source_action="use_exactly",
            **COMMON,
        )
        assert "word for word" in prompt.lower()

    def test_adapting_asks_for_the_rewrite_to_be_the_passage(self, source):
        prompt = get_prompt(
            worksheet_type="reading_comprehension",
            source_material=source,
            source_action="adapt",
            **COMMON,
        )
        assert "rewrite" in prompt.lower()
        assert "add none" in prompt.lower(), "adapting must not invent a character"


class TestTheLawAboutLaterPartsIsAlwaysStated:
    @pytest.mark.parametrize("worksheet_type", sorted(SOURCE_CAPABILITY))
    @pytest.mark.parametrize("action", sorted(WORKSHEET_ACTIONS))
    def test_every_sourced_prompt_says_there_is_no_rest_of_it(
        self, source, worksheet_type, action
    ):
        """Unconditional on purpose: a flag is a thing someone can forget."""
        if action not in [a for a in WORKSHEET_ACTIONS]:
            pytest.skip("not offered")
        instructions = source_instructions(source, action, worksheet_type)
        lowered = instructions.lower()
        assert "whole of what exists" in lowered
        assert "do not continue it" in lowered
        assert "later" in lowered


class TestASheetThatCannotPrintProseIsToldSomethingElse:
    def test_a_cloze_sheet_is_not_told_to_reproduce_the_whole_text(self, source):
        instructions = source_instructions(source, "questions_from", "cloze")
        assert "does not print the text whole" in instructions.lower()

    def test_a_reading_sheet_is_told_the_text_is_the_passage(self, source):
        instructions = source_instructions(source, "questions_from", "reading_comprehension")
        assert "is the passage" in instructions.lower()

    def test_the_two_are_not_the_same_instruction(self, source):
        assert source_instructions(source, "questions_from", "cloze") != source_instructions(
            source, "questions_from", "reading_comprehension"
        )


class TestAScanIsNamedRatherThanPrintedAsEmptyMarkers:
    """A PDF or a photograph has no text to put between the markers.

    🚨 The seam printed `<<<SOURCE\n\nSOURCE>>>` — an empty box — and then told
    the model to take every question and every vocabulary word from between
    those markers. Measured 2026-09-18: contradictory instructions, an empty
    source block, and nothing on the page saying which document was meant.
    Graeme expects Word files and PDFs to be roughly half her material each, so
    this is not an edge case.
    """

    def a_scan(self):
        from planning.source_material import SourceMaterial

        return SourceMaterial(text="", origin="chapter-one.pdf", blocks=({"type": "document"},))

    def test_the_markers_are_not_printed_empty(self):
        prompt = get_prompt(
            worksheet_type="reading_comprehension",
            source_material=self.a_scan(),
            source_action="questions_from",
            **COMMON,
        )
        assert "<<<SOURCE\n\nSOURCE>>>" not in prompt
        assert "<<<SOURCE\nSOURCE>>>" not in prompt

    def test_the_document_is_named_so_the_model_knows_what_to_read(self):
        prompt = get_prompt(
            worksheet_type="reading_comprehension",
            source_material=self.a_scan(),
            source_action="questions_from",
            **COMMON,
        )
        assert "chapter-one.pdf" in prompt

    def test_the_rules_still_point_at_her_material(self):
        """The override block says "the text between the markers" throughout.
        With no markers, something has to say what that phrase now means."""
        prompt = get_prompt(
            worksheet_type="reading_comprehension",
            source_material=self.a_scan(),
            source_action="questions_from",
            **COMMON,
        )
        assert "between the markers" in prompt
        assert "attached" in prompt.lower()

    def test_held_text_is_still_printed_between_the_markers(self, source):
        prompt = get_prompt(
            worksheet_type="reading_comprehension",
            source_material=source,
            source_action="questions_from",
            **COMMON,
        )
        assert "<<<SOURCE" in prompt
        assert "Misselthwaite" in prompt
