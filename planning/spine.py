"""The unit spine — the chain of objectives, before any lesson is written.

A unit is planned in one pass so that it hangs together, but not in one call.
The spine comes first: what each lesson's objective is, which earlier lesson it
needs, and why. It is small, it is fast, and it is the part worth the teacher's
judgement — so she reads and edits it before anything longer is generated off
the back of it.

Two things make this worth having as its own step.

**It is checkable.** A sequence has structure a program can verify without an
opinion: a lesson cannot build on one that comes after it, a six-lesson request
cannot come back with five, the same objective cannot be taught twice, and a
unit cannot claim to cover something the school's scheme never mentioned. None
of that is a judgement about teaching. All of it has shipped in tools that
looked fine on screen.

**Maths never reaches the model.** White Rose is mandated and its order is tied
to the school's calculation policy, so `build_locked_spine` assembles the spine
directly from the small steps she typed, in her order, word for word. The only
guarantee that an order cannot be invented is that nothing in the path is
capable of inventing one — an instruction not to re-sequence is a request, and
this is a property.

Nothing here judges whether the teaching is good. That is shown to the teacher,
side by side and editable, and labelled "AI-drafted — check before teaching".
"""

from dataclasses import dataclass, field, replace

from llm.client import generate_structured_content

# Subjects whose sequence the school mandates. Kept here as well as in
# `anchors.py` so that a caller who skipped the anchor check still cannot get a
# maths sequence invented -- see `generate_spine`.
LOCKED_SUBJECTS = {"Maths"}


class SpineError(ValueError):
    """The sequence is not usable as a sequence."""


@dataclass(frozen=True)
class SpineLesson:
    """One link in the chain.

    `builds_on_reason` is the part the teacher actually judges. "Builds on L2"
    is a link; *"grouping must be secure before it can be justified"* is a claim
    about her class that she can agree or disagree with.
    """

    number: int
    objective: str
    builds_on: int | None
    builds_on_reason: str
    covers: list = field(default_factory=list)
    assesses_outcome: bool = False


@dataclass(frozen=True)
class UnitSpine:
    """The whole chain, plus where it came from."""

    lessons: list
    outcome: str = ""
    source: str = ""


SPINE_SYSTEM_PROMPT = (
    "You are an experienced UK primary teacher planning a unit for a Year 3 "
    "class with many EAL and SEND pupils and a wide ability range. You sequence "
    "objectives so that each lesson genuinely needs the one before it, rather "
    "than listing six things about a topic. You never invent coverage a scheme "
    "did not name. You reply with JSON only, and no commentary."
)


