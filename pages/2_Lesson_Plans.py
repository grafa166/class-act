"""Plan mode — the screen where a unit or a single lesson is planned.

Deliberately a separate page rather than a second branch inside `app.py`.

`app.py` is 1,380 lines of Streamlit whose behaviour depends on module-level
CSS, session-state initialisation order and rerun semantics, and until this
week nothing in the test suite executed it at all. Splitting it to make room
for a second mode would have meant restructuring the one part of this app that
already works, with no coverage to catch a mistake. Streamlit's pages folder
gives a second screen for free: the worksheet flow is not moved, re-indented or
re-flowed by anything here.

Consequences of that choice, both deliberate:
  * this page runs as its own script, so it repeats the password gate;
  * session state is namespaced `plan_*` so the two screens cannot collide.

It collects what a plan needs, and reads the scheme she is required to follow.
The lessons themselves are the next piece of work.
"""

import streamlit as st

from access import check_password
from curriculum import SUBJECT_REGISTRY
from curriculum.selection import list_objectives, list_topics
from generators.lesson_plan import (
    LessonPlanError,
    lesson_plan_bytes,
    lesson_plan_filename,
)
from generators.styles import DIFF_LEVELS
from llm.client import TruncatedResponseError
from llm.validation import WorksheetContentError
from planning.anchors import anchor_for, is_locked, suggest_lesson_count
from planning.worksheet_document import (
    build_worksheet_document,
    worksheet_filename,
)
from planning.scheme_intake import (
    SchemePlanError,
    UnreadableUploadError,
    read_scheme_plan,
)
from planning.lesson import (
    LessonError,
    generate_lesson,
    lowered_objective_flags,
)
from planning.spine import (
    SpineError,
    approved_spine,
    build_locked_spine,
    coverage_map,
    coverage_never_taught,
    generate_spine,
)
from planning.worksheet import (
    WorksheetCouplingError,
    generate_worksheet_for_lesson,
    repeated_task_shapes,
)

st.set_page_config(page_title="Lesson Plans", page_icon="\U0001F4CB", layout="wide")

# Runs per page in a multipage app -- app.py's gate does not cover this file.
if not check_password():
    st.stop()


# ── Reading the scheme ───────────────────────────────────────────────────────
#
# The result lives in session state rather than in a variable, because a
# Streamlit script re-runs from the top on every interaction: without this the
# coverage record would vanish the moment she ticked a box further down the
# page.

_READING_KEYS = (
    "plan_scheme_plan",
    "plan_scheme_flags",
    "plan_scheme_dropped",
    "plan_scheme_source",
    "plan_scheme_read_from",
)


def _fingerprint(pasted, uploads):
    """What a reading was made from, cheaply comparable on a later run."""
    return (pasted.strip(), tuple((name, len(data)) for name, data in uploads))


def _forget_the_reading():
    for key in _READING_KEYS:
        st.session_state.pop(key, None)


def _read_the_scheme(scheme, subject, year_group, pasted, uploads):
    """Read the plan, and keep a result only if it survived checking.

    Every failure clears the previous reading. A coverage list left on screen
    beside an error would be read as the plan that was just accepted.
    """
    st.session_state.pop("plan_scheme_error", None)
    try:
        with st.spinner(f"Reading your {scheme} plan…"):
            reading = read_scheme_plan(
                scheme=scheme,
                subject=subject,
                year_group=year_group,
                pasted_text=pasted,
                uploads=uploads,
            )
    except (UnreadableUploadError, SchemePlanError) as exc:
        # Both already explain themselves in the teacher's terms.
        _forget_the_reading()
        st.session_state["plan_scheme_error"] = str(exc)
        return
    except TruncatedResponseError:
        _forget_the_reading()
        st.session_state["plan_scheme_error"] = (
            "Claude ran out of room before it finished reading, so nothing has "
            "been used. Paste just the unit page — the coverage list and the "
            "title are all this needs."
        )
        return
    except Exception as exc:  # noqa: BLE001 - a teacher cannot act on a traceback
        _forget_the_reading()
        st.session_state["plan_scheme_error"] = f"Could not read the plan: {exc}"
        return

    st.session_state["plan_scheme_plan"] = reading.plan
    st.session_state["plan_scheme_flags"] = reading.flagged
    st.session_state["plan_scheme_dropped"] = reading.dropped
    st.session_state["plan_scheme_source"] = reading.source
    st.session_state["plan_scheme_read_from"] = _fingerprint(pasted, uploads)


