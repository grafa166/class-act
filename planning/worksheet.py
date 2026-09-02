"""The worksheet built from a lesson, and made to evidence it.

This is the last handover in the chain. The spine's objective is checked
verbatim into the lesson, the lesson's into the worksheet — so the plan, the
sheet and the child's book carry the same sentence, and nothing on screen would
show it if one of them quietly drifted.

Two things are load-bearing, and only the second is new.

**Nothing is re-derived.** The objective and the success criteria come from the
lesson word for word: not re-worded, not improved, not a second model's
paraphrase. A reworded criterion is rejected, so is a dropped one, and so is an
invented extra. They are then printed back in the order she approved, whatever
order they came home in.

**A criterion is only met if the sheet produces its evidence.** Every criterion
must name the part of the sheet that evidences it, say what the child records
there, and — the part with teeth — **quote the instruction**, which is checked
against the worksheet itself.

That last check exists because the claim on its own is worthless, and this
project has already been bitten by exactly that shape: on the unit spine, a
scheme line was attached to a lesson that never taught it while the coverage map
vouched for it. A claim cannot be verified; a quote can. And the quote is
searched for in the sheet *with the claims removed* — searching the whole reply
would let every quote match itself, which is a check that asserts nothing.

What is not checked, and deliberately: whether the task is any good, whether it
is pitched right, whether the evidence would actually convince a moderator.
That is the teacher's, which is why the whole thing is shown to her and labelled
"AI-drafted — check before teaching".
"""

import re
from dataclasses import dataclass

from llm.client import generate_structured_content
from llm.prompts import get_prompt
from llm.validation import validate_worksheet_content

# The sheet now carries an evidence block as well as its tasks, and the biggest
# worksheet types were already asking for 6,144. A truncated reply is refused
# rather than rendered short, so too small a budget shows up as a failure rather
# than as a quietly thin worksheet -- but a failure still costs a whole run.
WORKSHEET_MAX_TOKENS = 8192

# Streamed, not requested whole. Anthropic's guidance is to stream anything with
# a long output or a high token budget; the lesson path learned the same thing
# live on 2026-09-02, when a long non-streaming request had its connection
# closed by the server and a longer timeout only moved the failure. The timeout
# stays as a bound on a request that stalls completely.
WORKSHEET_TIMEOUT = 180.0

# A quote shorter than this cannot be an instruction, and a two-word quote would
# match somewhere in almost any sheet -- which would turn the check that carries
# this whole module into a formality.
MIN_QUOTE_CHARS = 20

# Below this a unit is too short for sameness to mean anything: two sheets of
# one kind is a coincidence, and she may well have chosen both.
MIN_SHEETS_BEFORE_SAMENESS_MATTERS = 3


class WorksheetCouplingError(ValueError):
    """The worksheet does not belong to the lesson it claims to."""


@dataclass(frozen=True)
class EvidenceClaim:
    """One criterion, and the part of the sheet that produces its evidence."""

    criterion: str
    where: str
    quote: str
    pupil_writes: str


@dataclass(frozen=True)
class CoupledWorksheet:
    objective: str
    success_criteria: list
    evidence: list
    content: dict
    worksheet_type: str
    lesson_number: int | None = None
    source: str = "AI-drafted — check before teaching."


WORKSHEET_SYSTEM_PROMPT = (
    "You are an experienced UK primary teacher making the worksheet for a "
    "lesson you have already planned. The objective and the success criteria "
    "are fixed and are not yours to change — your job is to build tasks that "
    "produce the evidence each criterion names. If a criterion cannot be "
    "evidenced by the sheet, you change the sheet, never the criterion. You "
    "reply with JSON only, and no commentary."
)


