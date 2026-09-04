"""The units she has planned, still there tomorrow.

Until this existed nothing was saved. She could read a scheme, approve a
sequence, wait several minutes while every lesson was written, generate the
worksheets — and lose all of it by closing the tab.

**The risk here is not losing a unit. It is handing one back slightly
different.** Everything else in this project is built so that the objective she
approved is the objective on the lesson, on the worksheet, and in the child's
book — checked word for word at every handover. Saving is one more handover, and
a criterion that comes back quietly reworded would break the chain in the one
place nobody is watching, because a plan that loads *looks* like it worked.

Three decisions carry that:

**What is stored is what the validators produced**, turned to JSON by walking
the dataclasses rather than by any hand-written description of them. Nothing
re-derives, re-words or re-formats on the way in.

**What is rebuilt is driven by one map** (`_INSIDE`), not by ten constructors
that would each have to be remembered when a field is added. A field added to a
lesson and never stored fails `test_every_word_of_the_unit_comes_back`, which
walks the objects instead of naming them.

**One set of SQL, two databases.** A file on disk while it is being built and
tested, and Supabase once it is hosted — see `library_url()`. They are the same
code through SQLAlchemy rather than two hand-written dialects, because the
differences are real (auto-numbering, foreign-key enforcement, parameter style)
and two definitions of the same thing is how today's two dead-code findings
happened. The whole suite runs against the file, offline and in under a second;
the same tests run against Postgres when a URL is set.

⚠️ **Deliberately not stored: anything about a child.** No names, no SEND
detail, no EHCP records — a recorded decision, and there is nowhere here to put
one. When reflections are added on top, that stays true: tick-boxes first, free
text warned and previewed. There is a test on the column names so it cannot
drift quietly.

`status` is `planned | taught | skipped`, and **"planned" is never silently
treated as "not taught"** — she says which, and re-planning a unit keeps what
she already told us about the lessons in it.
"""

import dataclasses
import datetime as dt
import json
import os
import pathlib

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    case,
    create_engine,
    delete,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from planning.lesson import (
    Assessment,
    Criterion,
    Lesson,
    LessonStep,
    Question,
    Vocabulary,
    WatchFor,
)
from planning.spine import SpineLesson, UnitSpine
from planning.worksheet import CoupledWorksheet, EvidenceClaim

DEFAULT_PATH = pathlib.Path("data/class_act.sqlite3")

# Where the library lives when it is hosted. Set in the hosting's own secrets
# box, never in the repository.
#
# ⚠️ Use Supabase's **session pooler** string, port 5432 -- the host that looks
# like `aws-<region>.pooler.supabase.com`. The obvious one, the direct
# `db.<project>.supabase.co` string, is IPv6-only unless the paid IPv4 add-on
# is on, and Streamlit's hosting is IPv4-only: it would work on the machine it
# was written on and fail once deployed, which is the worst shape of bug there
# is. Confirmed against Supabase's connection docs on 2026-09-04.
LIBRARY_URL_SETTING = "LIBRARY_URL"

# What she can say about a lesson. Not a free-text field: "planned" and
# "taught" have to stay distinguishable, because the next plan reads them.
STATUSES = ("planned", "taught", "skipped")

# The one place that says what lives inside a list or a field that JSON cannot
# tell apart from a plain dict. A dataclass reached from here is rebuilt as
# itself; anything absent is left exactly as stored, which is right for the
# parts that really are plain dicts (misconceptions, resources, adaptations,
# and the worksheet's rendered content).
_INSIDE = {
    (UnitSpine, "lessons"): SpineLesson,
    (Lesson, "success_criteria"): Criterion,
    (Lesson, "steps"): LessonStep,
    (Lesson, "vocabulary"): Vocabulary,
    (Lesson, "assessment"): Assessment,
    (LessonStep, "questions"): Question,
    (LessonStep, "watch_for"): WatchFor,
    (CoupledWorksheet, "success_criteria"): Criterion,
    (CoupledWorksheet, "evidence"): EvidenceClaim,
}

_SCHEMA = MetaData()

UNITS = Table(
    "units", _SCHEMA,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("title", String(300), nullable=False),
    Column("subject", String(100), nullable=False),
    Column("year_group", String(50), nullable=False),
    Column("spine", Text, nullable=False),
    Column("created", String(32), nullable=False),
    Column("updated", String(32), nullable=False),
)

