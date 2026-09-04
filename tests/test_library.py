"""A unit she planned is still there tomorrow.

Until now nothing was saved. She could read a scheme, approve a sequence, wait
several minutes while every lesson was written, generate the worksheets — and
lose all of it by closing the tab. That is not a product, and it is the reason
the tool could not be handed to anyone.

The risk in saving is not losing the unit. It is **giving it back slightly
different**, which is the defect this whole repo keeps finding: a criterion
quietly reworded, a step's timing dropped, a worksheet's evidence pointing at a
task that no longer says what it said. The plan, the sheet and the child's book
agree only because every handover is checked word for word — and saving is one
more handover.

So the test that matters is not "does it save". It is
`test_every_word_of_the_unit_comes_back`, which walks the objects rather than
naming their fields, so a field added later and never stored fails here rather
than in front of a teacher.

None of these touch the network.
"""

import os
import pathlib

import pytest
import sqlalchemy

from planning.lesson import validate_lesson
from planning.library import (
    UnitNotFound,
    delete_unit,
    library_url,
    list_units,
    load_unit,
    open_library,
    save_unit,
    set_lesson_status,
)
from planning.spine import validate_spine
from planning.worksheet import validate_coupled_worksheet

OBJECTIVE_ONE = "Compare the appearance of different rocks using property words"
OBJECTIVE_TWO = "Group rocks by their properties and say what each group shares"

CRITERION_ONE = "I can describe two rocks using property words."
CRITERION_TWO = "I can put rocks into groups and say what the group has in common."

INSTRUCTION = "Write two property words for each rock in the table."


def a_spine():
    return validate_spine(
        {
            "lessons": [
                {
                    "number": 1,
                    "objective": OBJECTIVE_ONE,
                    "builds_on": None,
                    "builds_on_reason": "First lesson of the unit",
                    "covers": ["compare and group together different kinds of rocks"],
                },
                {
                    "number": 2,
                    "objective": OBJECTIVE_TWO,
                    "builds_on": 1,
                    "builds_on_reason": "They need the property words before grouping",
                    "covers": ["compare and group together different kinds of rocks"],
                    "assesses_outcome": True,
                },
            ],
            "outcome": "Children group rocks by their properties and justify the choice.",
        },
        expected_count=2,
        coverage=("compare and group together different kinds of rocks",),
    )


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


def a_lesson(objective=OBJECTIVE_ONE, number=1):
    payload = {
        "objective": objective,
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
            {"misconception": "Heavier means harder", "why": "Both feel physical",
             "address": "Chalk against granite"}
        ],
        "assessment": {
            "look_for": "A group heading naming a property rather than a colour",
            "not_yet_example": "Three rocks grouped under 'nice ones'",
        },
        "adaptations": {
            "eal": "Word bank with a photograph beside each property word",
            "send": "Pre-sorted pair of very different rocks to start from",
            "stretch": "Offer permeable and ask them to test it with a pipette",
        },
        "resources": [{"item": "Rock samples", "quantity": "6 sets of 4"}],
        "next_lesson": "Testing hardness by scratching",
        "number": number,
    }
    return validate_lesson(payload, expected_objective=objective, lesson_minutes=60)


def a_worksheet(lesson):
    payload = {
        "title": "Rock Detectives",
        "objective": lesson.objective,
        "success_criteria": [CRITERION_ONE, CRITERION_TWO],
        "sections": [
            {
                "title": "Part 1 — Describing",
                "instructions": INSTRUCTION,
                "sentences": [
                    {
                        "pieces": [
                            {"type": "text", "text": "Granite feels "},
                            {"type": "blank", "answer": "rough", "hint": "not smooth"},
                            {"type": "text", "text": " when you touch it."},
                        ]
                    }
                ],
            }
        ],
        "word_bank": {"words": ["hard", "soft", "rough"]},
        "evidence": [
            {
                "criterion": CRITERION_ONE,
                "where": "Part 1 — Describing",
                "quote": INSTRUCTION,
                "pupil_writes": "Two property words in each row",
            },
            {
                "criterion": CRITERION_TWO,
                "where": "Part 1 — Describing",
                "quote": "Granite feels ___ when you touch it.",
                "pupil_writes": "The property word that fits",
            },
        ],
    }
    return validate_coupled_worksheet(payload, lesson=lesson, worksheet_type="cloze")


HOSTED = os.getenv("LIBRARY_TEST_URL")