def build_worksheet_prompt(
    lesson,
    worksheet_type,
    subject,
    year_group,
    topic="",
    age_range="7-8",
    theme_name="Space Explorer",
    theme_icon="\U0001F680",
    level="expected",
    earlier_objectives=(),
):
    """The existing worksheet prompt, with the lesson bolted on to it.

    The base prompt is the one the worksheet flow already uses, so the ten
    generators keep working exactly as they do — this only adds what makes the
    sheet belong to a lesson rather than to a topic.
    """
    base = get_prompt(
        worksheet_type=worksheet_type,
        year_group=year_group,
        topic=(topic or lesson.objective).strip(),
        objective=lesson.objective,
        age_range=age_range,
        theme_name=theme_name,
        theme_icon=theme_icon,
        level=level,
        subject=subject,
    )

    parts = [
        base,
        "",
        "\u2500" * 60,
        "",
        "THIS WORKSHEET BELONGS TO A LESSON. The rules below override anything "
        "above them, including anything above about writing your own success "
        "criteria.",
        "",
        "1. THE SHEET MUST PRODUCE THE EVIDENCE EACH CRITERION NAMES. The "
        "teacher has already approved the objective and the criteria; your job "
        "is to build tasks that produce what each one names. A child who "
        "completes this worksheet should leave behind, in their book, the "
        "thing each criterion says to look for. Reading something is not "
        "evidence \u2014 the child has to record something.",
        "",
        "   These are the criteria, and the evidence each one names:",
    ]
    parts += [
        f"     {c.criterion}\n       evidence: {c.evidence}"
        for c in lesson.success_criteria
    ]

    parts += [
        "",
        '2. SAY WHAT EVIDENCES WHAT. Add an "evidence" array with one entry '
        "per criterion:",
        "",
        '   "evidence": [',
        "     {",
        '       "criterion": "the criterion, word for word",',
        '       "where": "which part of the sheet",',
        '       "quote": "one instruction, question or sentence from the sheet, '
        'copied exactly as you wrote it above",',
        '       "pupil_writes": "what the child records there"',
        "     }",
        "   ]",
        "",
        "   The quote must be text that is really on this worksheet \u2014 it is "
        "checked against it, character by character. Copy it from what you "
        "wrote; do not describe it from memory and do not tidy it up.",
        "",
        "   Quote ONE sentence, question or instruction, from one part of the "
        "sheet. Do not join text from two different parts together, do not "
        "read past a heading, and do not summarise several parts into one "
        "sentence \u2014 a summary is not a quote and is rejected even when every "
        "word of it is true.",
        "",
        "   If you cannot quote a single task that produces the evidence, the "
        "sheet does not produce it: change the sheet, never the criterion.",
    ]
    earlier = [str(o).strip() for o in earlier_objectives if str(o).strip()]
    if earlier:
        parts += [
            "",
            "Already taught in this unit, so the sheet may assume it — and "
            "must not re-teach or re-explain it:",
        ]
        parts += [f"  - {objective}" for objective in earlier]
    else:
        parts += [
            "",
            "This is the first lesson of the unit, so assume nothing beyond "
            "the lesson itself.",
        ]

    parts += [
        "",
        "3. THESE TWO FIELDS ARE THE TEACHER'S. Copy them into your JSON "
        "exactly as they appear here, without changing a character. Do not "
        "reword them, shorten them or improve them; do not write your own; do "
        "not add one more because the list looks thin.",
        "",
        f'  "objective": "{lesson.objective}",',
        '  "success_criteria": [',
    ]
    parts += [
        f'    "{c.criterion}"' + ("," if n < len(lesson.success_criteria) else "")
        for n, c in enumerate(lesson.success_criteria, 1)
    ]
    parts += [
        "  ],",
        "",
        "Before you finish, check your JSON has all of these:",
        "  - every field the worksheet schema above asks for",
        f'  - "objective", copied exactly',
        f'  - "success_criteria", all {len(lesson.success_criteria)} of them, '
        "copied exactly, in that order",
        '  - "evidence", one entry per criterion, each quoting the sheet',
    ]

    return "\n".join(parts)


def validate_coupled_worksheet(payload, lesson, worksheet_type):
    """Check the worksheet belongs to the lesson before it is shown as one.

    Everything here is structural. Nothing reads a task and decides whether it
    is a good task.

    Raises:
        WorksheetCouplingError: the objective or criteria drifted, or a
            criterion has no evidence on the sheet.
        WorksheetContentError: the sheet is missing something its generator
            needs, so it could not be rendered.
    """
    if not isinstance(payload, dict):
        raise WorksheetCouplingError("The worksheet is not an object.")

    _check_the_objective(payload, lesson)
    criteria = _check_the_criteria(payload, lesson)

    # Her order, not whatever order it came back in -- and her exact words,
    # which by this point are the only ones that can be here.
    content = dict(payload)
    content["objective"] = lesson.objective
    content["success_criteria"] = [c.criterion for c in criteria]

    # Still has to be a worksheet the generator can build.
    validate_worksheet_content(worksheet_type, content)

    evidence = _check_the_evidence(payload, criteria)

    return CoupledWorksheet(
        objective=lesson.objective,
        success_criteria=criteria,
        evidence=evidence,
        content=content,
        worksheet_type=worksheet_type,
        lesson_number=lesson.number,
    )


def _check_the_objective(payload, lesson):
    expected = (lesson.objective or "").strip()
    if not expected:
        raise WorksheetCouplingError(
            "The lesson has no objective, so there is nothing to build a "
            "worksheet from."
        )

    objective = str(payload.get("objective", "")).strip()
    if objective != expected:
        raise WorksheetCouplingError(
            "The worksheet came back with a different objective from the "
            f"lesson's.\n  The lesson says: {expected}\n  The sheet says:  "
            f"{objective or '(nothing)'}"
        )