def _show_the_reading(current):
    """What was read, and what is worth her eye before anything is built on it."""
    error = st.session_state.get("plan_scheme_error")
    if error:
        st.error(error, icon="\U0001F6AB")

    plan = st.session_state.get("plan_scheme_plan")
    if not plan:
        return

    source = st.session_state.get("plan_scheme_source") or "what you gave it"
    st.success(
        f"Read **{plan.unit_title}** from {source} — {len(plan.coverage)} "
        f"thing{'s' if len(plan.coverage) != 1 else ''} this unit has to cover.",
        icon="\U0001F4D6",
    )

    if st.session_state.get("plan_scheme_read_from") != current:
        # The coverage list is what she would hand a subject leader. It must
        # never quietly describe a page she has since changed.
        st.warning(
            "You have changed the plan since this was read, so everything below "
            "is the older version. Read it again.",
            icon="⚠️",
        )

    dropped = st.session_state.get("plan_scheme_dropped") or []
    if dropped:
        # Never restored on her behalf: putting a line into the coverage record
        # that the extraction did not put there is how an invented one would get
        # in. Shown instead, for her to add or dismiss.
        st.warning(
            "**Read off your plan, but missing from the coverage below.** Check "
            "each one against your page — if it belongs, paste it into the box "
            "before you plan the unit:\n\n"
            + "\n".join(f"- {item}" for item in dropped),
            icon="⚠️",
        )

    st.markdown("**Kept — this unit still has to cover all of this:**")
    st.markdown("\n".join(f"- {item}" for item in plan.coverage))

    if plan.assessment:
        st.markdown("**The assessment the subject leader set:**")
        st.markdown("\n".join(f"- {item}" for item in plan.assessment))

    # Suggested activities are extracted and kept as context for the generator,
    # but not shown: they are the part being rebuilt, and listing them here
    # invites the scheme's thin teaching back in through the front door.

    flags = st.session_state.get("plan_scheme_flags") or []
    if flags:
        st.markdown(
            "**Worth a look before the lessons are written.** Nothing has been "
            "changed — these are exactly as the scheme wrote them:"
        )
        st.markdown(
            "\n".join(f"- *{item}* — {reason}" for item, reason in flags)
        )


# ── The sequence ─────────────────────────────────────────────────────────────

_SPINE_KEYS = (
    "plan_spine",
    "plan_spine_built_from",
    "plan_spine_source",
    # Lessons belong to the sequence they were written from. Keeping them across
    # a re-plan would show lessons for objectives that no longer exist. Named
    # apart from the "plan_lessons" count widget: one key cannot mean two
    # things, and popping a widget's key deletes what the teacher typed.
    "plan_written_lessons",
    "plan_written_error",
    "plan_written_expected",
)


def _what_to_build_on():
    """The ticks and the optional note, as one line for the request.

    The ticks come first deliberately: they are the route that carries no pupil
    data at all, and they work on their own.
    """
    ticked = [label for label in TICKS if st.session_state.get(f"plan_tick_{label}")]
    note = (st.session_state.get("plan_build_on") or "").strip()
    return " · ".join(ticked + ([note] if note else []))


def _build_the_spine(
    anchor,
    subject,
    year_group,
    lesson_count,
    outcome,
    objectives,
    coverage,
    unit_title,
    build_on,
    small_steps,
    signature,
):
    """Draft or assemble the chain of objectives.

    A mandated scheme takes the assembled route, which makes no model call, so
    the guarantee that its order survives is structural rather than a request in
    a prompt.
    """
    st.session_state.pop("plan_spine_error", None)
    try:
        if is_locked(anchor.subject):
            spine = build_locked_spine(
                small_steps.splitlines(), outcome=outcome, scheme=anchor.scheme
            )
        else:
            with st.spinner("Working out the order these need to be taught in…"):
                spine = generate_spine(
                    subject=subject,
                    year_group=year_group,
                    lesson_count=lesson_count,
                    outcome=outcome,
                    objectives=objectives,
                    coverage=coverage,
                    scheme=anchor.scheme,
                    unit_title=unit_title,
                    build_on=build_on,
                )
    except SpineError as exc:
        _forget_the_spine()
        st.session_state["plan_spine_error"] = str(exc)
        return
    except TruncatedResponseError:
        _forget_the_spine()
        st.session_state["plan_spine_error"] = (
            "Claude ran out of room before finishing the sequence, so nothing "
            "has been used. Try fewer lessons."
        )
        return
    except Exception as exc:  # noqa: BLE001 - a teacher cannot act on a traceback
        _forget_the_spine()
        st.session_state["plan_spine_error"] = f"Could not plan the sequence: {exc}"
        return

    _forget_the_spine()
    st.session_state["plan_spine"] = spine
    st.session_state["plan_spine_source"] = spine.source
    st.session_state["plan_spine_built_from"] = signature
    # Drop any objective she edited on a previous sequence: they belong to
    # lessons that no longer exist.
    for key in [k for k in st.session_state if k.startswith("plan_spine_objective_")]:
        st.session_state.pop(key, None)


def _forget_the_spine():
    for key in _SPINE_KEYS:
        st.session_state.pop(key, None)


