"""The teacher's own text, and what each kind of worksheet can do with it.

She asked for this and called it game changing: upload a document or paste an
extract, then choose what the app does with it. Three things have to be true
before any of that is safe.

**Held text is what arms exactness.** Paste, Word and plain text give us the
words. A PDF or a photograph goes to Claude as an opaque block and we never
hold them, so those routes can build from a source but can never reproduce it
word for word or check a name against it. The difference is a property of the
object, not a flag someone remembers to check.

**A drill has nowhere to put a text.** A times-tables sheet that silently
ignored her upload would be worse than one that refused it, because the
refusal is visible and names the types that would have worked.

**A source the sheet cannot use is refused, not quietly dropped.** Measured
live on 2026-09-15: given a story extract, a maths word-problem sheet invented
a space-shopping scenario and ignored the source entirely, with no error.
"""

import pytest

from planning.source_material import (
    BUILDS_FROM_THE_SOURCE,
    MAX_SOURCE_CHARS,
    NOT_FROM_A_TEXT,
    PRINTS_THE_SOURCE,
    SOURCE_CAPABILITY,
    WORKSHEET_ACTIONS,
    SourceMaterial,
    SourceMaterialError,
    actions_for,
    check_the_pairing,
    read_upload,
    source_from_text,
)
from llm.prompts import list_worksheet_types

EXTRACT = (
    "When Mary Lennox was sent to Misselthwaite Manor to live with her uncle "
    "everybody said she was the most disagreeable-looking child ever seen."
)


def a_docx(paragraphs):
    """A real .docx in memory, so nothing here mocks the thing under test."""
    import io

    from docx import Document

    document = Document()
    for line in paragraphs:
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


