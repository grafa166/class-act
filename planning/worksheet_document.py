"""The worksheet, as the sheet she prints and hands out.

Found on 2026-09-04 by counting rather than by guessing: the plan page had
**one** download button, for the lesson plan, and imported none of the ten
generators. So the headline feature — a worksheet built from a lesson, checked
against it, printing her criteria — made something she could look at on screen
and could not get out of the app. A worksheet that cannot be printed is not a
worksheet.

**What is rendered is `sheet.content`, and nothing else is derived from it.**
That is the whole point. Every criterion was accepted because its quote was
found in the worksheet reply, and that guarantee only reaches the child if the
reply and the printed page are the same object. They quietly stopped being the
same object once already, on 2026-09-03, when six evidence claims quoted
sections no generator prints and the check passed all six. So
`test_every_quote_that_was_checked_is_on_the_page` takes the claims the guard
accepted and finds each one in the rendered document.

⚠️ **The map below is a second copy of the one in `app.py`**, and that is a
deliberate, tested exception to this project's own one-definition rule.
`app.py` is a Streamlit script: importing it to borrow the map would execute
the whole worksheet flow, and there is a recorded decision that it stays
structurally untouched because it works and has almost no coverage. So the two
are pinned to each other by a test that reads `app.py` as text rather than
running it — `test_the_two_generator_maps_agree`. If someone adds an eleventh
kind to one and not the other, that fails rather than a teacher.
"""

import io

from generators.calculation_practice import generate_calculation_practice_worksheet
from generators.cloze import generate_cloze_worksheet
from generators.fraction_practice import generate_fraction_practice_worksheet
from generators.investigation import generate_investigation_worksheet
from generators.matching import generate_matching_worksheet
from generators.problem_solving import generate_problem_solving_worksheet
from generators.reading_comprehension import generate_reading_comprehension_worksheet
from generators.sentence_builder import generate_sentence_builder_worksheet
from generators.styles import FONT_NAME
from generators.times_tables import generate_times_tables_worksheet
from generators.word_bank import generate_word_bank_worksheet

GENERATOR_FOR = {
    "cloze": generate_cloze_worksheet,
    "word_bank": generate_word_bank_worksheet,
    "matching": generate_matching_worksheet,
    "sentence_builder": generate_sentence_builder_worksheet,
    "reading_comprehension": generate_reading_comprehension_worksheet,
    "problem_solving": generate_problem_solving_worksheet,
    "calculation_practice": generate_calculation_practice_worksheet,
    "investigation": generate_investigation_worksheet,
    "fraction_practice": generate_fraction_practice_worksheet,
    "times_tables": generate_times_tables_worksheet,
}


def build_worksheet_document(
    sheet,
    level="expected",
    theme_key="classic",
    font=FONT_NAME,
    show_answers=False,
    extra_spacing=False,
    eal_glossary=False,
):
    """The Word document for a worksheet that has been checked against a lesson.

    `sheet.content` goes to the generator exactly as the checks left it: her
    objective and her criteria are already in it, in her order, put there by
    `validate_coupled_worksheet`. The objective is passed separately as well
    because the generators take it that way, and it is taken from the same
    object rather than from anywhere the two could differ.

    Raises:
        KeyError: a kind of sheet with no generator, which is a programming
            mistake rather than anything a teacher did.
    """
    return GENERATOR_FOR[sheet.worksheet_type](
        content=sheet.content,
        theme_key=theme_key,
        level=level,
        objective=sheet.objective,
        extra_spacing=extra_spacing,
        eal_glossary=eal_glossary,
        show_answers=show_answers,
        font=font,
    )


def worksheet_filename(sheet, unit_title="", answers=False):
    """What lands in her Downloads folder.

    A folder of files called `download.docx` is a folder of nothing. The unit
    title is hers to type, so it is scrubbed rather than trusted — the same law
    the lesson plan earned, because *"Rocks and Soils: term 1/2"* is a
    plausible thing to type and carries characters that are a path separator or
    illegal in a filename on the machines she uses.
    """
    number = f"lesson {sheet.lesson_number}" if sheet.lesson_number else "lesson"
    ending = "worksheet answers" if answers else "worksheet"
    title = "".join(
        character for character in str(unit_title).strip()
        if character.isalnum() or character in " -_&'"
    ).strip()
    title = " ".join(title.split())
    if title:
        return f"{title} - {number} - {ending}.docx"
    return f"{number.capitalize()} - {ending}.docx"


def worksheets_as_one_file(sheets, unit_title="", **rendering):
    """Every sheet in the unit, plus its answers, in one zip.

    Eight download buttons is eight chances to miss one, and the page reloads
    between each. She asks for the unit and gets the unit.
    """
    import zipfile

    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
        for sheet in sheets:
            for answers in (False, True):
                document = build_worksheet_document(
                    sheet, show_answers=answers, **rendering
                )
                archive.writestr(
                    worksheet_filename(sheet, unit_title, answers=answers),
                    document.getvalue(),
                )
    bundle.seek(0)
    return bundle