def _show_the_spine(current, coverage):
    """The chain, editable, with the coverage it accounts for."""
    error = st.session_state.get("plan_spine_error")
    if error:
        st.error(error, icon="\U0001F6AB")

    spine = st.session_state.get("plan_spine")
    if not spine:
        return

    st.caption(st.session_state.get("plan_spine_source", ""))

    if st.session_state.get("plan_spine_built_from") != current:
        st.warning(
            "You have changed the unit since this sequence was planned, so it "
            "is the older version. Plan it again.",
            icon="⚠️",
        )

    edited = []
    edited_objectives = {}
    for lesson in spine.lessons:
        heading = f"**Lesson {lesson.number}**"
        if lesson.assesses_outcome:
            heading += " · assesses the end-of-unit outcome"
        st.markdown(heading)
        objective = st.text_input(
            f"Objective for lesson {lesson.number}",
            value=lesson.objective,
            key=f"plan_spine_objective_{lesson.number}",
            label_visibility="collapsed",
        )
        # What she has on screen right now, which is what the lessons are
        # written from -- not what was drafted.
        edited_objectives[lesson.number] = objective
        if objective.strip() != lesson.objective:
            edited.append(lesson.number)
        if lesson.builds_on is None:
            st.caption("Starting point — no lesson before this one.")
        else:
            st.caption(
                f"Builds on lesson {lesson.builds_on} — {lesson.builds_on_reason}"
            )

    if edited:
        # She may change an objective the later reasons were written against.
        # Said out loud rather than left for her to notice.
        st.info(
            "You have changed the objective for lesson "
            + ", ".join(str(number) for number in edited)
            + ". The reasons above still describe what was drafted, so check "
            "the lessons after it still follow.",
            icon="✏️",
        )

    if coverage:
        _show_the_coverage_map(spine, coverage)

    st.divider()
    st.markdown("### 7 · The lessons")
    st.caption(
        "Written one at a time from the objectives above, so each knows what "
        "came before it and what is still to come. A minute or two per "
        "lesson, so leave it running."
    )
    if st.button("Write all the lessons", type="primary", key="plan_write_lessons"):
        _write_the_lessons(spine, edited_objectives)
    _show_the_lessons()


def _write_the_lessons(spine, edited_objectives):
    """Write every lesson of the sequence, one call at a time.

    One call per lesson because a unit of six would not fit in one reply, and a
    reply cut short at a tidy point parses perfectly and renders a short lesson.

    A failure part-way keeps the lessons already written -- three good lessons
    are worth having -- but says plainly which ones are missing, because a unit
    that looks complete and is not is the failure this whole screen exists to
    avoid.
    """
    st.session_state.pop("plan_written_error", None)
    st.session_state["plan_written_lessons"] = {}

    try:
        approved = approved_spine(spine, edited_objectives)
    except SpineError as exc:
        st.session_state["plan_written_error"] = str(exc)
        return

    scheme_plan = st.session_state.get("plan_scheme_plan")
    written = {}
    progress = st.progress(0.0, text="Writing lesson 1…")

    for position, lesson in enumerate(approved.lessons, 1):
        progress.progress(
            (position - 1) / len(approved.lessons),
            text=f"Writing lesson {lesson.number} of {len(approved.lessons)}…",
        )
        try:
            written[lesson.number] = generate_lesson(
                spine=approved,
                number=lesson.number,
                subject=st.session_state.get("plan_subject", ""),
                year_group=st.session_state.get("plan_year", ""),
                lesson_minutes=int(st.session_state.get("plan_minutes", 60)),
                coverage=lesson.covers,
                build_on=_what_to_build_on(),
                outcome=st.session_state.get("plan_outcome", ""),
            )
        except LessonError as exc:
            st.session_state["plan_written_error"] = (
                f"Lesson {lesson.number} could not be written: {exc}"
            )
            break
        except TruncatedResponseError:
            st.session_state["plan_written_error"] = (
                f"Lesson {lesson.number} ran out of room before it finished, so "
                f"it has not been used. Try a shorter lesson length."
            )
            break
        except Exception as exc:  # noqa: BLE001 - a teacher cannot act on a traceback
            st.session_state["plan_written_error"] = (
                f"Lesson {lesson.number} could not be written: {exc}"
            )
            break

    progress.empty()
    st.session_state["plan_written_lessons"] = written
    st.session_state["plan_written_expected"] = len(approved.lessons)