LESSONS = Table(
    "lessons", _SCHEMA,
    Column("unit_id", Integer, ForeignKey("units.id", ondelete="CASCADE"),
           primary_key=True),
    Column("number", Integer, primary_key=True),
    Column("status", String(20), nullable=False, default="planned"),
    Column("lesson", Text, nullable=False),
    Column("worksheet", Text, nullable=True),
)


class UnitNotFound(LookupError):
    """Asked for a unit that is not in the library."""


@dataclasses.dataclass(frozen=True)
class UnitSummary:
    """One line on the "units you have planned" list."""

    id: int
    title: str
    subject: str
    year_group: str
    lessons: int
    taught: int
    updated: str


@dataclasses.dataclass(frozen=True)
class SavedUnit:
    id: int
    title: str
    subject: str
    year_group: str
    spine: UnitSpine
    lessons: dict
    worksheets: dict
    status: dict


def library_url(setting=None):
    """Supabase when it is hosted, a file on disk when it is not.

    Reading the setting rather than choosing in code is what lets the whole
    suite run offline against the same statements production uses.
    """
    hosted = setting or _hosted_setting()
    if hosted:
        # Supabase hands out `postgres://`, which SQLAlchemy dropped in 2.0.
        if hosted.startswith("postgres://"):
            hosted = "postgresql+psycopg://" + hosted[len("postgres://"):]
        elif hosted.startswith("postgresql://"):
            hosted = "postgresql+psycopg://" + hosted[len("postgresql://"):]
        return hosted
    return None


def _hosted_setting():
    try:
        import streamlit as st

        if LIBRARY_URL_SETTING in st.secrets:
            return st.secrets[LIBRARY_URL_SETTING]
    except Exception:  # noqa: BLE001 - no secrets file at all is normal locally
        pass
    return os.getenv(LIBRARY_URL_SETTING)