class TestTextSheGivesUsDirectly:
    def test_pasted_text_is_the_source_the_moment_she_pastes_it(self):
        source = source_from_text(EXTRACT, origin="the text you pasted")
        assert source.text == EXTRACT
        assert source.is_held

    def test_a_word_document_becomes_text_without_asking_claude(self):
        data = a_docx(["When Mary Lennox was sent", "everybody said she was"])
        source = read_upload("chapter-1.docx", data)
        assert "When Mary Lennox was sent" in source.text
        assert source.is_held, "a Word document has a text layer, so we hold the words"

    def test_a_plain_text_file_becomes_text_without_asking_claude(self):
        source = read_upload("extract.txt", EXTRACT.encode("utf-8"))
        assert source.text == EXTRACT
        assert source.is_held

    def test_a_spreadsheet_is_refused_by_name_and_told_what_to_do_instead(self):
        with pytest.raises(SourceMaterialError) as refused:
            read_upload("marks.xlsx", b"not really a spreadsheet")
        assert "xlsx" in str(refused.value)
        assert "paste" in str(refused.value).lower(), "a refusal has to say what would fix it"

    def test_an_empty_source_is_refused_before_any_request_is_sent(self):
        with pytest.raises(SourceMaterialError):
            source_from_text("   \n  ", origin="the text you pasted")

    def test_a_source_longer_than_the_limit_says_how_many_words_to_cut(self):
        too_long = "word " * (MAX_SOURCE_CHARS // 2)
        with pytest.raises(SourceMaterialError) as refused:
            source_from_text(too_long, origin="the text you pasted")
        assert "words" in str(refused.value), "a limit nobody can act on is not a limit"


class TestHerParagraphsReachThePage:
    """`add_reading_passage` splits on a blank line and only on a blank line.

    Measured at `generators/components.py:835`: a text with single newlines is
    rendered as one unbroken block, on the worksheet type that matters most.
    """

    def test_her_blank_lines_between_paragraphs_survive_intact(self):
        source = source_from_text("First para.\n\nSecond para.", origin="x")
        assert source.text == "First para.\n\nSecond para."

    def test_single_newlines_become_paragraph_breaks(self):
        source = source_from_text("First para.\nSecond para.", origin="x")
        assert source.text == "First para.\n\nSecond para."

    def test_a_run_of_blank_lines_is_still_one_break(self):
        source = source_from_text("First.\n\n\n\nSecond.", origin="x")
        assert source.text == "First.\n\nSecond."


class TestAScanIsNotHeldText:
    def test_a_photograph_is_carried_as_blocks_rather_than_words(self):
        source = read_upload("page.jpg", b"\xff\xd8\xff\xe0 pretend jpeg")
        assert not source.is_held, "we never see the words on a photograph"
        assert source.blocks, "but it still reaches the model"

    def test_a_scan_cannot_be_asked_for_word_for_word_reproduction(self):
        source = read_upload("page.jpg", b"\xff\xd8\xff\xe0 pretend jpeg")
        offered = actions_for("reading_comprehension", source)
        assert "use_exactly" not in offered
        assert "questions_from" in offered, "the other three still work on a scan"

    def test_held_text_is_offered_every_action(self):
        source = source_from_text(EXTRACT, origin="x")
        offered = actions_for("reading_comprehension", source)
        assert set(offered) == set(WORKSHEET_ACTIONS)


class TestTheMatrixCannotDrift:
    def test_every_worksheet_type_has_an_entry_in_the_capability_matrix(self):
        missing = sorted(set(list_worksheet_types()) - set(SOURCE_CAPABILITY))
        assert not missing, f"no source capability declared for: {missing}"

    def test_the_matrix_names_no_worksheet_type_that_does_not_exist(self):
        invented = sorted(set(SOURCE_CAPABILITY) - set(list_worksheet_types()))
        assert not invented, f"the matrix names types that do not exist: {invented}"

    def test_a_worksheet_type_nobody_has_heard_of_is_offered_no_actions(self):
        """Fails closed, not open.

        Nothing called `actions_for` with an unknown type until the positive
        control pointed out that defaulting it to "prints the source" was
        invisible to the whole suite. A type with no declared capability must
        offer nothing rather than everything.
        """
        held = source_from_text(EXTRACT, origin="x")
        assert actions_for("origami_practice", held) == {}

    def test_between_them_the_types_offer_all_four_worksheet_actions(self):
        held = source_from_text(EXTRACT, origin="x")
        offered = set()
        for worksheet_type in SOURCE_CAPABILITY:
            offered |= set(actions_for(worksheet_type, held))
        assert offered == set(WORKSHEET_ACTIONS), "she asked for four; she gets four"

    def test_the_two_types_that_print_prose_are_the_ones_measured_to_do_it(self):
        """Both were proved live on 2026-09-15 — see scripts/probe_source_types.py."""
        prints = {t for t, c in SOURCE_CAPABILITY.items() if c is PRINTS_THE_SOURCE}
        assert prints == {"reading_comprehension", "problem_solving"}


class TestAPairingThatCannotWorkIsRefused:
    def test_a_times_tables_sheet_says_a_drill_has_nowhere_to_put_a_text(self):
        with pytest.raises(SourceMaterialError) as refused:
            check_the_pairing("times_tables", "questions_from")
        message = str(refused.value).lower()
        assert "times tables" in message
        # ⚠️ The word that tells the two refusals apart. Asserting only on the
        # type name passed even with this branch disabled, because execution
        # fell through to the "nowhere to print it whole" refusal, which names
        # the type too. The positive control found that; no test did.
        assert "drill" in message, "this is the drill refusal, not the other one"

    def test_a_fill_in_the_gaps_sheet_refused_for_exactness_names_the_two_that_can(self):
        with pytest.raises(SourceMaterialError) as refused:
            check_the_pairing("cloze", "use_exactly")
        message = str(refused.value)
        assert "reading comprehension" in message.lower()

    def test_a_refusal_names_every_action_that_would_have_worked(self):
        with pytest.raises(SourceMaterialError) as refused:
            check_the_pairing("cloze", "use_exactly")
        message = str(refused.value).lower()
        for still_fine in ("simplify", "questions", "scaffold"):
            assert still_fine in message, f"the refusal never mentions {still_fine}"

    def test_a_reading_sheet_accepts_all_four_actions(self):
        for action in WORKSHEET_ACTIONS:
            check_the_pairing("reading_comprehension", action)

    def test_an_action_nobody_has_heard_of_is_refused_by_name(self):
        with pytest.raises(SourceMaterialError) as refused:
            check_the_pairing("reading_comprehension", "make_it_rhyme")
        assert "make_it_rhyme" in str(refused.value)


class TestTheCapabilitiesAreDistinct:
    def test_a_drill_is_offered_no_actions_at_all(self):
        held = source_from_text(EXTRACT, origin="x")
        for worksheet_type, capability in SOURCE_CAPABILITY.items():
            if capability is NOT_FROM_A_TEXT:
                assert actions_for(worksheet_type, held) == {}

    def test_a_build_from_type_is_offered_three_not_four(self):
        held = source_from_text(EXTRACT, origin="x")
        for worksheet_type, capability in SOURCE_CAPABILITY.items():
            if capability is BUILDS_FROM_THE_SOURCE:
                offered = actions_for(worksheet_type, held)
                assert "use_exactly" not in offered
                assert len(offered) == 3


class TestSourceMaterialIsNotProvenance:
    def test_the_field_is_never_called_source(self):
        """`UnitSpine.source`, `CoupledWorksheet.source` already mean provenance.

        One word, two meanings, is how the wrong one gets printed on a sheet.
        """
        assert not hasattr(SourceMaterial(text="x", origin="y"), "source")
