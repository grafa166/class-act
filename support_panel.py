"""The two boxes on the worksheet screen: what the children should do, and what
is getting in the way.

Her words, 2026-10-02 (relayed by Graeme): an optional box for *"What should
pupils actually do on this worksheet?"*, and a section for what the children
need help with, *"so the site removes the actual barrier rather than just
making the work easier."*

⚠️ **The barrier question is about the work, never the child.** She asked
*"what does this pupil need help with?"*; the word *pupil* invites a name into
a box sent to Anthropic. So it asks *"What is getting in the way?"*, as seven
tick-boxes with **no free text**, and shows the literal block that will be sent
-- drawn by the same function that builds it, so there is no second copy to
drift from what is actually sent.

⚠️ **Four of seven barriers change the printed sheet in this slice; three do
not.** Each ticked box says what *this kind of sheet* does about it, rather
than letting the screen imply all seven are handled.
"""

import streamlit as st

from llm.prompts import barrier_instructions
from planning.lesson import lowered_objective_flags
from planning.support import BARRIERS, what_this_sheet_does

TASK_LABEL = "What should pupils actually do on this worksheet?"

# A task is a sentence or two. Anything far longer is almost certainly the
# children's text pasted into the wrong box -- which, unlike a task that
# contradicts the objective, is something a check can actually see.
TASK_LIMIT = 600

TASK_HELP = (
    "Say what they do, in a sentence or two. How many questions there are and how "
    "long the passage is still come from the three levels."
)

TASK_SENT = (
    "Sent to Anthropic with the request. It is about the work, not the children — "
    "no names, please."
)

# Printed on the lesson page, which builds the sheets handed to children by a
# second, independent path that these boxes do not reach yet. Silence there
# would be the "nothing changes silently" failure.
NOT_ON_THIS_PAGE = (
    "The two boxes on the worksheet screen — what pupils should do, and what is "
    "getting in the way — are not used for the sheets made on this page. They "
    "only change sheets made on the worksheet screen."
)


def task_box_problem(task):
    """Why the task box should not be sent as it stands, or None."""
    task = (task or "").strip()
    if len(task) > TASK_LIMIT:
        return (
            f"This is {len(task):,} characters — longer than a task. If it is the text "
            "the children will read, put it in **Use your own text** further down. "
            "It is not sent from here until it is shorter."
        )
    flags = lowered_objective_flags({"What pupils will do": task})
    if flags:
        return flags[0][1]
    return None


def task_box(namespace):
    """Her answer, or "" if there is none or it cannot be sent as it stands."""
    task = st.text_area(
        TASK_LABEL,
        key=f"{namespace}_task",
        height=80,
        placeholder="e.g. Sort the rocks into two groups and say why each one belongs there.",
        help=TASK_HELP,
    ).strip()
    if not task:
        return ""
    st.caption(TASK_SENT)
    problem = task_box_problem(task)
    if problem and len(task) > TASK_LIMIT:
        st.warning(problem)
        return ""
    if problem:
        # A flag, never a refusal: the task is still sent.
        st.warning(problem)
    return task


def show_the_two_sentences(objective, task):
    """No check can tell whether a task fits the objective -- word overlap
    fails both ways at once. So she sees the two side by side instead."""
    if task:
        st.info(f"**Objective:** {objective}\n\n**They will:** {task}")


def barriers_panel(namespace, worksheet_type):
    """The barriers she ticked, as keys of `BARRIERS`, in her list's order."""
    st.markdown("### What is getting in the way?")
    st.caption(
        "Tick what is stopping them. This changes what is printed on the sheet, "
        "not just how hard it is."
    )
    ticked = tuple(
        key
        for key, label in BARRIERS.items()
        if st.checkbox(label, key=f"{namespace}_barrier_{key}")
    )
    if not ticked:
        return ()

    for key in ticked:
        _, sentence = what_this_sheet_does(key, worksheet_type)
        st.caption(f"**{BARRIERS[key]}** — {sentence}")

    with st.expander("Show me exactly what is sent", expanded=False):
        st.caption("This is the whole of it. Nothing typed goes with it.")
        st.code(barrier_instructions(ticked), language=None)
    return ticked
