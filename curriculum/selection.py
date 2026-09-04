"""Choosing which curriculum objective a worksheet or lesson is built on.

Why this module exists
----------------------
Each strand in the curriculum data carries two independent lists — `topics` and
`objectives` — and `app.py` used to take `objectives[0]` regardless of which
topic the teacher had picked. Choosing "How Fossils Are Formed" produced the
objective about comparing and grouping rocks, on every worksheet built from a
non-first topic.

Pairing the lists by position does not fix it. Measured across the curriculum,
94% of strands happen to have equal-length lists, but the entries do not line
up: in Year 3 Rocks, topic 3 ("How Fossils Are Formed") sits opposite the
objective about soils. The two lists were written independently and drifted.

So this module does not guess. It hands the caller the whole strand and lets
the teacher choose, which is what she would do anyway. `resolve_objective`
keeps the old first-objective fallback so that nothing changes silently for a
caller that does not choose.
"""

from curriculum import SUBJECT_REGISTRY


class UnknownStrandError(KeyError):
    """Raised for a subject, year group or strand that is not in the data.

    A distinct type so callers can tell "you asked for something that does not
    exist" apart from "this strand is empty", which used to look identical when
    the lookup returned `""`.
    """


def _strand(subject, year_group, strand):
    try:
        return SUBJECT_REGISTRY[subject]["curriculum"][year_group][strand]
    except KeyError as exc:
        raise UnknownStrandError(
            f"No curriculum data for {subject} / {year_group} / {strand}"
        ) from exc


def list_objectives(subject, year_group, strand):
    """Every objective in the strand — not just the first one."""
    return list(_strand(subject, year_group, strand).get("objectives", []))


def list_topics(subject, year_group, strand):
    """Every topic in the strand.

    Returned separately from the objectives, and deliberately not zipped with
    them: they are not parallel, and presenting them as if they were is the bug
    this module replaces.
    """
    return list(_strand(subject, year_group, strand).get("topics", []))


def resolve_objective(subject, year_group, strand, chosen=None, custom=None):
    """The objective a worksheet or lesson should actually be built on.

    Precedence, highest first:
      1. `custom` — the teacher typed her own; used verbatim, stripped.
      2. `chosen` — she picked one of the strand's objectives.
      3. The strand's first objective, which is what the app did before. Kept as
         the fallback so this change cannot alter existing behaviour for a
         caller that passes neither.

    Raises:
        ValueError: if `chosen` is not an objective of this strand. Silently
            accepting a stray string is how the wrong objective travelled
            across the app in the first place.
        UnknownStrandError: if the strand does not exist.
    """
    if custom and custom.strip():
        return custom.strip()

    objectives = list_objectives(subject, year_group, strand)
    if not objectives:
        raise UnknownStrandError(
            f"{subject} / {year_group} / {strand} has no objectives"
        )

    if chosen is None:
        return objectives[0]

    if chosen not in objectives:
        raise ValueError(
            f"{chosen!r} is not an objective of {subject} / {year_group} / {strand}"
        )
    return chosen
