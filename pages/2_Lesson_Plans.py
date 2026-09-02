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

This is the shell. It collects what a plan needs and shows what it would be
built from. It does not generate anything yet.
"""

import streamlit as st

from access import check_password
from curriculum import SUBJECT_REGISTRY
from curriculum.selection import list_objectives, list_topics
from planning.anchors import anchor_for, is_locked, suggest_lesson_count

st.set_page_config(page_title="Lesson Plans", page_icon="\U0001F4CB", layout="wide")

# Runs per page in a multipage app -- app.py's gate does not cover this file.
if not check_password():
    st.stop()


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
        "coverage and order are kept; the teaching is rebuilt."
    )
    st.text_area(
        f"What {anchor.scheme} says this unit covers",
        placeholder=(
            "Boost · Y3 Autumn 1 · Rocks and Soils\n"
            "Coverage: types of rock; properties; fossils; soil formation.\n"
            "Assessment: children know that rocks have different properties."
        ),
        height=140,
        key="plan_scheme_text",
    )
    st.file_uploader(
        "Or upload the plan the subject leader circulated",
        type=["docx", "pdf", "png", "jpg", "jpeg"],
        help="A photograph of a printed plan works too.",
        key="plan_scheme_file",
    )

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
