"""A lesson deep enough to teach from.

The first version of this product was rejected in one sentence: *"the bullet
point outline of what the lesson should include — it doesn't speak to what
would actually happen in the lesson."* So the standard is what actually
happens, in order — what is on the board at that moment, the words the teacher
says, the questions with the answers to expect, what the children do, the
common wrong answer and how to respond to it, and where the other adult is.
Deep enough to build slides from.

Two things are load-bearing.

**The objective is hers, word for word.** She approves the spine; each lesson
is written from it; the worksheet is later built from the lesson. A reworded
objective at any of those handovers means the plan, the sheet and the child's
book stop agreeing, and nothing on screen would show it. So the objective is
sent in and checked on the way back, exactly — not similar, not improved.

**The checks are structural and nothing else.** Whether the teaching is any
good is the teacher's judgement, which is why the whole lesson is shown to her
and labelled "AI-drafted — check before teaching". What a program can establish
it establishes hard: the timings add up to the lesson she actually has, success
criteria name evidence rather than effort, vocabulary comes in three bands
because one list is what she said does not work, and the assessment names an
example of work that has *not* met the criterion.

One API call per lesson. A unit of six would not fit in one reply, and a reply
cut short at a tidy point parses perfectly and renders a short lesson.
"""

from dataclasses import dataclass, field

from llm.client import generate_structured_content

# One deep lesson does not fit the worksheet budget. Measured: the sections
# below run past 4,096 tokens routinely, and a truncated reply is refused rather
# than rendered short -- so too small a budget shows up as a failure, not a
# quietly thin lesson.
LESSON_MAX_TOKENS = 8192

# A lesson is streamed, not requested whole. Measured on 2026-09-02: at this
# depth the request ran past the 60-second client default, and raising the
# timeout only moved the failure -- the next attempt was cut off with the server
# closing the connection, which is what a long non-streaming request gets.
# Streaming is Anthropic's own guidance for a long output or a high token
# budget. The timeout stays as a bound on a request that stalls completely;
# because it applies per chunk of a stream, a slow-but-alive reply no longer
# trips it.
LESSON_TIMEOUT = 180.0

# Between 2 and 5. One criterion cannot describe a lesson; six cannot be
# assessed in one, and a criterion nobody checks is decoration.
MIN_CRITERIA = 2
MAX_CRITERIA = 5

# The class this is planned for. Not pupil data -- no names, no records, no
# individuals. It is here because "adapt for EAL and SEND" means nothing without
# it, and because it is the same for every lesson this teacher plans.
CLASS_PROFILE = (
    "A one-form-entry Year 3 class at a Catholic primary in Bromley. Many "
    "pupils have English as an additional language, several have SEND, the "
    "ability range is wide, and motivation is low — ambition in the intake "
    "often stops at 'footballer'. Reading, writing and maths are the school's "
    "focus. There is usually one other adult in the room."
)

# Criteria naming effort rather than evidence. Deliberately a short, unarguable
# list: a child cannot tell whether they met one, and a teacher cannot mark it.
# Anything broader would catch "children only need to say 'lets water through'",
# which is exactly right.
_EFFORT_PHRASES = (
    "worked hard",
    "work hard",
    "tried my best",
    "try my best",
    "did my best",
    "do my best",
    "tried hard",
    "behaved well",
    "was sensible",
    "concentrated well",
)

# Phrases that announce a different goal rather than a different route to the
# same one. Narrow on purpose -- "only need to" appears in correct access
# changes, so it is not here.
_LOWERED_OBJECTIVE_PHRASES = (
    "simpler objective",
    "easier objective",
    "different objective",
    "lower objective",
    "lowered objective",
    "reduced objective",
    "modified objective",
    "alternative objective",
    "simplified objective",
)


class LessonError(ValueError):
    """The lesson is not usable as a lesson."""


@dataclass(frozen=True)
class Question:
    ask: str
    expect: str


@dataclass(frozen=True)
class WatchFor:
    wrong: str
    respond: str


@dataclass(frozen=True)
class LessonStep:
    """One phase of the lesson, with what actually happens in it."""

    name: str
    minutes: int
    on_the_board: str
    teacher_says: str
    children_do: str
    questions: list = field(default_factory=list)
    watch_for: list = field(default_factory=list)
    adults: str = ""
    builds_on_step: str = ""