def _show_the_lessons():
    """The written lessons, and an honest account of any that are missing."""
    error = st.session_state.get("plan_written_error")
    written = st.session_state.get("plan_written_lessons") or {}

    if error:
        st.error(error, icon="\U0001F6AB")

    if not written:
        return

    expected = st.session_state.get("plan_written_expected", len(written))
    if len(written) < expected:
        missing = [n for n in range(1, expected + 1) if n not in written]
        st.warning(
            f"{len(written)} of {expected} lessons were written. Nothing exists "
            f"for lesson{'s' if len(missing) != 1 else ''} "
            + ", ".join(str(n) for n in missing)
            + " — the unit is incomplete.",
            icon="⚠️",
        )

    st.caption("AI-drafted — check before teaching.")

    for number in sorted(written):
        _show_one_lesson(written[number])

    for flag in repeated_task_shapes(
        [st.session_state["plan_worksheets"][n]
         for n in sorted(st.session_state.get("plan_worksheets") or {})]
    ):
        # A flag, not a refusal. She may have a reason, and the sequence is
        # never changed for her.
        st.warning(flag, icon="⚠️")


def _show_one_lesson(lesson):
    with st.expander(f"Lesson {lesson.number} · {lesson.objective}", expanded=False):
        st.markdown(f"**Objective** — {lesson.objective}")
        if lesson.builds_on:
            st.caption(
                f"Builds on lesson {lesson.builds_on} — {lesson.builds_on_reason}"
            )

        st.markdown("**Success criteria, and what shows a child met them**")
        st.markdown(
            "\n".join(
                f"- {c.criterion} — *{c.evidence}*" for c in lesson.success_criteria
            )
        )

        vocab = lesson.vocabulary
        st.markdown("**Vocabulary, in three bands**")
        st.markdown(
            f"- **Everyone leaves with**: {', '.join(vocab.everyone)}\n"
            f"- **Expected**: {', '.join(vocab.expected)}\n"
            f"- **Stretch**: {', '.join(vocab.stretch)}\n\n{vocab.guidance}"
        )

        st.markdown("**The lesson, step by step**")
        for step in lesson.steps:
            st.markdown(f"**{step.minutes} min · {step.name}**")
            lines = [
                f"- *On the board*: {step.on_the_board}",
                f"- *You say*: {step.teacher_says}",
            ]
            lines += [
                f"- *Ask*: {q.ask} → expect: {q.expect}" for q in step.questions
            ]
            lines.append(f"- *Children*: {step.children_do}")
            lines += [
                f"- *Watch for*: {w.wrong} → {w.respond}" for w in step.watch_for
            ]
            if step.adults:
                lines.append(f"- *Other adult*: {step.adults}")
            st.markdown("\n".join(lines))

        st.markdown("**Misconceptions to expect**")
        st.markdown(
            "\n".join(
                f"- {m['misconception']}"
                + (f" — {m['address']}" if m["address"] else "")
                for m in lesson.misconceptions
            )
        )

        st.markdown("**Assessment**")
        st.markdown(
            f"- *Look for*: {lesson.assessment.look_for}\n"
            f"- *Not yet met looks like*: {lesson.assessment.not_yet_example}"
        )

        st.markdown("**Same objective, different route in**")
        st.markdown(
            "\n".join(
                f"- **{name.upper() if name != 'stretch' else 'Stretch'}**: {text}"
                for name, text in lesson.adaptations.items()
            )
        )
        for where, reason in lowered_objective_flags(lesson.adaptations):
            # An adaptation changes how a child reaches the objective, never
            # which objective they are reaching.
            st.warning(f"{where}\n\n{reason}", icon="⚠️")

        st.markdown("**Resources**")
        st.markdown(
            "\n".join(f"- {r['quantity']} — {r['item']}" for r in lesson.resources)
        )

        if lesson.next_lesson:
            st.caption(f"Next lesson: {lesson.next_lesson}")

        _the_worksheet_for(lesson)
        _the_document_for(lesson)


# ── The plan as a document she can edit ──────────────────────────────────────
#
# Arial, black and blue, and every box a paragraph rather than a one-cell
# table, so pressing Enter inside one adds a line instead of fighting a table.
# The font is hers to change: it is the one piece of the typography decision
# that is a preference rather than a rule, and she is the one who has to read
# it at seven in the morning.

# The joined font used elsewhere in school is deliberately absent, not left to
# her to avoid: children still decoding, and SEND children in particular,
# cannot read it. Comic Sans is out for the same kind of reason.
PLAN_FONTS = ("Arial", "Verdana", "Tahoma", "Calibri", "Century Gothic")

