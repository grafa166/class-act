"""The box on the worksheet screen where she brings her own text.

One editable box is the source. An upload *fills* that box rather than being
held somewhere alongside it, so what she can see is exactly what will be sent —
there is no second copy, and no confirmed flag to forget to set.

A PDF or a photograph is the exception, because nothing here can read one: it
is carried as blocks for Claude to look at, the box stays empty, and the panel
says out loud which of the four things it can still do with it.

⚠️ **The panel is given the worksheet type, not a list of actions.** The plan
wrote `source_panel("ws", actions_for(worksheet_type_key))`, and that cannot
work: what she may ask for depends on what she supplied — *use exactly* is
impossible on a photograph — and the source is only known in here. Passing a
list settled before the upload either offers word-for-word reproduction of a
scan, or puts a second copy of the narrowing rule in this file. `actions_for`
stays the one definition of it instead.
"""

import streamlit as st

from planning.source_material import (
    WORKSHEET_ACTIONS,
    SourceMaterialError,
    actions_for,
    pages_in,
    read_upload,
    source_from_text,
)

# Word, plain text and markdown give us the words. A PDF or a photograph does
# not — and is still accepted, because a photocopy in a folder is the realistic
# case (`planning/scheme_intake.py:13`) and a page from the Boost book *is* a
# scan.
ACCEPTED_FILES = ["txt", "md", "docx", "pdf", "png", "jpg", "jpeg", "webp"]

HELD = (
    "We have the words, so this can be printed word for word and the names on "
    "the sheet checked against it."
)
NOT_HELD = (
    "Claude can read this, but nothing here can. So it can be built from — not "
    "reproduced word for word, and the names on the sheet cannot be checked "
    "against it."
)

SENT_AWAY = (
    "What you put here is sent to Anthropic to be read. It is not saved "
    "anywhere by this app."
)

PICK_THE_PAGES = (
    "Only these pages are sent. The rest of the file stays on this computer, so "
    "nothing on the sheet can come from a page the children have not reached."
)
COULD_NOT_COUNT = (
    "Nothing here could count the pages in this PDF, so all of it is sent. To "
    "send part of it, photograph the pages you want instead."
)


def _keys(namespace):
    return (
        f"{namespace}_source_text",
        f"{namespace}_source_scan",
        f"{namespace}_source_from",
        f"{namespace}_source_upload",
        f"{namespace}_source_action",
    )


def _take_the_upload(upload, box, scan, came_from):
    """Put an upload into the box, or hold it as blocks if we cannot read it.

    Returns a message to show, or None. Runs once per file: the same upload is
    handed back on every rerun, and refilling the box each time would throw
    away any edit she has made to it.
    """
    stamp = f"{upload.name}:{upload.size}"
    if st.session_state.get(came_from) == stamp:
        return None

    try:
        material = read_upload(upload.name, upload.getvalue())
    except SourceMaterialError as refused:
        st.session_state[came_from] = stamp
        return str(refused)

    st.session_state[came_from] = stamp
    if material.is_held:
        st.session_state[box] = material.text
        st.session_state[scan] = None
    else:
        st.session_state[box] = ""
        st.session_state[scan] = material
    return None


def _her_choice_moved(before, offered):
    """What to say when what she picked is no longer one of the choices.

    ⚠️ Measured 2026-09-21: pick *use the source exactly* with her text pasted
    in, then upload a photograph of the page, and Streamlit finds the stored
    choice missing from the three a photograph allows, drops it, and falls back
    to the first on the list. Nothing crashes — she asked for one kind of sheet
    and is quietly getting another.

    The fallback is Streamlit's, so the sentence reads the offered list rather
    than naming a replacement of its own: a second opinion about which option
    she ends up on is a second thing to get wrong.
    """
    if not before or before in offered:
        return ""
    became = next(iter(offered.values()), "")
    return (
        f"'{WORKSHEET_ACTIONS.get(before, before)}' is not something this kind of sheet "
        f"can do with what you have supplied, so this has moved to '{became}'."
    )


def _is_a_pdf(filename):
    """Only a PDF has pages to choose between.

    ⚠️ A `.docx`, a `.txt`, a `.md` and a paste all land in the editable box,
    which she can already cut down by hand. A photograph is a single page, and
    the uploader takes one file at a time, so on every other route there is
    nothing to pick.
    """
    return str(filename).lower().endswith(".pdf")


def _the_pages_she_wants(total, first_key, last_key):
    """The range to send, or `None` when there is nothing to choose between.

    Defaults to the whole document. Narrowing is something she does on purpose
    — a picker that quietly sent only page 1 would be its own defect — and the
    origin above the sheet names whatever was sent either way.
    """
    if not total or total < 2:
        return None

    st.caption(PICK_THE_PAGES)
    first_column, last_column = st.columns(2)
    with first_column:
        first = st.number_input(
            "First page", min_value=1, max_value=total, value=1, step=1, key=first_key
        )
    with last_column:
        last = st.number_input(
            "Last page", min_value=1, max_value=total, value=total, step=1, key=last_key
        )
    return int(first), int(last)