@dataclass(frozen=True)
class Criterion:
    criterion: str
    evidence: str


@dataclass(frozen=True)
class Vocabulary:
    """Three bands, never one list.

    Her words: *"hard, soft and rough are too easy for some and too difficult
    for others."* A child saying "lets water through" has met the criterion;
    "permeable" exceeds it.
    """

    everyone: list
    expected: list
    stretch: list
    guidance: str


@dataclass(frozen=True)
class Assessment:
    look_for: str
    not_yet_example: str


@dataclass(frozen=True)
class Lesson:
    objective: str
    success_criteria: list
    vocabulary: Vocabulary
    steps: list
    misconceptions: list
    assessment: Assessment
    adaptations: dict
    resources: list
    number: int | None = None
    builds_on: int | None = None
    builds_on_reason: str = ""
    next_lesson: str = ""
    source: str = "AI-drafted — check before teaching."


LESSON_SYSTEM_PROMPT = (
    "You are an experienced UK primary teacher writing a lesson plan another "
    "teacher will teach from tomorrow morning without you there. You write what "
    "actually happens — the words to say, the questions to ask and the answers "
    "to expect, the wrong answer that will come up and what to do about it — "
    "never a description of what a lesson of this kind should contain. You "
    "never change an objective you have been given. You reply with JSON only, "
    "and no commentary."
)


def build_lesson_prompt(
    spine,
    number,
    subject,
    year_group,
    lesson_minutes,
    coverage=(),
    build_on="",
    outcome="",
):
    """Ask for one lesson, in its place in the sequence.

    The whole chain goes in, not just this lesson: a lesson that does not know
    what was taught last week re-teaches it, and one that does not know what is
    coming teaches it early. That is the difference between a unit and six
    lessons about the same topic.
    """
    this = _lesson_in(spine, number)

    before = [lsn for lsn in spine.lessons if lsn.number < number]
    after = [lsn for lsn in spine.lessons if lsn.number > number]

    parts = [
        f"Write lesson {number} of {len(spine.lessons)} in a {year_group} "
        f"{subject} unit. The lesson is {lesson_minutes} minutes long.",
        "",
        "THE OBJECTIVE, which the teacher has already approved. Use it word for "
        "word. Do not reword it, shorten it, or improve it:",
        f"  {this.objective}",
        "",
        f"THE CLASS: {CLASS_PROFILE}",
    ]

    if before:
        parts += ["", "Already taught, so you may assume it and must not re-teach it:"]
        parts += [f"  Lesson {lsn.number}: {lsn.objective}" for lsn in before]
        if this.builds_on:
            parts += [
                "",
                f"This lesson builds on lesson {this.builds_on} — "
                f"{this.builds_on_reason}",
            ]
    else:
        parts += ["", "This is the first lesson of the unit. Assume nothing."]

    if after:
        parts += ["", "Still to come, so do not teach it yet:"]
        parts += [f"  Lesson {lsn.number}: {lsn.objective}" for lsn in after]

    if this.assesses_outcome and outcome:
        parts += ["", f"This is the last lesson, and it assesses: {outcome.strip()}"]

    if coverage:
        parts += ["", "Scheme coverage this lesson is accountable for:"]
        parts += [f"  - {line}" for line in coverage]

    if build_on and build_on.strip():
        parts += [
            "",
            "What happened when this class met related content before — use it "
            "to decide what to re-model or re-teach:",
            f"  {build_on.strip()}",
        ]

    parts += [
        "",
        "Return JSON only, in this shape. Every field is required.",
        "",
        "{",
        f'  "objective": "{this.objective}",',
        '  "success_criteria": [',
        '    {"criterion": "I can ...", "evidence": "what in the lesson shows it"}',
        f"  ],   (between {MIN_CRITERIA} and {MAX_CRITERIA}; each must name "
        "evidence a teacher could look at. Never effort — \"I worked hard\" "
        "cannot be marked)",
        '  "vocabulary": {',
        '    "everyone": ["words every child leaves with, including a child new '
        'to English"],',
        '    "expected": ["words most of the class will use, taught explicitly"],',
        '    "stretch": ["words offered to all and expected of some"],',
        '    "guidance": "how to use the three bands in this lesson"',
        "  },",
        "  (The three bands are an ORDER OF DIFFICULTY: everyone is the "
        "easiest, stretch is the hardest and holds the technical words. A word "
        "belongs in exactly one band. For Year 3 rocks the bands would be "
        "everyone: hard, soft, rough, smooth, shiny, dull — expected: grainy, "
        "layered, absorbent, waterproof, scratch — stretch: permeable, "
        "impermeable, porous, durable. Never put a technical word in "
        "'everyone', an everyday word in 'stretch', or the same word in two "
        "bands. Do not pad 'stretch' by adding a noun to an easier word.)",
        '  "steps": [',
        "    {",
        '      "name": "Hook / Modelling / Practice / Plenary",',
        '      "minutes": 10,',
        '      "on_the_board": "exactly what is displayed at that moment",',
        '      "teacher_says": "the actual words, not a description of them",',
        '      "questions": [{"ask": "the question", "expect": "the answer to '
        'expect"}],',
        '      "children_do": "what the children are doing",',
        '      "watch_for": [{"wrong": "the common wrong answer", "respond": '
        '"what to do about it"}],',
        '      "adults": "where the other adult is and who they are with",',
        '      "builds_on_step": "why this step needs the one before it"',
        "    }",
        f"  ],   (the minutes must add up to exactly {lesson_minutes})",
        '  "misconceptions": [{"misconception": "...", "why": "...", "address": '
        '"..."}],',
        '  "assessment": {',
        '    "look_for": "what to look at in the books",',
        '    "not_yet_example": "an example of work that has NOT met the '
        'criterion, and why"',
        "  },",
        '  "adaptations": {',
        '    "eal": "...", "send": "...", "stretch": "..."',
        "  },   (these change how a child reaches the SAME objective — never a "
        "different or easier objective)",
        '  "resources": [{"item": "...", "quantity": "6 sets of 4"}],',
        '  "next_lesson": "one line on what this sets up"',
        "}",
    ]
    return "\n".join(parts)