# What Word documents are, spelled out once rather than twice.
DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _the_document_for(lesson):
    """The plan, as a Word file, with this lesson's worksheet if she made one."""
    st.divider()

    font = st.selectbox(
        "Font for the document",
        PLAN_FONTS,
        key=f"plan_doc_font_{lesson.number}",
        help="Arial by default. The joined handwriting font is not offered — "
        "children still learning to decode cannot read it.",
    )

    spine = st.session_state.get("plan_spine")
    scheme_plan = st.session_state.get("plan_scheme_plan")
    anchor = anchor_for(st.session_state.get("plan_subject", ""))
    unit_title = getattr(scheme_plan, "unit_title", "") or ", ".join(
        st.session_state.get("plan_topics") or []
    )

    try:
        document = lesson_plan_bytes(
            lesson=lesson,
            unit_title=unit_title,
            subject=st.session_state.get("plan_subject", ""),
            year_group=st.session_state.get("plan_year", ""),
            lesson_minutes=int(st.session_state.get("plan_minutes", 60)),
            lesson_count=len(spine.lessons) if spine else None,
            anchor=anchor.scheme or anchor.note,
            outcome=st.session_state.get("plan_outcome", ""),
            # Only if she has actually made one. A plan that names a sheet
            # that does not exist is a plan that lies.
            worksheet=(st.session_state.get("plan_worksheets") or {}).get(
                lesson.number
            ),
            font=font,
        )
    except LessonPlanError as exc:
        # The one thing the document refuses: another lesson's sheet printed
        # as this lesson's evidence.
        st.error(str(exc), icon="\U0001F6AB")
        return

    st.download_button(
        "Download this lesson plan",
        data=document,
        file_name=lesson_plan_filename(lesson, unit_title),
        mime=DOCX_MIME,
        key=f"plan_doc_{lesson.number}",
    )


# ── The worksheet, built from the lesson ─────────────────────────────────────
#
# The headline feature. A worksheet made here inherits the lesson's objective
# and success criteria word for word and has to produce the evidence each
# criterion names -- so the plan, the sheet and the child's book agree.

# Plain names for the ten generators. She is choosing a kind of task, not a
# module.
WORKSHEET_KINDS = {
    "cloze": "Fill in the gaps",
    "word_bank": "Word bank and sentences",
    "matching": "Matching",
    "sentence_builder": "Building sentences",
    "reading_comprehension": "Reading and questions",
    "problem_solving": "Word problems",
    "calculation_practice": "Calculation practice",
    "fraction_practice": "Fractions practice",
    "times_tables": "Times tables",
    "investigation": "Investigation planner",
}

# Where to start, per subject. A starting point only -- every kind stays on the
# list, because the subject does not decide what a lesson needs.
DEFAULT_KIND = {
    "Maths": "calculation_practice",
    "English": "cloze",
    "Science": "investigation",
}


def _the_worksheet_for(lesson):
    """Make and show the worksheet belonging to one lesson."""
    st.divider()
    st.markdown("**The worksheet for this lesson**")
    st.caption(
        "It carries this lesson's objective and success criteria word for "
        "word, and has to produce the evidence each criterion names."
    )

    subject = st.session_state.get("plan_subject", "")
    kinds = list(WORKSHEET_KINDS)
    default = DEFAULT_KIND.get(subject, "word_bank")

    col_kind, col_level = st.columns(2)
    with col_kind:
        kind = st.selectbox(
            "Kind of task",
            kinds,
            index=kinds.index(default),
            format_func=lambda key: WORKSHEET_KINDS[key],
            key=f"plan_ws_kind_{lesson.number}",
        )
    with col_level:
        level = st.selectbox(
            "Pitched for",
            list(DIFF_LEVELS),
            index=list(DIFF_LEVELS).index("expected"),
            format_func=lambda key: DIFF_LEVELS[key]["label"],
            key=f"plan_ws_level_{lesson.number}",
        )

    if st.button(
        "Make the worksheet", key=f"plan_make_ws_{lesson.number}"
    ):
        _make_the_worksheet(lesson, kind, level)

    _show_the_worksheet(lesson)


def _make_the_worksheet(lesson, kind, level):
    """One call, then checked against the lesson before it is shown."""
    st.session_state.setdefault("plan_worksheets", {})
    st.session_state.setdefault("plan_worksheet_errors", {})
    st.session_state["plan_worksheets"].pop(lesson.number, None)
    st.session_state["plan_worksheet_errors"].pop(lesson.number, None)

    written = st.session_state.get("plan_written_lessons") or {}
    earlier = [
        written[number].objective
        for number in sorted(written)
        if lesson.number is not None and number < lesson.number
    ]

    try:
        with st.spinner(f"Making the worksheet for lesson {lesson.number}…"):
            sheet = generate_worksheet_for_lesson(
                lesson=lesson,
                worksheet_type=kind,
                subject=st.session_state.get("plan_subject", ""),
                year_group=st.session_state.get("plan_year", ""),
                level=level,
                earlier_objectives=earlier,
            )
    except (WorksheetCouplingError, WorksheetContentError) as exc:
        # Refused rather than shown. A sheet whose objective drifted looks
        # completely normal on paper, which is exactly the failure.
        st.session_state["plan_worksheet_errors"][lesson.number] = str(exc)
        return
    except TruncatedResponseError:
        st.session_state["plan_worksheet_errors"][lesson.number] = (
            "The worksheet ran out of room before it finished, so it has not "
            "been used. Try a shorter kind of task."
        )
        return
    except Exception as exc:  # noqa: BLE001 - a teacher cannot act on a traceback
        st.session_state["plan_worksheet_errors"][lesson.number] = (
            f"The worksheet could not be made: {exc}"
        )
        return

    st.session_state["plan_worksheets"][lesson.number] = sheet