@pytest.fixture
def library(tmp_path):
    """The file while building; the real hosted database when one is offered.

    ⚠️ **The reason this switch exists.** The store speaks to two databases, and
    for its first hours only one of them was ever exercised: a positive control
    on 2026-09-04 swapped the Postgres upsert for the SQLite one and **nothing
    failed**, because no test had ever reached Postgres. That is not a passing
    guard, it is an unguarded one.

        LIBRARY_TEST_URL='postgresql://...pooler.supabase.com:5432/postgres' \\
            .venv/bin/python -m pytest tests/test_library.py

    Run it against the Supabase project once it exists, and again after any
    change to this store. Everything else in the suite stays offline.
    """
    if HOSTED:
        engine = open_library(url=library_url(HOSTED))
        with engine.begin() as db:
            db.execute(sqlalchemy.text("DROP TABLE IF EXISTS lessons"))
            db.execute(sqlalchemy.text("DROP TABLE IF EXISTS units"))
        return open_library(url=library_url(HOSTED))
    return open_library(tmp_path / "class_act.sqlite3")


@pytest.fixture
def a_unit():
    lessons = {1: a_lesson(OBJECTIVE_ONE, 1), 2: a_lesson(OBJECTIVE_TWO, 2)}
    return {
        "title": "Rocks and Soils",
        "subject": "Science",
        "year_group": "Year 3",
        "spine": a_spine(),
        "lessons": lessons,
        "worksheets": {1: a_worksheet(lessons[1])},
    }


def _every_string(value, seen=None):
    """Every string anywhere in the object, however deeply nested."""
    import dataclasses

    if seen is None:
        seen = []
    if isinstance(value, str):
        seen.append(value)
    elif dataclasses.is_dataclass(value):
        for f in dataclasses.fields(value):
            _every_string(getattr(value, f.name), seen)
    elif isinstance(value, dict):
        for key, item in value.items():
            _every_string(key, seen)
            _every_string(item, seen)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _every_string(item, seen)
    return seen


class TestItComesBack:
    def test_a_saved_unit_can_be_listed(self, library, a_unit):
        save_unit(library, **a_unit)
        assert [u.title for u in list_units(library)] == ["Rocks and Soils"]

    def test_every_word_of_the_unit_comes_back(self, library, a_unit):
        """⚠️ The test that matters, and the reason it walks rather than names.

        A field added to a lesson later and never stored would be invisible to
        any test that lists the fields it expects. This one fails the moment a
        word she can see stops surviving the round trip.
        """
        unit_id = save_unit(library, **a_unit)
        back = load_unit(library, unit_id)

        for name in ("spine", "lessons", "worksheets"):
            before = _every_string(a_unit[name])
            after = _every_string(getattr(back, name))
            missing = [s for s in before if s not in after]
            assert not missing, f"{name} lost these words: {missing[:3]}"

    def test_the_objective_survives_word_for_word(self, library, a_unit):
        """The one string the whole product rests on, checked on its own."""
        back = load_unit(library, save_unit(library, **a_unit))
        assert back.lessons[1].objective == OBJECTIVE_ONE
        assert back.spine.lessons[0].objective == OBJECTIVE_ONE

    def test_the_worksheet_still_belongs_to_its_lesson(self, library, a_unit):
        back = load_unit(library, save_unit(library, **a_unit))
        assert back.worksheets[1].objective == back.lessons[1].objective

    def test_the_evidence_still_quotes_the_sheet(self, library, a_unit):
        back = load_unit(library, save_unit(library, **a_unit))
        assert back.worksheets[1].evidence[0].quote == INSTRUCTION

    def test_a_lesson_with_no_worksheet_comes_back_without_one(self, library, a_unit):
        back = load_unit(library, save_unit(library, **a_unit))
        assert 2 not in back.worksheets

    def test_the_numbers_are_numbers_not_text(self, library, a_unit):
        """A key that comes back as "1" instead of 1 looks fine and breaks
        every lookup that follows."""
        back = load_unit(library, save_unit(library, **a_unit))
        assert set(back.lessons) == {1, 2}
        assert back.lessons[1].steps[0].minutes == 20


