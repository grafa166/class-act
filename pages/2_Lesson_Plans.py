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
from llm.client import TruncatedResponseError
from planning.anchors import anchor_for, is_locked, suggest_lesson_count
from planning.scheme_intake import (
    SchemePlanError,
    UnreadableUploadError,
    read_scheme_plan,
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
    st.text_input(
        f"The {anchor.scheme} small step",
        placeholder="e.g. Represent numbers to 1,000",
        help="Typed exactly as it appears in the scheme. This becomes the objective.",
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

col_scope, col_weeks, col_lessons = st.columns(3)
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

col_ticks, col_note = st.columns(2)
with col_ticks:
    for label in (
        "Most were secure",
        "Needed more modelling",
        "Vocabulary was the barrier",
        "Ran out of time",
        "Didn't teach it",
    ):
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

# ── Not wired up yet ─────────────────────────────────────────────────────────

st.divider()
st.button(
    "Plan it",
    type="primary",
    disabled=True,
    help="Not connected yet — the generator is the next piece of work.",
)
st.caption(
    "This screen collects what a plan needs. Generation, the lesson document "
    "and the worksheet link are the next steps."
)