def build_spine_prompt(
    subject,
    year_group,
    lesson_count,
    outcome,
    objectives=(),
    coverage=(),
    scheme=None,
    unit_title=None,
    build_on="",
):
    """Ask for the chain of objectives, and nothing longer.

    The instruction that carries the weight is **why**, not which. A sequence
    where every lesson says "builds on the last one" is not a sequence; the
    reason is what the teacher reads to decide whether the order is right for
    her class, and it is the only part of this she can meaningfully disagree
    with.
    """
    parts = [
        f"Plan the spine of a {lesson_count}-lesson {year_group} {subject} unit.",
        "",
        "The spine is the chain of objectives only — no activities, no lesson "
        "detail, no success criteria. Those come later.",
        "",
        f"The unit ends when: {outcome.strip()}"
        if outcome and outcome.strip()
        else "No end-of-unit outcome was given; the last lesson should assess "
        "the unit's main objective.",
    ]

    if unit_title:
        parts += ["", f"Unit title, as the school has it: {unit_title}"]

    if coverage:
        parts += [
            "",
            f"The {scheme or 'school'} scheme says this unit covers the "
            "following. A lesson may only claim coverage from this list — never "
            "add to it. Try to cover every line, but do not attach a line to a "
            "lesson that does not teach it: a line left out is shown to the "
            "teacher as an honest gap, which is far better than a coverage "
            "record that says a lesson taught something it did not.",
        ]
        parts += [f"  - {line}" for line in coverage]

    if objectives:
        parts += [
            "",
            "National Curriculum objectives this unit sits under:",
        ]
        parts += [f"  - {line}" for line in objectives]

    if build_on and build_on.strip():
        parts += [
            "",
            "What happened last time this class was taught related content — "
            "use it to decide what needs re-teaching or more modelling:",
            f"  {build_on.strip()}",
        ]

    parts += [
        "",
        f"Return JSON only, with exactly {lesson_count} lessons, in this shape:",
        "{",
        '  "lessons": [',
        "    {",
        '      "number": 1,',
        '      "objective": "what the children will be able to do, in one line",',
        '      "builds_on": null,',
        '      "builds_on_reason": "why this lesson needs that one — what the '
        'children must already be secure in before this can be taught",',
        '      "covers": ["the scheme coverage lines this lesson teaches"],',
        '      "assesses_outcome": false',
        "    }",
        "  ]",
        "}",
        "",
        f"Number the lessons 1 to {lesson_count} in order. Lesson 1 has "
        '"builds_on": null. Every other lesson builds on an earlier lesson '
        "number, and says why in terms of what the children must already be "
        "able to do. Only the last lesson has \"assesses_outcome\": true. No "
        "two lessons may share an objective.",
    ]
    return "\n".join(parts)


def validate_spine(payload, expected_count, coverage=()):
    """Check a sequence is a sequence before anything is built on it.

    Everything here is structural. Nothing in this function has an opinion about
    whether the teaching is any good -- that is the teacher's, and the spine is
    shown to her for exactly that reason.
    """
    if not isinstance(payload, dict):
        raise SpineError("The spine is not an object.")

    raw = payload.get("lessons")
    if not isinstance(raw, list) or not raw:
        raise SpineError("The spine has no lessons in it.")

    if len(raw) != expected_count:
        raise SpineError(
            f"Asked for {expected_count} lessons and got {len(raw)}. A short "
            f"unit would render as if it were the whole one."
        )

    lessons = [_read_lesson(item, position) for position, item in enumerate(raw, 1)]

    _check_objectives_are_distinct(lessons)
    _check_the_chain(lessons)
    _check_the_outcome(lessons)
    if coverage:
        _check_coverage(lessons, coverage)

    return UnitSpine(lessons=lessons, outcome=str(payload.get("outcome", "")).strip())


def _read_lesson(item, position):
    if not isinstance(item, dict):
        raise SpineError(f"Lesson {position} is not an object.")

    number = item.get("number")
    if number != position:
        raise SpineError(
            f"Lesson numbers must run 1 to n in order; position {position} is "
            f"numbered {number!r}."
        )

    objective = str(item.get("objective", "")).strip()
    if not objective:
        raise SpineError(f"Lesson {position} has no objective.")

    builds_on = item.get("builds_on")
    if builds_on is not None and not isinstance(builds_on, int):
        raise SpineError(
            f"Lesson {position} builds on {builds_on!r}, which is not a lesson "
            f"number."
        )

    covers = item.get("covers")
    if covers is None:
        covers = []
    if not isinstance(covers, list) or any(not isinstance(c, str) for c in covers):
        raise SpineError(f"Lesson {position}'s coverage is not a list of lines.")

    return SpineLesson(
        number=position,
        objective=objective,
        builds_on=builds_on,
        builds_on_reason=str(item.get("builds_on_reason", "")).strip(),
        covers=[c.strip() for c in covers if c.strip()],
        assesses_outcome=bool(item.get("assesses_outcome")),
    )


def _check_objectives_are_distinct(lessons):
    seen = {}
    for lesson in lessons:
        key = " ".join(lesson.objective.lower().split())
        if key in seen:
            raise SpineError(
                f"Lessons {seen[key]} and {lesson.number} teach the same "
                f"objective. Six lessons on one objective is a sequence in name "
                f"only."
            )
        seen[key] = lesson.number