def _show_the_worksheet(lesson):
    """The sheet, and what on it evidences each criterion."""
    error = (st.session_state.get("plan_worksheet_errors") or {}).get(lesson.number)
    if error:
        st.error(error, icon="\U0001F6AB")

    sheet = (st.session_state.get("plan_worksheets") or {}).get(lesson.number)
    if not sheet:
        return

    st.success(f"**{sheet.content.get('title', 'Worksheet')}**", icon="\U0001F4DD")
    st.caption(sheet.source)
    st.markdown(f"*Objective on the sheet* — {sheet.objective}")

    # The part that makes this more than a themed activity: every criterion,
    # and the task that produces the evidence for it.
    st.markdown("**What on this sheet shows each criterion was met**")
    by_criterion = {}
    for claim in sheet.evidence:
        by_criterion.setdefault(claim.criterion, []).append(claim)

    for criterion in sheet.success_criteria:
        claims = by_criterion.get(criterion.criterion, [])
        st.markdown(
            f"- **{criterion.criterion}**\n"
            + "\n".join(
                f"    - *{claim.where}*: {claim.quote} → the child writes "
                f"{claim.pupil_writes}"
                for claim in claims
            )
        )

    _offer_the_worksheet(lesson, sheet)


def _offer_the_worksheet(lesson, sheet):
    """The sheet she prints, and the answers.

    Until 2026-09-04 there was nothing here. The plan page had one download
    button, for the lesson plan, and a worksheet could be made, checked and
    shown — and never taken out of the app. A worksheet she cannot hand out is
    not a worksheet.
    """
    # The same title the lesson plan is named after, so a unit's plans and
    # sheets sit together in her Downloads folder rather than under two names.
    scheme_plan = st.session_state.get("plan_scheme_plan")
    unit_title = getattr(scheme_plan, "unit_title", "") or ", ".join(
        st.session_state.get("plan_topics") or []
    )
    font = st.session_state.get(f"plan_doc_font_{lesson.number}", PLAN_FONTS[0])
    level = st.session_state.get(f"plan_ws_level_{lesson.number}", "expected")

    try:
        for_the_children = build_worksheet_document(sheet, level=level, font=font)
        for_her = build_worksheet_document(
            sheet, level=level, font=font, show_answers=True
        )
    except Exception as exc:  # noqa: BLE001 - a teacher cannot act on a traceback
        # The sheet passed its checks and still could not be drawn. Rare — the
        # shape sent with every request forbids it — but a traceback in front
        # of her is the worst possible version of this.
        st.error(
            "This worksheet passed its checks but could not be turned into a "
            "document, so there is nothing to download. Make it again — this "
            f"is usually a one-off. ({exc})",
            icon="\U0001F6AB",
        )
        return

    left, right = st.columns(2)
    with left:
        st.download_button(
            "Download the worksheet",
            data=for_the_children,
            file_name=worksheet_filename(sheet, unit_title),
            mime=DOCX_MIME,
            key=f"plan_ws_doc_{lesson.number}",
            use_container_width=True,
        )
    with right:
        st.download_button(
            "Download the answers",
            data=for_her,
            file_name=worksheet_filename(sheet, unit_title, answers=True),
            mime=DOCX_MIME,
            key=f"plan_ws_answers_{lesson.number}",
            use_container_width=True,
        )


def _show_the_coverage_map(spine, coverage):
    """Every line the scheme named, and which lesson now teaches it.

    Her evidence to the subject leader that nothing was dropped. A line no
    lesson teaches is shown as a gap rather than left out — a map with a line
    quietly absent is the same failure as dropping it.
    """
    mapping = coverage_map(spine, coverage)
    st.markdown("**What the scheme said this unit covers, and where it now is:**")
    st.markdown(
        "\n".join(
            f"- {line} — "
            + (
                "lesson " + ", ".join(str(n) for n in lessons)
                if lessons
                else "**no lesson teaches this**"
            )
            for line, lessons in mapping.items()
        )
    )

    gaps = [line for line, lessons in mapping.items() if not lessons]
    if gaps:
        st.warning(
            f"{len(gaps)} of {len(coverage)} things the scheme named are not "
            "taught by any lesson in this sequence. Add a lesson, or say where "
            "else the class covers them — the sequence is not changed for you.",
            icon="⚠️",
        )

    assessed_only = coverage_never_taught(spine, coverage)
    if assessed_only:
        # The map above says the last lesson covers these. It is the only lesson
        # that does, and it is the one that assesses the unit -- so on paper
        # they are covered and in practice they were never taught.
        st.warning(
            "**Covered only by the last lesson, which is the assessment.** The "
            "map above counts these as taught, but nothing before the "
            "assessment teaches them:\n\n"
            + "\n".join(f"- {line}" for line in assessed_only),
            icon="⚠️",
        )


