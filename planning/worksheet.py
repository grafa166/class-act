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
against the worksheet itself, and against the part of it that reaches the page.

That last clause was earned on 2026-09-03, reading every worksheet reply ever
saved: of 87 evidence claims, six quoted text no generator prints. Both
investigation sheets on the 11:51 run evidenced all three of their criteria out
of `sorting_section`, `job_section` and `explanation_section` — keys the prompt
never asks for and the generator has never heard of. This check passed them and
the run recorded the worksheets as made. Told to change the sheet rather than
the criterion, the model had added tasks, correctly, and put them where nothing
would print them. Two things close it: the reply is now constrained to the
shape of its own kind of sheet (`planning/worksheet_schema.py`), and the search
below looks only at the keys that kind of generator renders.

That last check exists because the claim on its own is worthless, and this
project has already been bitten by exactly that shape: on the unit spine, a
scheme line was attached to a lesson that never taught it while the coverage map
vouched for it. A claim cannot be verified; a quote can. And the quote is
searched for in the sheet *with the claims and the header removed* — searching
the whole reply would let every quote match itself, and searching the printed
objective and criteria would let it match the very thing it is supposed to be
evidence for. Neither asserts anything. What is left is the tasks.

**A sheet refused by that check is asked for once more, never softened.** Four
times now the check has refused correct work, and each time the temptation was
to widen the search. Three of the four were genuinely the search being blind to
a shape a sheet legitimately comes back in, and were fixed by teaching it that
shape. The fourth, on 2026-09-03, was not: the sheet was right, the quote was a
sentence *about* a results-table column rather than the column's own words, and
the guard was right to refuse it. A search loose enough to accept a paraphrase
also accepts the fabrication this check was built to catch, so the search does
not move — the sheet is told what is wrong, in terms it can act on, and gets one
more attempt through exactly the same checks.

**And "in terms it can act on" means handing back the sheet's own words.** Two
more sheets were lost on the evening of 2026-09-03 with the search behaving
correctly both times: one quoted a twelve-character label while a conforming
instruction sat on the same activity, and one quoted a passage the sheet prints
as four separate paragraphs. Both refusals named the right move and left the
model to find it, and neither was found. A refusal now carries the lines the
sheet really prints where that quote appears — see `_lines_to_copy`, which
offers nothing at all when the quote appears nowhere, because a fabrication
must not be handed a list of lines that would pass.