def _check_the_chain(lessons):
    """The one check that catches a sequence which is not one.

    A lesson pointing forwards reads perfectly on screen and teaches in an order
    nothing supports.
    """
    for lesson in lessons:
        if lesson.number == 1:
            if lesson.builds_on is not None:
                raise SpineError(
                    "Lesson 1 builds on "
                    f"lesson {lesson.builds_on}, but nothing comes before it."
                )
            continue

        if lesson.builds_on is None:
            raise SpineError(
                f"Lesson {lesson.number} builds on nothing. Every lesson after "
                f"the first has to need one before it."
            )
        if lesson.builds_on >= lesson.number:
            raise SpineError(
                f"Lesson {lesson.number} builds on lesson {lesson.builds_on}, "
                f"which comes later. A lesson cannot need something taught "
                f"after it."
            )
        if lesson.builds_on < 1:
            raise SpineError(
                f"Lesson {lesson.number} builds on lesson {lesson.builds_on}, "
                f"which does not exist."
            )
        if not lesson.builds_on_reason:
            raise SpineError(
                f"Lesson {lesson.number} does not say why it needs lesson "
                f"{lesson.builds_on}. The reason is the part worth reading."
            )


def _check_the_outcome(lessons):
    assessing = [lesson.number for lesson in lessons if lesson.assesses_outcome]
    if not assessing:
        raise SpineError(
            "No lesson assesses the end-of-unit outcome, so the unit never "
            "checks the thing it was built to teach."
        )
    if assessing != [lessons[-1].number]:
        raise SpineError(
            f"The end-of-unit outcome is assessed by lesson(s) {assessing}. It "
            f"is what the unit ends on, so it belongs to lesson "
            f"{lessons[-1].number} and no other."
        )


def _check_coverage(lessons, coverage):
    """A lesson may only claim coverage the scheme actually named.

    Omission is reported by `coverage_map` and left to her. Invention is
    rejected here, because the coverage record is her evidence to a subject
    leader and an added line would be read as the school's own plan.
    """
    allowed = set(coverage)
    for lesson in lessons:
        for claim in lesson.covers:
            if claim not in allowed:
                raise SpineError(
                    f"Lesson {lesson.number} says it covers {claim!r}, which is "
                    f"not in the scheme's coverage. Coverage may not be added to."
                )


def coverage_map(spine, coverage):
    """Every line the scheme named, and which lessons teach it.

    Her evidence to the subject leader that nothing was dropped — so a line no
    lesson teaches comes back with an empty list, never left out. A map missing
    a line is the same failure as dropping it.
    """
    return {
        line: [lesson.number for lesson in spine.lessons if line in lesson.covers]
        for line in coverage
    }


def coverage_never_taught(spine, coverage):
    """Scheme lines whose only lesson is the one that assesses the outcome.

    Found on the first live run. Told that every line had to be taught by at
    least one lesson, the draft attached *"recognise that soils are made from
    rocks"* to a final lesson about grouping rocks by property. The line was
    dropped in substance while the coverage map vouched for it -- worse than an
    honest gap, because the map is the artefact she would show a subject leader.

    Nothing here reads an objective and decides whether it teaches something:
    that is a judgement, and it is hers. This is structural. If a line appears
    only in the lesson that assesses the unit, the children were assessed on it
    without ever being taught it.

    A one-lesson unit cannot trip this -- its only lesson is also its
    assessment, so flagging everything would be noise rather than a finding.
    """
    if len(spine.lessons) < 2:
        return []

    taught_earlier = {line for lesson in spine.lessons[:-1] for line in lesson.covers}
    assessed = set(spine.lessons[-1].covers)
    return [
        line for line in coverage if line in assessed and line not in taught_earlier
    ]