class TestSheCanKeepWorking:
    def test_saving_the_same_unit_again_updates_it(self, library, a_unit):
        """She replans, she does not accumulate seven copies of one unit."""
        unit_id = save_unit(library, **a_unit)
        again = save_unit(library, unit_id=unit_id, **{**a_unit, "title": "Rocks & Soils"})
        assert again == unit_id
        assert [u.title for u in list_units(library)] == ["Rocks & Soils"]

    def test_a_lesson_can_be_marked_taught(self, library, a_unit):
        unit_id = save_unit(library, **a_unit)
        set_lesson_status(library, unit_id, 1, "taught")
        assert load_unit(library, unit_id).status[1] == "taught"

    def test_a_lesson_starts_as_planned(self, library, a_unit):
        back = load_unit(library, save_unit(library, **a_unit))
        assert back.status == {1: "planned", 2: "planned"}

    def test_planned_is_never_silently_treated_as_taught(self, library, a_unit):
        """A recorded decision: the tool must lose a feature visibly rather
        than quietly start lying about what happened in the room."""
        unit_id = save_unit(library, **a_unit)
        set_lesson_status(library, unit_id, 1, "taught")
        back = load_unit(library, unit_id)
        assert back.status[2] == "planned"

    def test_an_unknown_status_is_refused(self, library, a_unit):
        unit_id = save_unit(library, **a_unit)
        with pytest.raises(ValueError):
            set_lesson_status(library, unit_id, 1, "sort of taught")

    def test_re_saving_keeps_what_was_taught(self, library, a_unit):
        """Regenerating a lesson must not quietly forget that she taught it."""
        unit_id = save_unit(library, **a_unit)
        set_lesson_status(library, unit_id, 1, "taught")
        save_unit(library, unit_id=unit_id, **a_unit)
        assert load_unit(library, unit_id).status[1] == "taught"

    def test_a_unit_can_be_deleted(self, library, a_unit):
        unit_id = save_unit(library, **a_unit)
        delete_unit(library, unit_id)
        assert list_units(library) == []

    def test_loading_something_that_is_not_there_says_so(self, library):
        with pytest.raises(UnitNotFound):
            load_unit(library, 999)

    def test_deleting_a_unit_takes_its_lessons_with_it(self, library, a_unit):
        """Counted in the file, not inferred from what loads.

        Checking that the next unit looks right would pass with every lesson
        still sitting there orphaned, because a new unit gets a new number and
        never looks at them.
        """
        delete_unit(library, save_unit(library, **a_unit))
        with library.connect() as db:
            left = db.execute(sqlalchemy.select(sqlalchemy.func.count()).select_from(
                sqlalchemy.table("lessons"))).scalar()
        assert left == 0

    def test_a_lesson_she_removed_does_not_come_back(self, library, a_unit):
        """Re-planning a shorter unit has to shorten it in the file too."""
        unit_id = save_unit(library, **a_unit)
        shorter = {**a_unit, "lessons": {1: a_unit["lessons"][1]}, "worksheets": {}}
        save_unit(library, unit_id=unit_id, **shorter)
        assert set(load_unit(library, unit_id).lessons) == {1}


class TestWhatIsStored:
    def test_no_pupil_data_reaches_the_database(self, library, a_unit):
        """A recorded decision: no names, no EHCP records, no pupil-level data.
        Nothing saved here has a place to put one — this is the control that
        keeps it that way when reflections are added on top later. Runs against
        the hosted database too, because that is where it would matter."""
        save_unit(library, **a_unit)
        inspector = sqlalchemy.inspect(library)
        columns = {
            column["name"]
            for table in inspector.get_table_names()
            for column in inspector.get_columns(table)
        }
        assert columns, "no tables at all — this would pass vacuously"
        assert not {"pupil", "pupils", "child", "children", "names", "send", "ehcp"} & columns


@pytest.mark.skipif(bool(HOSTED), reason="about the local file, not the hosted database")
class TestTheFileItself:
    def test_it_survives_the_app_being_closed(self, tmp_path, a_unit):
        """The whole point. A second connection, as a new session would open."""
        path = tmp_path / "class_act.sqlite3"
        unit_id = save_unit(open_library(path), **a_unit)
        assert load_unit(open_library(path), unit_id).lessons[1].objective == OBJECTIVE_ONE

    def test_it_makes_its_own_folder(self, tmp_path, a_unit):
        path = tmp_path / "data" / "class_act.sqlite3"
        save_unit(open_library(path), **a_unit)
        assert pathlib.Path(path).exists()

    def test_the_file_is_not_left_readable_as_plain_text(self, tmp_path, a_unit):
        """Not encryption — a check that the unit really went into the database
        rather than beside it. A store that silently wrote nothing would pass
        every test above by keeping the objects in memory."""
        path = tmp_path / "class_act.sqlite3"
        save_unit(open_library(path), **a_unit)
        assert path.stat().st_size > 0