What is not checked, and deliberately: whether the task is any good, whether it
is pitched right, whether the evidence would actually convince a moderator.
That is the teacher's, which is why the whole thing is shown to her and labelled
"AI-drafted — check before teaching".
"""

import json
import logging
import re
from dataclasses import dataclass

from llm.client import generate_structured_content
from llm.prompts import get_prompt
from llm.validation import validate_worksheet_content
from planning.worksheet_schema import RENDERED_KEYS, get_worksheet_schema

logger = logging.getLogger(__name__)

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

# How many of the sheet's own lines a refusal hands back. Measured across every
# worksheet reply ever saved: of the fourteen claims that would be refused,
# seven have a line the sheet really prints, and the most any of them has is
# three. The cap is a bound on a sheet nobody has seen yet rather than on
# anything in the corpus -- and when it bites it says so, because a list that
# quietly stops short reads as "these are all of them".
MOST_LINES_TO_OFFER = 4

# Below this a unit is too short for sameness to mean anything: two sheets of
# one kind is a coincidence, and she may well have chosen both.
MIN_SHEETS_BEFORE_SAMENESS_MATTERS = 3

# The sheet's header, and not part of the sheet a quote may be found in.
#
# `evidence` is out for the original reason: searching the claims would let
# every quote match itself, and a check that matches itself asserts nothing.
# The other three are the same hole one step further out. The objective and the
# criteria are the teacher's own words printed at the top, and the title names
# the sheet -- none of them is a task a child does, so a quote matching nothing
# but one of them proves nothing about whether the sheet produces any evidence.
#
# Left out by key, never by text: a sheet whose closing section asks the child
# to tick a criterion off has really printed that instruction, and quoting it
# is quoting the sheet.
NOT_A_TASK = ("evidence", "objective", "success_criteria", "title")


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
        '       "quote": "one instruction, question, prompt, heading or '
        'sentence from the sheet, copied exactly as you wrote it above",',
        '       "pupil_writes": "what the child records there"',
        "     }",
        "   ]",
        "",
        "   The quote must be text that is really on this worksheet \u2014 it is "
        "checked against it, character by character. Copy it from what you "
        "wrote; do not describe it from memory and do not tidy it up.",
        "",
        "   Quote ONE sentence, question, instruction, prompt or heading, "
        "from one part of the sheet. Do not join text from two different "
        "parts together, do not read past a heading, and do not summarise "
        "several parts into one sentence \u2014 a summary is not a quote and is "
        "rejected even when every word of it is true.",
        "",
        "   Where the child writes in a table, the words on the sheet are the "
        "COLUMN HEADING \u2014 quote the heading exactly as you wrote it, brackets "
        "and all. Where the child writes under a question or a prompt, quote "
        "that question or prompt. A sentence saying where the child writes is "
        "a description, not a quote, and is rejected:",
        "",
        '     "In the \'What we found\' column, record what it looks like."',
        "       \u2014 this is a description, and it is refused.",
        '     "What we found (describe what it looks like)"',
        "       \u2014 this is the quote, because it is what is printed there.",
        "",
        "   If you cannot quote a single task that produces the evidence, the "
        "sheet does not produce it: change the sheet, never the criterion.",
        "",
        "   AN ADDED TASK GOES IN A FIELD THIS WORKSHEET ALREADY HAS. Put it "
        "in one of the fields the schema above lists — another step, another "
        "prompt, another question, another section of the kind it already "
        "uses. Do not invent a field of your own for it: an invented field is "
        "not printed on the sheet the child is handed, so a criterion "
        "evidenced there is evidenced by nothing at all.",
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

    evidence = _check_the_evidence(payload, criteria, worksheet_type)

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


# What to do about a quote that is not on the sheet.
#
# Both branches, because from here the two are indistinguishable, and a refusal
# naming only one fits half the cases and contradicts the other half.
#
# It goes after the fault, never before it, and behind "To fix it". These
# refusals have two readers: the model, in the repair, which needs to be told
# what to do — and the teacher, who sees the same string on screen if the
# second attempt fails too. She needs to know what was refused and why; the
# instruction is not addressed to her and she can stop reading at the blank
# line.
_HOW_TO_QUOTE = (
    "To fix it: if the sheet does have a part that produces this evidence, "
    "then the quote is wrong rather than the sheet — copy that part's own "
    "words, character for character, and quote nothing else. Where the child "
    "writes in a table, its words are the column heading: copy the heading, "
    "including anything in brackets. Where the child writes under a question "
    "or a prompt, copy that question or prompt. A sentence describing where "
    "the child writes is not a quote. If no part of the sheet produces this "
    "evidence, add a task that does and quote that instead."
)


def _long_enough(text):
    """Measured on its own words, never on its gaps.

    One definition, used both to refuse a quote and to decide whether a line is
    worth handing back — offering a line that would then be refused for length
    reproduces the very fault being reported.
    """
    return len("".join(_segments_of(text))) >= MIN_QUOTE_CHARS


def _sentences_of(text):
    """The quote broken where a reader would stop.

    Only ever used to work out *where a welded quote came from*, so that the
    refusal can hand those parts back. It is never used to accept one: a quote
    running across two parts of the sheet is refused exactly as it was before.
    """
    return [
        part.strip() for part in re.split(r"(?<=[.?!:])\s+", str(text)) if part.strip()
    ]


def _read_lines(value):
    """Each line of the sheet, and the ways it can legitimately be quoted.

    Yields `(what is printed, every form it may be quoted in)`. A sentence
    stored as fragments is printed with its gaps showing and may be quoted
    either with them or with the answers in place, so both forms search and the
    blanked one is what gets handed back.

    Deliberately a second, narrower walk than `_strings_in`. That one yields
    everything a quote may legitimately be *found* in — the fragments a
    sentence is stored in, the hints beside its gaps, two adjacent prompts run
    together. None of those is something to hand back and say "copy this": a
    fragment ends mid-sentence, a hint is not a task, and offering a run of two
    prompts teaches the welding that lost a sheet in the first place.

    The two walks cannot quietly drift apart, because every line this offers is
    quoted back through the real check in the tests. One that the check would
    refuse fails the suite rather than a teacher.
    """
    if isinstance(value, str):
        yield value, (value,)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _read_lines(item)
    elif isinstance(value, (list, tuple)):
        if _is_pieces(value):
            filled, blanked = tuple(_assembled(value))
            yield blanked, (filled, blanked)
            return
        for item in value:
            yield from _read_lines(item)


def _lines_to_copy(quote, payload, worksheet_type):
    """The sheet's own lines where this quote appears, as they are printed.

    This is the conforming move, made findable rather than described. It came
    from two sheets lost on the evening of 2026-09-03, both read off the
    artefacts: a word-bank sheet told to quote *"the instruction or question
    the child reads before writing"* quoted a twelve-character label twice,
    with a conforming instruction sitting on the same activity; and a cloze
    sheet told to copy *"that part's own words"* was never told which parts
    there were, and welded four paragraphs into one quote.

    ⚠️ **A quote that appears nowhere gets nothing back**, and that is the
    point. Handing a fabricated claim a list of lines it could quote instead
    would let it pick any line that passes and evidence a criterion with a task
    that does not produce it. That is a false pass, and a false pass is worse
    than the refusal it replaces: a refusal is visible and gets a second
    attempt, while a sheet that passes is handed to a child.

    Nothing here accepts anything. The search is untouched; this only reports.
    """
    lines = _lines_a_child_reads(payload, worksheet_type)
    found = [
        printed
        for printed, forms in lines
        if any(_says_the_same(quote, form) for form in forms)
    ]
    if not found:
        # Nothing prints it whole. If its sentences are printed separately then
        # the quote was welded across them, and the parts are the legal move.
        sentences = _sentences_of(quote)
        if len(sentences) > 1:
            found = [
                printed
                for printed, forms in lines
                if any(
                    _says_the_same(sentence, form)
                    for sentence in sentences
                    for form in forms
                )
            ]
    return [line for line in found if _long_enough(line)]


def _lines_a_child_reads(payload, worksheet_type):
    """`_read_lines` over the same part of the sheet the check searches."""
    lines, seen = [], set()
    for text, forms in _read_lines(_what_reaches_the_page(payload, worksheet_type)):
        line = " ".join(str(text).split())
        if not line or line in seen:
            continue
        seen.add(line)
        lines.append((line, tuple(_normalise(form) for form in forms)))
    return lines


def _copy_one_of_these(lines):
    """The lines, under an instruction that says to take exactly one.

    A bare list is an invitation to join them, which is the fault it is
    answering. Empty when there is nothing conforming to offer, so the refusal
    reads exactly as it did before.
    """
    if not lines:
        return ""
    shown = lines[:MOST_LINES_TO_OFFER]
    left = len(lines) - len(shown)
    return (
        "\nThese are the sheet's own words where that quote appears, each "
        "printed on its own. Copy ONE of them exactly, and nothing else:\n"
        + "\n".join(f"  {line}" for line in shown)
        + (f"\n  ...and {left} more of the sheet's lines like these." if left else "")
    )


def _check_the_evidence(payload, criteria, worksheet_type):
    """Every criterion evidenced, and every claim checked against the sheet.

    Faults are collected and raised together, never one at a time. There is
    exactly one repair, so a refusal naming the first fault it meets gets that
    one fixed and loses the sheet to the second — a law the lesson lane earned
    live on 2026-09-03, and one this lane inherited the moment a refused
    worksheet started being asked for again.

    The refusals are written to be read by the model as well as by her, so each
    says what would fix it rather than describing what went wrong. *"The quote
    does not appear on the sheet"* is true and useless: it describes exactly
    what the model chose to do, and gets the same reply back.
    """
    raw = payload.get("evidence")
    if not isinstance(raw, list) or not raw:
        raise WorksheetCouplingError(
            "The worksheet does not say which part of it evidences each "
            "success criterion, so there is no way to tell whether it does. "
            'Add an "evidence" array with one entry per criterion, each '
            "quoting the part of the sheet that produces it."
        )

    known = {c.criterion for c in criteria}
    sheet = _sheet_pieces(payload, worksheet_type)

    if not sheet:
        # Nothing on this sheet reaches the page, so every quote below would be
        # refused with "it does not appear on the worksheet" — true, and the
        # most useless refusal there is, because every quote really is in what
        # was returned. The fault is one step up: this is not a sheet of the
        # kind that was asked for. Reachable because investigation, times
        # tables and fractions practice need nothing but a title to get here.
        raise WorksheetCouplingError(
            f"Nothing on this worksheet is a {worksheet_type} task, so there is "
            f"nothing on the page for a criterion to be evidenced by.\n"
            f"To fix it: build the sheet in the shape a {worksheet_type} "
            f"worksheet takes, using the fields the instructions above ask for, "
            f"and quote the tasks from that."
        )

    problems, claims, mentioned = [], [], set()
    for item in raw:
        if not isinstance(item, dict):
            problems.append(
                "An evidence entry is not an object. Each one needs a "
                '"criterion", a "where", a "quote" and a "pupil_writes".'
            )
            continue

        criterion = str(item.get("criterion", "")).strip()
        mentioned.add(criterion)
        if criterion not in known:
            problems.append(
                f"The worksheet claims to evidence {criterion!r}, which is not "
                f"one of the lesson's success criteria.\n"
                f"To fix it: use the criteria you were given, word for word, "
                f"and evidence each of them."
            )
            continue

        quote = str(item.get("quote", "")).strip()
        pupil_writes = str(item.get("pupil_writes", "")).strip()
        faults = []

        if not pupil_writes:
            # A child who reads a box has not evidenced anything.
            faults.append(
                f"{criterion!r} is said to be evidenced by a part of the sheet "
                f"where the child records nothing. Reading is not evidence.\n"
                f'To fix it: say in "pupil_writes" what the child leaves '
                f"behind there, or point at a part of the sheet where they "
                f"write something."
            )

        # Measured on the words, not the gaps. A gap matches anything, so a
        # quote made mostly of gaps would make this check assert nothing.
        if not _long_enough(quote):
            # Fired live on 2026-09-03 on "This ___ is ___ because ___." — a
            # sentence frame that really is on the sheet and that the child
            # really writes in. Quoting it whole is not the fix and telling it
            # to do that would be a refusal it cannot act on: the frame has
            # too few of its own words to say which part of the sheet is meant.
            #
            # The line the frame sits in usually does have enough of its own
            # words, and `_lines_to_copy` is what hands it back. Twice on the
            # evening of 2026-09-03 this refusal named the right move — quote
            # the instruction the child reads — and left the model to find it,
            # and both times it quoted the label again.
            faults.append(
                f"The instruction quoted for {criterion!r} is too short to be "
                f"a task: {quote!r}.\n"
                f"To fix it: quote a part of the sheet with more of its own "
                f"words in it — the instruction or question the child reads "
                f"before writing, or the heading the answer sits under. A "
                f"line that is mostly blanks could be almost any line, so it "
                f"does not say which part of the sheet you mean."
                + _copy_one_of_these(_lines_to_copy(quote, payload, worksheet_type))
            )
        elif not any(_says_the_same(quote, piece) for piece in sheet):
            # The check the whole module rests on. The sheet searched here has
            # the claims and the header stripped out, so a quote can match
            # neither itself nor the criteria printed above the tasks.
            #
            # Where the quote was welded across parts of the sheet that really
            # are contiguous on the page, the parts come back with it — the
            # refusal is otherwise a true sentence with no move in it. Where
            # the quote was invented, nothing comes back, which is the point.
            faults.append(
                f"{criterion!r} is said to be evidenced by:\n  {quote}\n"
                f"...which does not appear anywhere on the worksheet.\n"
                f"{_HOW_TO_QUOTE}"
                + _copy_one_of_these(_lines_to_copy(quote, payload, worksheet_type))
            )

        if faults:
            problems.extend(faults)
        else:
            claims.append(
                EvidenceClaim(
                    criterion=criterion,
                    where=str(item.get("where", "")).strip(),
                    quote=quote,
                    pupil_writes=pupil_writes,
                )
            )

    # Never mentioned at all, so it is the sheet that is short of a task rather
    # than a claim that is wrong. A criterion whose claim failed above is
    # already named there, and naming it twice makes one fault read as two.
    unevidenced = sorted(known - mentioned)
    if unevidenced:
        problems.append(
            "Nothing on the sheet is said to produce the evidence for:\n  "
            + "\n  ".join(unevidenced)
            + "\nTo fix it: add a task to the sheet that produces it, and an "
            "evidence entry quoting that task."
        )

    if problems:
        raise WorksheetCouplingError("\n\n".join(problems))

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


def _what_reaches_the_page(payload, worksheet_type):
    """The part of the reply the child is actually handed.

    **One definition, deliberately, and it is load-bearing.** Both the search
    and the lines a refusal hands back have to mean the same thing by "on the
    sheet" — a refusal that offered a line out of a key no generator prints
    would be telling a model to evidence a criterion with something nobody
    sees, which is the exact defect this filter was written to close.

    It was two definitions for about an hour on 2026-09-03, and the positive
    control caught it rather than a test: with the same lines written out
    twice, the mutation that opens this filter landed on the copy and
    `NOTHING FAILED`. A guard whose mutation goes quiet is a guard nobody is
    checking any more.
    """
    printed = RENDERED_KEYS.get(worksheet_type)
    return {
        k: v
        for k, v in payload.items()
        if k not in NOT_A_TASK and (printed is None or k in printed)
    }


def _sheet_pieces(payload, worksheet_type):
    """Every task on the worksheet, with the header and the claims left out.

    Kept as separate pieces rather than joined into one blob, so a quote has to
    be found inside a single instruction rather than manufactured across the
    join between two unrelated ones. What is left out, and why, is `NOT_A_TASK`.

    **And only what reaches the document.** Found on 2026-09-03, reading every
    worksheet reply ever saved: of 87 evidence claims, six quoted text that no
    generator prints. Both investigation sheets on the 11:51 run answered all
    three of their criteria out of `sorting_section`, `job_section` and
    `explanation_section` — keys the prompt never asks for and the generator has
    never heard of. This check said the sheet evidenced her criteria. The sheet
    the child would have been handed contained none of it.

    That is the same hole as the header fields in `NOT_A_TASK`, one step
    further out, and it closes the same way: what is searched is what is
    printed. `RENDERED_KEYS` comes from the generators and is re-derived from
    their source in the tests, so it cannot quietly fall behind them.

    A type the map has never heard of searches everything, exactly as before.
    Searching nothing would refuse every criterion on a sheet that is probably
    fine, which is the failure this file has already paid for four times.
    """
    tasks = _what_reaches_the_page(payload, worksheet_type)
    return [_normalise(piece) for piece in _strings_in(tasks)]


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


def build_worksheet_repair_prompt(original_prompt, attempt, reason):
    """Ask again for a worksheet that failed one of its own checks.

    Not a retry. A retry sends the same request again and hopes for better
    luck; this sends back the sheet that *was* made, names everything wrong
    with it, and asks for those to be fixed. The reason is information the
    first request did not have.

    It exists for the fourth guard-refuses-correct-work, found live on
    2026-09-03. An investigation sheet evidenced a criterion in a results-table
    column the child writes in — the column is there, the child records in it,
    the criterion is genuinely evidenced — and the quote came back as a
    sentence *about* the column rather than the column's own text. The guard
    was right and the sheet was right, and the sheet was thrown away.

    Loosening the search is not the answer to that: the same check caught a
    cloze sheet claiming a task sentence that existed nowhere but inside its
    own claim, and a search loose enough to accept a paraphrase would accept
    that too. So the search does not move. What changes is that the sheet gets
    told what is wrong and gets one more go, and the second reply is checked by
    exactly the same code.

    **What it asks to be kept is the sheet, not the claims.** The commonest
    failure this handles is a pointer that does not match the task it points
    at, and re-rolling the whole worksheet over that throws away four tasks to
    fix a sentence.
    """
    return "\n".join(
        [
            original_prompt,
            "",
            "---",
            "",
            "You have already made this worksheet once and it was refused. "
            "This is exactly what you returned:",
            "",
            json.dumps(attempt, indent=2, ensure_ascii=False),
            "",
            "It was refused for these reasons:",
            "",
            str(reason),
            "",
            "Fix exactly those. Keep the tasks word for word — the sheet "
            "itself is wanted as it is, and this is a repair rather than a "
            "rewrite. Most of these failures are in the evidence rather than "
            "in the sheet: the task is there, and the quote does not match the "
            "words actually printed on it. Where that is the case, copy those "
            "words and change nothing else. Where a criterion genuinely has no "
            "task producing its evidence, add that task and quote it. Return "
            "the whole worksheet again, in the same shape, with the objective "
            "and the success criteria copied exactly as they were given to you.",
        ]
    )


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

    A sheet that fails its own coupling checks is asked for **once** more,
    carrying the attempt and every reason it was refused — see
    `build_worksheet_repair_prompt`. The checks themselves do not move: the
    repaired sheet goes through the same `validate_coupled_worksheet`, and a
    second failure is refused, which is what the screen reports honestly.
    Softening a check to make a second attempt pass would put a sheet that
    evidences nothing in front of a child.

    Only a `WorksheetCouplingError` is repairable, and deliberately so. A reply
    that ran out of room or came back unusable is a problem with the request
    rather than with the answer, and sending it again only doubles the cost of
    finding that out. A `WorksheetContentError` — a sheet the generator cannot
    build — is left refused as it was: it is a different class of failure, no
    live run has produced one, and an untested second attempt on a fault
    nobody has seen is a guess.

    Raises:
        WorksheetCouplingError: the objective or criteria drifted, or a
            criterion has no evidence on the sheet, after two attempts.
        WorksheetContentError: the sheet could not be rendered.
        TruncatedResponseError, json.JSONDecodeError: from the model call.
    """
    prompt = build_worksheet_prompt(
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
    )

    # The shape of this kind of sheet, sent with the request rather than
    # described in it -- see `planning/worksheet_schema.py`. The same schema
    # goes with the repair, which is the longer request of the two.
    schema = get_worksheet_schema(worksheet_type)

    def ask(text):
        return generate_structured_content(
            text,
            WORKSHEET_SYSTEM_PROMPT,
            max_tokens=WORKSHEET_MAX_TOKENS,
            timeout=WORKSHEET_TIMEOUT,
            stream=True,
            schema=schema,
        )

    def check(payload):
        return validate_coupled_worksheet(
            payload, lesson=lesson, worksheet_type=worksheet_type
        )

    # The ask stays outside the try on purpose, so that only a failed *check*
    # can reach the repair. Widening this to wrap the call as well is how a
    # reply that ran out of room gets sent a second time to run out of room
    # again.
    payload = ask(prompt)
    try:
        return check(payload)
    except WorksheetCouplingError as refused:
        logger.warning(
            "The worksheet for lesson %s failed its checks (%s). Asking once "
            "for a repair.",
            lesson.number,
            refused,
        )
        try:
            sheet = check(ask(build_worksheet_repair_prompt(prompt, payload, refused)))
        except WorksheetCouplingError as refused_again:
            raise WorksheetCouplingError(
                f"{refused_again}\n\nThis was the second attempt — the first "
                f"was sent back with the reasons it was refused and still did "
                f"not meet them."
            ) from refused_again
        logger.info(
            "The worksheet for lesson %s passed its checks on the repaired "
            "attempt.",
            lesson.number,
        )
        return sheet


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