def _lesson_in(spine, number):
    for lesson in spine.lessons:
        if lesson.number == number:
            return lesson
    raise LessonError(
        f"There is no lesson {number} in this sequence — it has "
        f"{len(spine.lessons)}."
    )


def validate_lesson(payload, expected_objective, lesson_minutes):
    """Check a lesson before it is shown as one.

    Everything here is structural. Nothing reads the teaching and decides
    whether it is any good.
    """
    expected = (expected_objective or "").strip()
    if not expected:
        raise LessonError("No approved objective to check the lesson against.")

    if not isinstance(payload, dict):
        raise LessonError("The lesson is not an object.")

    objective = str(payload.get("objective", "")).strip()
    if objective != expected:
        # The one guarantee the worksheet coupling later rests on.
        raise LessonError(
            "The lesson came back with a different objective from the one you "
            f"approved.\n  You approved: {expected}\n  It returned:  {objective}"
        )

    criteria = _read_criteria(payload.get("success_criteria"))
    vocabulary = _read_vocabulary(payload.get("vocabulary"))
    steps = _read_steps(payload.get("steps"), lesson_minutes)
    assessment = _read_assessment(payload.get("assessment"))
    adaptations = _read_adaptations(payload.get("adaptations"))
    misconceptions = _read_misconceptions(payload.get("misconceptions"))
    resources = _read_resources(payload.get("resources"))

    return Lesson(
        objective=objective,
        success_criteria=criteria,
        vocabulary=vocabulary,
        steps=steps,
        misconceptions=misconceptions,
        assessment=assessment,
        adaptations=adaptations,
        resources=resources,
        next_lesson=str(payload.get("next_lesson", "")).strip(),
    )


def _read_criteria(raw):
    if not isinstance(raw, list) or not (MIN_CRITERIA <= len(raw) <= MAX_CRITERIA):
        raise LessonError(
            f"A lesson needs between {MIN_CRITERIA} and {MAX_CRITERIA} success "
            f"criteria; this has {len(raw) if isinstance(raw, list) else 'none'}."
        )

    criteria = []
    for item in raw:
        if not isinstance(item, dict):
            raise LessonError("A success criterion is not an object.")
        text = str(item.get("criterion", "")).strip()
        evidence = str(item.get("evidence", "")).strip()
        if not text:
            raise LessonError("A success criterion is blank.")
        if not evidence:
            raise LessonError(
                f"{text!r} names no evidence, so nothing in the lesson shows "
                f"whether a child met it."
            )
        lowered = text.lower()
        if any(phrase in lowered for phrase in _EFFORT_PHRASES):
            raise LessonError(
                f"{text!r} describes effort, not evidence. A child cannot tell "
                f"whether they met it and a teacher cannot mark it."
            )
        criteria.append(Criterion(criterion=text, evidence=evidence))
    return criteria