def approved_spine(spine, objectives):
    """The spine as she edited it, which is the one the lessons are written from.

    Without this the approval step is decoration: she would change a sentence on
    screen and the lesson would still be written from the one she rejected.

    Only the wording changes. The chain, the coverage and which lesson assesses
    the outcome are the sequence she already accepted -- editing an objective is
    rewording a lesson, not re-deciding the unit.

    Args:
        objectives: `{lesson number: text}`. Absent numbers keep their draft.
    """
    lessons = []
    for lesson in spine.lessons:
        objective = str(objectives.get(lesson.number, lesson.objective)).strip()
        if not objective:
            raise SpineError(f"Lesson {lesson.number} has no objective on it.")
        lessons.append(replace(lesson, objective=objective))

    seen = {}
    for lesson in lessons:
        key = " ".join(lesson.objective.lower().split())
        if key in seen:
            raise SpineError(
                f"Lessons {seen[key]} and {lesson.number} now have the same "
                f"objective."
            )
        seen[key] = lesson.number

    return UnitSpine(
        lessons=lessons,
        outcome=spine.outcome,
        source=f"{spine.source} Objectives as you approved them.",
    )


def build_locked_spine(steps, outcome, scheme="White Rose"):
    """The spine for a mandated scheme, assembled rather than generated.

    No model call. The steps she typed become the objectives word for word, in
    the order she typed them. The reason each lesson needs the last is stated as
    what it is -- the scheme's order -- because we know the school teaches them
    in this sequence and we do not know why, and inventing a pedagogical reason
    would be putting words in the scheme's mouth.
    """
    objectives = [line.strip() for line in steps if line and line.strip()]
    if not objectives:
        raise SpineError(f"No {scheme} steps given. Type one step per line.")

    seen = set()
    for objective in objectives:
        key = " ".join(objective.lower().split())
        if key in seen:
            raise SpineError(f"{objective!r} is listed twice.")
        seen.add(key)

    last = len(objectives)
    lessons = [
        SpineLesson(
            number=number,
            objective=objective,
            builds_on=None if number == 1 else number - 1,
            builds_on_reason=(
                "" if number == 1 else f"{scheme} teaches these steps in this order."
            ),
            covers=[objective],
            assesses_outcome=(number == last),
        )
        for number, objective in enumerate(objectives, 1)
    ]
    return UnitSpine(
        lessons=lessons,
        outcome=(outcome or "").strip(),
        source=f"{scheme}, in the order you listed. Not re-sequenced.",
    )


def generate_spine(
    subject,
    year_group,
    lesson_count,
    outcome,
    objectives=(),
    coverage=(),
    scheme=None,
    unit_title=None,
    build_on="",
):
    """Draft the chain of objectives, then check it before returning it.

    Raises:
        SpineError: the subject's sequence is mandated, there is nothing to
            build from, or what came back is not a usable sequence.
    """
    if subject in LOCKED_SUBJECTS:
        # Reached only if a caller skipped the anchor check. Refusing here means
        # there is no route through this module that can invent a maths order.
        raise SpineError(
            f"{subject} follows White Rose, which is locked. Use the scheme's "
            f"small steps rather than drafting a sequence."
        )

    if not objectives and not coverage:
        raise SpineError(
            "Nothing to build a unit from. Choose the objectives it covers, or "
            "read the scheme plan first."
        )

    payload = generate_structured_content(
        build_spine_prompt(
            subject=subject,
            year_group=year_group,
            lesson_count=lesson_count,
            outcome=outcome,
            objectives=objectives,
            coverage=coverage,
            scheme=scheme,
            unit_title=unit_title,
            build_on=build_on,
        ),
        SPINE_SYSTEM_PROMPT,
    )
    spine = validate_spine(payload, expected_count=lesson_count, coverage=coverage)
    return UnitSpine(
        lessons=spine.lessons,
        outcome=(outcome or "").strip(),
        source="AI-drafted — check before teaching.",
    )