def open_library(path=None, url=None):
    """The library, made if it is not there yet.

    Give it nothing and it uses the hosted database when one is configured and
    the local file when one is not.
    """
    url = url or library_url()
    if url is None:
        path = pathlib.Path(path or DEFAULT_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite+pysqlite:///{path}"

    engine = create_engine(url, future=True)
    if engine.dialect.name == "sqlite":
        # SQLite leaves foreign keys off by default, and with them off deleting
        # a unit silently orphans every lesson in it. Postgres always enforces
        # them. Measured: turning this off breaks the deletion test.
        from sqlalchemy import event

        @event.listens_for(engine, "connect")
        def _enforce_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.close()

    _SCHEMA.create_all(engine)
    return engine


def save_unit(library, title, subject, year_group, spine, lessons,
              worksheets=None, unit_id=None):
    """Write the unit, replacing the one it came from rather than adding a copy.

    Re-planning keeps what she has already said about each lesson: a lesson she
    marked taught is still marked taught when its plan is rewritten, because
    what happened in the room did not stop having happened.
    """
    worksheets = worksheets or {}
    now = dt.datetime.now().isoformat(timespec="seconds")

    with library.begin() as db:
        if unit_id is None:
            unit_id = db.execute(
                insert(UNITS).values(
                    title=title, subject=subject, year_group=year_group,
                    spine=_to_json(spine), created=now, updated=now,
                ).returning(UNITS.c.id)
            ).scalar_one()
        else:
            changed = db.execute(
                update(UNITS).where(UNITS.c.id == unit_id).values(
                    title=title, subject=subject, year_group=year_group,
                    spine=_to_json(spine), updated=now,
                )
            )
            if not changed.rowcount:
                raise UnitNotFound(f"There is no saved unit numbered {unit_id}.")

        numbers = [int(n) for n in lessons]
        # Gone from the plan means gone from the library. A lesson she deleted
        # must not reappear the next time she opens the unit.
        db.execute(
            delete(LESSONS).where(
                LESSONS.c.unit_id == unit_id, LESSONS.c.number.notin_(numbers)
            )
        )
        for number, lesson in lessons.items():
            sheet = worksheets.get(number)
            row = {
                "unit_id": unit_id,
                "number": int(number),
                "status": "planned",
                "lesson": _to_json(lesson),
                "worksheet": _to_json(sheet) if sheet else None,
            }
            upsert = (
                postgres_insert if library.dialect.name == "postgresql" else sqlite_insert
            )(LESSONS).values(**row)
            # `status` is deliberately absent from the update: rewriting a
            # lesson's plan says nothing about whether she taught it, and what
            # happened in the room did not stop having happened. Leaving the
            # column alone is what keeps it, so do not "tidy" it into the list.
            db.execute(
                upsert.on_conflict_do_update(
                    index_elements=[LESSONS.c.unit_id, LESSONS.c.number],
                    set_={"lesson": row["lesson"], "worksheet": row["worksheet"]},
                )
            )
    return unit_id


def list_units(library):
    """Every unit she has planned, newest first."""
    taught = func.sum(case((LESSONS.c.status == "taught", 1), else_=0))
    with library.connect() as db:
        rows = db.execute(
            select(
                UNITS.c.id, UNITS.c.title, UNITS.c.subject, UNITS.c.year_group,
                UNITS.c.updated, func.count(LESSONS.c.number), taught,
            )
            .select_from(UNITS.outerjoin(LESSONS, LESSONS.c.unit_id == UNITS.c.id))
            .group_by(UNITS.c.id, UNITS.c.title, UNITS.c.subject,
                      UNITS.c.year_group, UNITS.c.updated)
            .order_by(UNITS.c.updated.desc(), UNITS.c.id.desc())
        ).all()
    return [
        UnitSummary(
            id=row[0], title=row[1], subject=row[2], year_group=row[3],
            updated=row[4], lessons=row[5] or 0, taught=int(row[6] or 0),
        )
        for row in rows
    ]


def load_unit(library, unit_id):
    """The unit as she left it."""
    with library.connect() as db:
        row = db.execute(
            select(UNITS.c.title, UNITS.c.subject, UNITS.c.year_group, UNITS.c.spine)
            .where(UNITS.c.id == unit_id)
        ).first()
        if row is None:
            raise UnitNotFound(f"There is no saved unit numbered {unit_id}.")

        taught = db.execute(
            select(LESSONS.c.number, LESSONS.c.status, LESSONS.c.lesson,
                   LESSONS.c.worksheet)
            .where(LESSONS.c.unit_id == unit_id)
            .order_by(LESSONS.c.number)
        ).all()

    lessons, worksheets, status = {}, {}, {}
    for number, state, lesson, worksheet in taught:
        lessons[number] = _rebuild(Lesson, json.loads(lesson))
        status[number] = state
        if worksheet:
            worksheets[number] = _rebuild(CoupledWorksheet, json.loads(worksheet))

    return SavedUnit(
        id=unit_id, title=row[0], subject=row[1], year_group=row[2],
        spine=_rebuild(UnitSpine, json.loads(row[3])),
        lessons=lessons, worksheets=worksheets, status=status,
    )


def set_lesson_status(library, unit_id, number, status):
    """What actually happened to this lesson."""
    if status not in STATUSES:
        raise ValueError(
            f"{status!r} is not something a lesson can be. It is one of: "
            + ", ".join(STATUSES)
        )
    with library.begin() as db:
        changed = db.execute(
            update(LESSONS)
            .where(LESSONS.c.unit_id == unit_id, LESSONS.c.number == int(number))
            .values(status=status)
        )
    if not changed.rowcount:
        raise UnitNotFound(
            f"There is no lesson {number} in the unit numbered {unit_id}."
        )


def delete_unit(library, unit_id):
    """Hers to remove, and it takes its lessons with it.

    The lessons go by the cascade declared on the table. Deleting them here as
    well looked like prudence and was measured to be dead code: the mutation
    that removed it broke nothing, because the cascade had already done it.
    """
    with library.begin() as db:
        db.execute(delete(UNITS).where(UNITS.c.id == unit_id))


def _to_json(value):
    """The object as it stands, with nothing re-derived on the way."""
    return json.dumps(dataclasses.asdict(value), ensure_ascii=False)


def _rebuild(cls, value):
    """The object again, field for field.

    Driven by `_INSIDE` rather than by a constructor per class, so a field
    added to a lesson is stored and restored without anyone remembering to come
    back here. A field the file does not have is left at its default, which is
    what lets a unit saved by an older version still open.
    """
    if not isinstance(value, dict):
        return value

    known = {f.name for f in dataclasses.fields(cls)}
    built = {}
    for name, item in value.items():
        if name not in known:
            # Written by a later version than this one. Ignored rather than
            # passed on, because an unexpected argument would refuse to open
            # the unit entirely.
            continue
        inside = _INSIDE.get((cls, name))
        if inside is None:
            built[name] = item
        elif isinstance(item, list):
            built[name] = [_rebuild(inside, entry) for entry in item]
        else:
            built[name] = _rebuild(inside, item)
    return cls(**built)