def _take_the_pdf(upload, box, scan, came_from, namespace):
    """A PDF, cut to the pages she has reached — recut on every rerun.

    ⚠️ **Deliberately not stamped like `_take_the_upload`.** That stamp exists
    so a rerun cannot refill the box and throw away her edits; a *cut* made once
    at upload would ignore every change she made to the range afterwards, and
    the screen would say pages 4 to 6 while the whole chapter went. Measured
    2026-09-21 on an 18.8 MB, 120-page PDF: counting the pages takes 5 ms and
    cutting three of them 1 ms, so there is nothing worth caching here.

    The widget keys carry the file, so swapping a long PDF for a short one
    cannot leave a page number behind that the new file does not have.

    Returns a message to show, or None.
    """
    data = upload.getvalue()
    stamp = f"{upload.name}:{upload.size}"
    if st.session_state.get(came_from) != stamp:
        # A PDF leaves the box empty. Once per file, because she may type
        # alongside it and a rerun must not wipe what she typed.
        st.session_state[box] = ""
        st.session_state[came_from] = stamp

    total = pages_in(upload.name, data)
    if total is None:
        st.caption(COULD_NOT_COUNT)

    pages = _the_pages_she_wants(
        total, f"{namespace}_source_first_{stamp}", f"{namespace}_source_last_{stamp}"
    )

    try:
        st.session_state[scan] = read_upload(upload.name, data, pages=pages)
    except SourceMaterialError as refused:
        st.session_state[scan] = None
        return str(refused)
    return None


def source_panel(namespace, worksheet_type):
    """Her text and what to do with it, or `(None, None)` if she brought none.

    The panel renders for every worksheet type. A type that can take no source
    says so rather than disappearing — a control that vanishes reads as a bug,
    and the sentence names the sheets that would have worked.
    """
    box, scan, came_from, uploader, chosen = _keys(namespace)

    offered_at_all = actions_for(worksheet_type)
    with st.expander("\U0001F4C4 Use your own text", expanded=False):
        if not offered_at_all:
            st.caption(
                "This kind of sheet is a drill, so there is nowhere on it to put a text. "
                "Reading comprehension and problem solving can print one whole; the "
                "others can build tasks from one."
            )
            return None, None

        st.caption(SENT_AWAY)

        upload = st.file_uploader(
            "Upload a chapter, an extract or a page you have photographed",
            type=ACCEPTED_FILES,
            key=uploader,
            help="A Word file or plain text fills the box below. A PDF or a photo is "
            "sent to Claude as it is.",
        )
        if upload is not None:
            if _is_a_pdf(upload.name):
                unreadable = _take_the_pdf(upload, box, scan, came_from, namespace)
            else:
                unreadable = _take_the_upload(upload, box, scan, came_from)
            if unreadable:
                st.error(unreadable)
        elif st.session_state.get(scan) is not None:
            # ⚠️ She removed the file. A scan lives in session state rather
            # than in the box on screen, so without this it stayed attached and
            # the next sheet was still built from a document she had taken
            # away — with nothing on screen saying so.
            st.session_state[scan] = None
            st.session_state[came_from] = None

        held_scan = st.session_state.get(scan)
        if held_scan is not None:
            st.info(f"**{held_scan.origin}** — {NOT_HELD}")

        st.text_area(
            "Or paste the text itself",
            key=box,
            height=200,
            placeholder=(
                "When Mary Lennox was sent to Misselthwaite Manor to live with her "
                "uncle everybody said she was the most disagreeable-looking child "
                "ever seen."
            ),
        )

        typed = (st.session_state.get(box) or "").strip()
        material = None
        if typed:
            origin = "the text you pasted"
            if held_scan is None and st.session_state.get(came_from):
                origin = st.session_state[came_from].rsplit(":", 1)[0]
            try:
                material = source_from_text(typed, origin=origin)
            except SourceMaterialError as refused:
                st.error(str(refused))
                return None, None
            st.caption(f"{material.words:,} words. {HELD}")
        elif held_scan is not None:
            material = held_scan

        if material is None:
            return None, None

        offered = actions_for(worksheet_type, material)
        if not offered:
            st.error(
                "There is nothing this kind of sheet can do with a text like that."
            )
            return None, None

        moved = _her_choice_moved(st.session_state.get(chosen), offered)
        if moved:
            # Read before the radio is drawn: the widget is what drops the
            # stale value, so after it there is nothing left to notice.
            st.info(moved)

        action = st.radio(
            "What should it do with your text?",
            list(offered),
            format_func=lambda key: offered[key],
            key=chosen,
        )
        return material, action