with st.sidebar:
    st.markdown("## \U0001F3EB Class Act")
    # Mirrors app.py: the automatic page menu is off, so each screen carries
    # its own named links.
    st.page_link("app.py", label="Worksheets", icon="\U0001F4DD")
    st.page_link("pages/2_Lesson_Plans.py", label="Lesson Plans", icon="\U0001F4CB")
    st.markdown("---")

st.title("\U0001F4CB Plan a unit")
st.caption(
    "Objectives that build on each other, success criteria that match them, "
    "and worksheets made from the lesson they belong to."
)

# ── 1 · Where does this come from? ───────────────────────────────────────────

st.markdown("### 1 · Where does this lesson come from?")

col_subject, col_year = st.columns(2)
with col_subject:
    subject = st.selectbox(
        "Subject", list(SUBJECT_REGISTRY), key="plan_subject"
    )
with col_year:
    years = SUBJECT_REGISTRY[subject]["years"]
    year_group = st.selectbox(
        "Year group",
        years,
        index=min(2, len(years) - 1),
        key="plan_year",
    )

anchor = anchor_for(subject)

if is_locked(anchor.subject):
    # The one case where the app must not think for itself. Stated plainly on
    # screen so the teacher can see the constraint being honoured rather than
    # having to trust it.
    st.error(
        f"**{anchor.scheme} is locked.** {anchor.note}",
        icon="\U0001F512",
    )
else:
    scheme = anchor.scheme or "No published scheme"
    st.info(f"**{scheme} — yours to build.** {anchor.note}", icon="✏️")

# ── 2 · The objective ────────────────────────────────────────────────────────

st.markdown("### 2 · What is being taught")

strands = list(SUBJECT_REGISTRY[subject]["curriculum"][year_group])
strand = st.selectbox("Strand", strands, key="plan_strand")

objectives = list_objectives(subject, year_group, strand)
topics = list_topics(subject, year_group, strand)

if is_locked(anchor.subject):
    # For a mandated scheme the objective is the scheme's, not ours. She pastes
    # the small step; we do not offer a curriculum objective that might quietly
    # differ from what the school has agreed to teach.
    st.text_area(
        f"The {anchor.scheme} small steps — one per line",
        placeholder=(
            "Represent numbers to 1,000\n"
            "Partition numbers to 1,000\n"
            "Compare numbers to 1,000"
        ),
        height=120,
        help=(
            "Typed exactly as they appear in the scheme, in the order the scheme "
            "teaches them. These become the objectives, word for word, and "
            "nothing here re-orders them."
        ),
        key="plan_small_step",
    )
else:
    st.multiselect(
        "Objectives this unit covers",
        objectives,
        default=objectives[:1],
        help=(
            "The whole strand is listed. Objectives are not tied to the topics "
            "below -- the two lists are independent, so choose deliberately."
        ),
        key="plan_objectives",
    )
    st.multiselect(
        "Topics (optional)",
        topics,
        help="Context for the generator. Does not set the objective.",
        key="plan_topics",
    )
    if not st.session_state.get("plan_objectives"):
        # Changing subject empties this box, because the objectives it held
        # belong to the subject before. Said out loud: an empty box below a
        # subject you have just chosen looks like a screen still loading.
        st.caption(
            "Pick at least one — the sequence is built from these, and "
            "changing subject clears them."
        )

# ── 3 · Bring your own scheme ────────────────────────────────────────────────

if anchor.teacher_supplies_content and not is_locked(anchor.subject):
    st.markdown(f"### 3 · Your {anchor.scheme} plan")
    st.caption(
        f"{anchor.scheme} is copyrighted, so this app never ships its content. "
        "Paste the unit page or the medium-term plan you have to follow. Its "
        "coverage and order are kept; the teaching is rebuilt. What you give it "
        "is sent to Anthropic to be read, so keep it to the unit page rather "
        "than whole chapters."
    )
    pasted_plan = st.text_area(
        f"What {anchor.scheme} says this unit covers",
        placeholder=(
            "Boost · Y3 Autumn 1 · Rocks and Soils\n"
            "Coverage: types of rock; properties; fossils; soil formation.\n"
            "Assessment: children know that rocks have different properties."
        ),
        height=140,
        key="plan_scheme_text",
    )
    uploaded_plans = st.file_uploader(
        "Or upload the plan the subject leader circulated",
        type=["docx", "pdf", "png", "jpg", "jpeg", "txt"],
        # A printed medium-term plan is two sides of A4 more often than one.
        accept_multiple_files=True,
        help="A photograph of a printed plan works too.",
        key="plan_scheme_file",
    )

    uploads = [(f.name, f.getvalue()) for f in uploaded_plans or []]

    if st.button("Read my plan", key="plan_read_scheme"):
        _read_the_scheme(anchor.scheme, subject, year_group, pasted_plan, uploads)

    _show_the_reading(_fingerprint(pasted_plan, uploads))