def _check_the_criteria(payload, lesson):
    """Hers, all of them, and nothing else."""
    hers = list(lesson.success_criteria)
    if not hers:
        raise WorksheetCouplingError(
            "The lesson has no success criteria, so nothing on a worksheet "
            "could evidence it."
        )

    raw = payload.get("success_criteria")
    if not isinstance(raw, list) or not raw:
        # Not an error. The criteria printed on the child's sheet are hers,
        # filled in below from the lesson, so an echo that never came back
        # costs the sheet nothing. Three times live a word-bank sheet came back
        # without one, and refusing an otherwise correct worksheet over a field
        # the teacher never sees is the guard blocking correct work.
        #
        # What the sheet was actually built to is checked by the evidence
        # instead: every criterion of hers must be claimed there, word for
        # word, and quoted from the sheet. That came back every time.
        return hers

    came_back = [str(item).strip() for item in raw if str(item).strip()]
    expected = [c.criterion for c in hers]

    missing = [text for text in expected if text not in came_back]
    if missing:
        # Either dropped or quietly reworded; both are the same failure to her.
        raise WorksheetCouplingError(
            "The worksheet's success criteria are not the lesson's. Missing "
            "or reworded:\n  "
            + "\n  ".join(missing)
        )

    invented = [text for text in came_back if text not in expected]
    if invented:
        raise WorksheetCouplingError(
            "The worksheet added success criteria the lesson does not have:\n"
            "  " + "\n  ".join(invented)
        )

    return hers


def _check_the_evidence(payload, criteria):
    """Every criterion evidenced, and every claim checked against the sheet."""
    raw = payload.get("evidence")
    if not isinstance(raw, list) or not raw:
        raise WorksheetCouplingError(
            "The worksheet does not say which part of it evidences each "
            "success criterion, so there is no way to tell whether it does."
        )

    known = {c.criterion for c in criteria}
    sheet = _sheet_pieces(payload)

    claims = []
    for item in raw:
        if not isinstance(item, dict):
            raise WorksheetCouplingError("An evidence entry is not an object.")

        criterion = str(item.get("criterion", "")).strip()
        if criterion not in known:
            raise WorksheetCouplingError(
                f"The worksheet claims to evidence {criterion!r}, which is not "
                f"one of the lesson's success criteria."
            )

        pupil_writes = str(item.get("pupil_writes", "")).strip()
        if not pupil_writes:
            # A child who reads a box has not evidenced anything.
            raise WorksheetCouplingError(
                f"{criterion!r} is said to be evidenced by a part of the sheet "
                f"where the child records nothing. Reading is not evidence."
            )

        quote = str(item.get("quote", "")).strip()
        # Measured on the words, not the gaps. A gap matches anything, so a
        # quote made mostly of gaps would make this check assert nothing.
        if len("".join(_segments_of(quote))) < MIN_QUOTE_CHARS:
            raise WorksheetCouplingError(
                f"The instruction quoted for {criterion!r} is too short to be "
                f"a task: {quote!r}."
            )

        if not any(_says_the_same(quote, piece) for piece in sheet):
            # The check the whole module rests on. The sheet searched here has
            # the claims stripped out, so a quote cannot match itself.
            raise WorksheetCouplingError(
                f"{criterion!r} is said to be evidenced by:\n  {quote}\n"
                f"...which does not appear anywhere on the worksheet. Nothing "
                f"on the sheet produces that evidence."
            )

        claims.append(
            EvidenceClaim(
                criterion=criterion,
                where=str(item.get("where", "")).strip(),
                quote=quote,
                pupil_writes=pupil_writes,
            )
        )

    unevidenced = known - {claim.criterion for claim in claims}
    if unevidenced:
        raise WorksheetCouplingError(
            "Nothing on the sheet produces the evidence for:\n  "
            + "\n  ".join(sorted(unevidenced))
        )

    return claims


def _normalise(text):
    """Compared the way a reader would, not byte for byte.

    Runs of underscores collapse to one, so how wide a gap happens to be drawn
    is not a difference — the model writes a blank as anything from `___` to a
    full ruled line, and none of that changes what the sentence says.
    """
    collapsed = re.sub(r"_{2,}", "_", str(text))
    return " ".join(collapsed.split()).lower()


def _segments_of(quote):
    """The quote's own words, split where the sheet has a gap.

    A gap reaches the reply drawn several different ways -- a run of
    underscores, or the choices a child picks between in brackets -- and none
    of that is what the sentence says. What is left is what the quote claims.
    """
    without_gaps = re.sub(r"\[[^\]]*\]|_+", " ", _normalise(quote))
    return [part.strip() for part in without_gaps.split(" " * 2) if part.strip()]