def _read_vocabulary(raw):
    if not isinstance(raw, dict):
        raise LessonError("The lesson has no vocabulary in three bands.")

    bands = {}
    for band in ("everyone", "expected", "stretch"):
        words = raw.get(band)
        words = [w.strip() for w in words if isinstance(w, str) and w.strip()] if isinstance(words, list) else []
        if not words:
            # One list is precisely what she said does not work for this class.
            raise LessonError(
                f"The {band} vocabulary band is empty. All three bands are "
                f"needed — one list is too easy for some and too hard for others."
            )
        bands[band] = words

    # Which band a word belongs in is a judgement, and it stays hers. A word in
    # two bands is not a judgement -- it cannot be both what every child leaves
    # with and what is expected of some, and it is the tell that the bands were
    # written as three lists rather than as an order.
    seen = {}
    for band, words in bands.items():
        for word in words:
            key = " ".join(word.lower().split())
            if key in seen:
                raise LessonError(
                    f"{word!r} is in both the {seen[key]} and {band} vocabulary "
                    f"bands. The bands are an order of difficulty, so a word "
                    f"belongs in exactly one."
                )
            seen[key] = band

    guidance = str(raw.get("guidance", "")).strip()
    if not guidance:
        raise LessonError(
            "The vocabulary has no guidance on how to use the three bands."
        )
    return Vocabulary(guidance=guidance, **bands)


def _read_steps(raw, lesson_minutes):
    if not isinstance(raw, list) or len(raw) < 2:
        raise LessonError("A lesson needs at least two steps.")

    steps = []
    for position, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            raise LessonError(f"Step {position} is not an object.")

        minutes = item.get("minutes")
        if not isinstance(minutes, int) or minutes <= 0:
            raise LessonError(f"Step {position} has no time on it.")

        fields = {}
        for name in ("on_the_board", "teacher_says", "children_do"):
            value = str(item.get(name, "")).strip()
            if not value:
                raise LessonError(
                    f"Step {position} does not say {name.replace('_', ' ')}. "
                    f"That is the difference between a plan and an outline."
                )
            fields[name] = value

        questions = []
        for question in item.get("questions") or []:
            if not isinstance(question, dict):
                continue
            ask = str(question.get("ask", "")).strip()
            expect = str(question.get("expect", "")).strip()
            if ask and not expect:
                raise LessonError(
                    f"Step {position} asks {ask!r} without saying what answer to "
                    f"expect."
                )
            if ask:
                questions.append(Question(ask=ask, expect=expect))

        watch_for = [
            WatchFor(
                wrong=str(w.get("wrong", "")).strip(),
                respond=str(w.get("respond", "")).strip(),
            )
            for w in item.get("watch_for") or []
            if isinstance(w, dict) and str(w.get("wrong", "")).strip()
        ]

        steps.append(
            LessonStep(
                name=str(item.get("name", f"Step {position}")).strip(),
                minutes=minutes,
                questions=questions,
                watch_for=watch_for,
                adults=str(item.get("adults", "")).strip(),
                builds_on_step=str(item.get("builds_on_step", "")).strip(),
                **fields,
            )
        )

    total = sum(step.minutes for step in steps)
    if total != lesson_minutes:
        # The commonest way a plan turns out to be useless in the room.
        raise LessonError(
            f"The steps add up to {total} minutes but the lesson is "
            f"{lesson_minutes}."
        )

    if not any(step.questions for step in steps):
        raise LessonError(
            "No lesson step asks a question. Without them this is an outline."
        )
    if not any(step.watch_for for step in steps):
        raise LessonError(
            "No lesson step says what to watch for. The common wrong answer is "
            "the part a teacher cannot plan for on the spot."
        )
    if not any(step.adults for step in steps):
        raise LessonError(
            "No lesson step says where the other adult is. She has one in the "
            "room and the plan has to use them."
        )
    return steps