# ── 4 · Shape of the unit ────────────────────────────────────────────────────

st.markdown("### 4 · Shape of the unit")

col_scope, col_weeks, col_lessons, col_minutes = st.columns(4)
with col_scope:
    scope = st.radio(
        "Plan",
        ["A whole unit", "A single lesson"],
        help="A unit is written in one pass so it hangs together. Any single "
        "lesson can be re-planned afterwards.",
        key="plan_scope",
    )
with col_weeks:
    weeks = st.number_input(
        "Weeks left in term", min_value=1, max_value=14, value=6, key="plan_weeks"
    )
with col_lessons:
    chosen_objectives = st.session_state.get("plan_objectives", objectives[:1])
    suggested = suggest_lesson_count(weeks=weeks, objectives=len(chosen_objectives))
    st.number_input(
        "Lessons",
        min_value=1,
        max_value=20,
        value=suggested if scope == "A whole unit" else 1,
        help=f"Suggested: {suggested}. Six is not a rule -- override freely.",
        key="plan_lessons",
    )
with col_minutes:
    # The step timings are checked against this, so a plan cannot come back
    # needing seventy minutes of a sixty-minute slot.
    st.number_input(
        "Minutes per lesson",
        min_value=20,
        max_value=120,
        value=60,
        step=5,
        key="plan_minutes",
    )

st.text_input(
    "End-of-unit outcome",
    placeholder=(
        "e.g. Children group a set of unknown rocks by their physical "
        "properties and justify each grouping."
    ),
    help="What the last lesson has to produce or assess.",
    key="plan_outcome",
)

# ── 5 · What to build on ─────────────────────────────────────────────────────

st.markdown("### 5 · What should this build on?")
st.caption(
    "What the class actually did and where they got stuck. Ticks are enough; "
    "the box is optional."
)

TICKS = (
    "Most were secure",
    "Needed more modelling",
    "Vocabulary was the barrier",
    "Ran out of time",
    "Didn't teach it",
)

col_ticks, col_note = st.columns(2)
with col_ticks:
    for label in TICKS:
        st.checkbox(label, key=f"plan_tick_{label}")
with col_note:
    st.text_area(
        "Anything else? (optional)",
        placeholder="e.g. permeability confused everyone",
        height=120,
        key="plan_build_on",
    )
    # Named on screen, not buried in a policy page. The field predictably
    # attracts pupil names, and "we did not ask for them" is not a control.
    st.warning(
        "**No names, please.** This text is sent to Anthropic to write the "
        "next lesson. The ticks alone work fine.",
        icon="⚠️",
    )

# ── 6 · The sequence ─────────────────────────────────────────────────────────

st.divider()
st.markdown("### 6 · The sequence")
st.caption(
    "The chain of objectives, and why each lesson needs the one before it. "
    "This is the part worth your judgement, so it comes first and on its own — "
    "read it, change anything you disagree with, and the lessons get written "
    "from what you approved."
)

small_steps = st.session_state.get("plan_small_step", "")
build_on = _what_to_build_on()
scheme_plan = st.session_state.get("plan_scheme_plan")
coverage = list(scheme_plan.coverage) if scheme_plan else []
lesson_count = int(st.session_state.get("plan_lessons", 1))
outcome = st.session_state.get("plan_outcome", "")

if is_locked(anchor.subject):
    # No model call at all. The steps she typed become the objectives, in her
    # order. Nothing in this path is capable of re-sequencing them.
    st.caption(
        f"Assembled from your {anchor.scheme} steps — no sequence is generated "
        f"for a locked scheme."
    )

signature = (
    subject,
    year_group,
    lesson_count,
    outcome.strip(),
    tuple(chosen_objectives),
    tuple(coverage),
    build_on,
    small_steps.strip(),
)

if st.button("Plan the sequence", type="primary", key="plan_build_spine"):
    _build_the_spine(
        anchor=anchor,
        subject=subject,
        year_group=year_group,
        lesson_count=lesson_count,
        outcome=outcome,
        objectives=chosen_objectives,
        coverage=coverage,
        unit_title=scheme_plan.unit_title if scheme_plan else None,
        build_on=build_on,
        small_steps=small_steps,
        signature=signature,
    )

_show_the_spine(signature, coverage)