def _says_the_same(quote, piece):
    """Is this quote the text of that part of the sheet?

    With no gaps in it, an exact match -- the strongest form, and the usual
    one. With gaps, every stretch of words between them has to appear in that
    one piece, in that order, because how wide a gap is drawn is not what the
    sentence says.

    Still one piece, and still whole stretches rather than loose words: text
    gathered from two unrelated tasks is a fabrication, which is the whole
    reason this check exists.
    """
    normalised = _normalise(quote)
    if normalised in piece:
        return True

    at = 0
    for segment in _segments_of(quote):
        found = piece.find(segment, at)
        if found == -1:
            return False
        at = found + len(segment)
    return True


def _sheet_pieces(payload):
    """Every piece of text on the worksheet, with the claims left out.

    Kept as separate pieces rather than joined into one blob, so a quote has to
    be found inside a single instruction rather than manufactured across the
    join between two unrelated ones.
    """
    without_claims = {k: v for k, v in payload.items() if k != "evidence"}
    return [_normalise(piece) for piece in _strings_in(without_claims)]


def _is_pieces(value):
    """A run of sentence fragments with the gaps between them.

    Recognised by shape rather than by the key holding it: a word-bank sentence
    keeps them under `pieces` and a cloze passage keeps them under `paragraphs`
    as a bare list of lists. Both were refused live on 2026-09-02 for quoting
    text that was genuinely on the sheet.
    """
    return (
        isinstance(value, (list, tuple))
        and value
        and all(
            isinstance(item, dict) and item.get("type") in ("text", "blank")
            for item in value
        )
    )


def _strings_in(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings_in(item)
    elif isinstance(value, (list, tuple)):
        if _is_pieces(value):
            # No single fragment holds the sentence the child actually reads.
            yield from _assembled(value)
        for item in value:
            yield from _strings_in(item)
        # A list of plain strings is printed one under the other, so a child
        # meets several of them together. Found live on 2026-09-02, when an
        # investigation sheet was refused for quoting two of its conclusion
        # prompts as they appear. Only runs that are actually adjacent on the
        # page are joined -- welding the end of one task to the start of an
        # unrelated one is still a fabrication.
        lines = [item for item in value if isinstance(item, str)]
        if len(lines) == len(value) > 1:
            for start in range(len(lines)):
                for end in range(start + 2, len(lines) + 1):
                    yield " ".join(lines[start:end])


def _assembled(pieces):
    """The sentence as the child reads it — both filled in and left blank.

    Both, because the model quotes it either way: with the answers in place, or
    with the gaps still showing.
    """
    filled, blanked = [], []
    for piece in pieces:
        if not isinstance(piece, dict):
            continue
        text = str(piece.get("text", ""))
        answer = str(piece.get("answer", ""))
        if piece.get("type") == "blank":
            filled.append(answer)
            blanked.append("___")
        else:
            filled.append(text)
            blanked.append(text)
    yield "".join(filled)
    yield "".join(blanked)


def generate_worksheet_for_lesson(
    lesson,
    worksheet_type,
    subject,
    year_group,
    topic="",
    age_range="7-8",
    theme_name="Space Explorer",
    theme_icon="\U0001F680",
    level="expected",
    earlier_objectives=(),
):
    """Make the worksheet for one lesson, and check it belongs to it.

    Raises:
        WorksheetCouplingError: the objective or criteria drifted, or a
            criterion has no evidence on the sheet.
        WorksheetContentError: the sheet could not be rendered.
        TruncatedResponseError, json.JSONDecodeError: from the model call.
    """
    payload = generate_structured_content(
        build_worksheet_prompt(
            lesson=lesson,
            worksheet_type=worksheet_type,
            subject=subject,
            year_group=year_group,
            topic=topic,
            age_range=age_range,
            theme_name=theme_name,
            theme_icon=theme_icon,
            level=level,
            earlier_objectives=earlier_objectives,
        ),
        WORKSHEET_SYSTEM_PROMPT,
        max_tokens=WORKSHEET_MAX_TOKENS,
        timeout=WORKSHEET_TIMEOUT,
        stream=True,
    )
    return validate_coupled_worksheet(
        payload, lesson=lesson, worksheet_type=worksheet_type
    )


def repeated_task_shapes(worksheets):
    """A unit that is the same task six times over.

    A flag, never a rejection — she may have a reason, and the sequence is not
    changed for her. Returns a list of reasons, empty when there is nothing to
    say.
    """
    kinds = [sheet.worksheet_type for sheet in worksheets or []]
    if len(kinds) < MIN_SHEETS_BEFORE_SAMENESS_MATTERS or len(set(kinds)) > 1:
        return []
    return [
        f"All {len(kinds)} worksheets in this unit are the same kind of task "
        f"({kinds[0]}). Children stop reading an instruction they have already "
        f"met five times, and the sheet stops showing you anything new."
    ]