def _read_assessment(raw):
    if not isinstance(raw, dict):
        raise LessonError("The lesson has no assessment.")
    look_for = str(raw.get("look_for", "")).strip()
    not_yet = str(raw.get("not_yet_example", "")).strip()
    if not look_for:
        raise LessonError("The assessment does not say what to look for.")
    if not not_yet:
        # Asked for by name. "Look for children meeting the criterion" tells a
        # teacher nothing she did not already know.
        raise LessonError(
            "The assessment gives no example of work that has not met the "
            "criterion, which is the part that makes it usable."
        )
    return Assessment(look_for=look_for, not_yet_example=not_yet)


def _read_adaptations(raw):
    if not isinstance(raw, dict):
        raise LessonError("The lesson has no adaptations.")
    adaptations = {}
    for name in ("eal", "send", "stretch"):
        value = str(raw.get(name, "")).strip()
        if not value:
            raise LessonError(
                f"The lesson has no {name.upper() if name != 'stretch' else name} "
                f"adaptation. This class needs all three."
            )
        adaptations[name] = value
    return adaptations


def _read_misconceptions(raw):
    if not isinstance(raw, list) or not raw:
        raise LessonError("The lesson names no misconception to expect.")
    misconceptions = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        text = str(item.get("misconception", "")).strip()
        if text:
            misconceptions.append(
                {
                    "misconception": text,
                    "why": str(item.get("why", "")).strip(),
                    "address": str(item.get("address", "")).strip(),
                }
            )
    if not misconceptions:
        raise LessonError("The lesson names no misconception to expect.")
    return misconceptions


def _read_resources(raw):
    if not isinstance(raw, list) or not raw:
        raise LessonError("The lesson lists no resources.")
    resources = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("item", "")).strip()
        quantity = str(item.get("quantity", "")).strip()
        if not name:
            continue
        if not quantity:
            # "Rock samples" sends her to the cupboard twice.
            raise LessonError(f"{name!r} has no quantity against it.")
        resources.append({"item": name, "quantity": quantity})
    if not resources:
        raise LessonError("The lesson lists no resources.")
    return resources


def lowered_objective_flags(adaptations):
    """Adaptations that announce a different goal rather than a different route.

    A flag, never a rejection, and deliberately narrow. *"Children only need to
    say 'lets water through' rather than 'permeable'"* is exactly right — the
    child has met the criterion in easier words — and no word list can tell that
    apart from lowering the bar. What it does catch is an adaptation that says
    out loud it is using a different objective.

    Returns `(where, reason)` pairs.
    """
    flags = []
    for where, text in (adaptations or {}).items():
        lowered = str(text).lower()
        for phrase in _LOWERED_OBJECTIVE_PHRASES:
            if phrase in lowered:
                flags.append((
                    f"{where}: {text}",
                    f"Says {phrase!r}. An adaptation changes how a child reaches "
                    f"the same objective, not which objective they are reaching.",
                ))
                break
    return flags


def generate_lesson(
    spine,
    number,
    subject,
    year_group,
    lesson_minutes=60,
    coverage=(),
    build_on="",
    outcome="",
):
    """Write one lesson of the approved sequence, and check it before returning.

    Raises:
        LessonError: the sequence has no such lesson, or what came back is not
            usable — including an objective that drifted from the approved one.
        TruncatedResponseError, json.JSONDecodeError: from the model call.
    """
    this = _lesson_in(spine, number)

    payload = generate_structured_content(
        build_lesson_prompt(
            spine=spine,
            number=number,
            subject=subject,
            year_group=year_group,
            lesson_minutes=lesson_minutes,
            coverage=coverage,
            build_on=build_on,
            outcome=outcome,
        ),
        LESSON_SYSTEM_PROMPT,
        max_tokens=LESSON_MAX_TOKENS,
        timeout=LESSON_TIMEOUT,
        stream=True,
    )
    lesson = validate_lesson(
        payload,
        expected_objective=this.objective,
        lesson_minutes=lesson_minutes,
    )
    return Lesson(
        objective=lesson.objective,
        success_criteria=lesson.success_criteria,
        vocabulary=lesson.vocabulary,
        steps=lesson.steps,
        misconceptions=lesson.misconceptions,
        assessment=lesson.assessment,
        adaptations=lesson.adaptations,
        resources=lesson.resources,
        number=number,
        builds_on=this.builds_on,
        builds_on_reason=this.builds_on_reason,
        next_lesson=lesson.next_lesson,
    )
