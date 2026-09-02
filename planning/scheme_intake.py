"""Reading the plan the teacher has to follow, without her retyping it.

Boost governs science, history, geography and computing at St Anthony's. Its
long- and medium-term plans have to be followed, and they are too thin to teach
from. So this module treats the scheme as a *constraint*, not as teaching:

  * **Kept** -- what the unit covers, in what order, under what title, and any
    assessment point the subject leader set. She is accountable for those, and
    quietly dropping one is what causes trouble.
  * **Rebuilt elsewhere** -- the objectives, success criteria, vocabulary and
    the lesson itself.

Three ways in, because a photocopy in a folder is the realistic case:

  * paste the text,
  * upload the Word or PDF that was circulated,
  * photograph the printed page.

PDFs and photographs are handed to Claude as document and image blocks rather
than run through a text extractor. A scanned or photographed plan has no text
layer, so a parser returns nothing and reports it as an empty document -- which
looks exactly like a plan with no coverage in it.

Publisher content is never reproduced by this app. She supplies the page; we
extract the coverage statements and unit title, which are largely National
Curriculum wording anyway, and build the teaching around them.
"""

import base64
import os
from dataclasses import dataclass, field

# Anthropic caps a request at 32 MB including the base64 expansion, which is
# ~4/3 of the raw bytes. 20 MB of source leaves comfortable room for the prompt
# and is far above any medium-term plan; the limit exists to fail clearly on a
# wrong file rather than to be tight.
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

_IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
_TEXT_TYPES = {".txt", ".md"}

# Words that describe what the *teacher* or the *unit* does. A coverage line
# built only from these says nothing about what a child would be able to do,
# which is what makes it unteachable as written.
_TEACHER_FACING = (
    "children know",
    "children will know",
    "pupils know",
    "pupils will know",
    "children learn",
    "pupils learn",
    "understand that",
    "be aware",
    "introduce",
    "cover",
)

# Verbs a child can actually be observed doing. Not exhaustive, and not meant
# to be: this is a hint for the teacher's eye, not a grammar checker.
_CHILD_VERBS = (
    "compare", "group", "sort", "classify", "describe", "explain", "identify",
    "name", "measure", "record", "observe", "predict", "test", "order",
    "sequence", "justify", "evaluate", "create", "build", "draw", "write",
    "calculate", "solve", "recognise", "recognize", "use", "apply", "select",
)


class SchemePlanError(ValueError):
    """The extracted plan is not usable as a coverage record."""


class UnreadableUploadError(ValueError):
    """The uploaded file cannot be given to the model as-is."""


@dataclass(frozen=True)
class SchemePlan:
    """What the school's scheme says this unit must cover.

    The coverage list is the part she is accountable for; everything the app
    generates is checked back against it.
    """

    unit_title: str
    coverage: list
    assessment: list = field(default_factory=list)
    activities: list = field(default_factory=list)


def blocks_for_upload(filename, data):
    """Turn an uploaded file into content blocks for the Anthropic API.

    PDFs become `document` blocks and photographs become `image` blocks, so
    Claude reads the page itself. Plain text is passed through as text.

    The caller places these *before* the instruction text in the message --
    documents and images ahead of the prompt is the documented ordering, and
    the model attends to them better that way.

    Raises:
        UnreadableUploadError: empty, too large, or a type we do not accept.
            Named explicitly so the screen can say which file and why, rather
            than failing somewhere downstream with an empty extraction.
    """
    if not data:
        raise UnreadableUploadError(f"{filename} is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise UnreadableUploadError(
            f"{filename} is too large ({len(data) // (1024 * 1024)} MB). "
            f"The limit is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
        )

    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        return [{
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                # b64encode returns one unbroken line; the API rejects wrapped
                # base64, so nothing here may reformat it.
                "data": base64.b64encode(data).decode("ascii"),
            },
        }]

    if ext in _IMAGE_TYPES:
        return [{
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": _IMAGE_TYPES[ext],
                "data": base64.b64encode(data).decode("ascii"),
            },
        }]

    if ext in _TEXT_TYPES:
        return [{"type": "text", "text": data.decode("utf-8", errors="replace")}]

    raise UnreadableUploadError(
        f"Cannot read a {ext.lstrip('.') or 'file'} file. "
        "Paste the text, or upload a PDF, a photograph, or a plain text file."
    )


def build_extraction_prompt(scheme, subject, year_group):
    """Ask for the scheme's coverage, and nothing beyond it.

    Two instructions carry the weight. **Do not invent** -- an added coverage
    line looks identical to a real one on the screen and would be defended to a
    subject leader as the school's own plan. And **flag rather than fix** -- a
    vague statement is reported as vague, not quietly rewritten into something
    teachable, because the rewrite is a judgement the teacher should see.
    """
    return (
        f"You are reading a {year_group} {subject} unit from the {scheme} scheme "
        f"of work, exactly as a teacher received it.\n\n"
        "Extract only what the document actually says. Do not invent coverage, "
        "do not complete a partial list, and do not improve the wording. If the "
        "document is unclear or partly unreadable, return what you can read and "
        "leave the rest out.\n\n"
        "Return JSON only, with no commentary, in this shape:\n"
        "{\n"
        '  "unit_title": "the unit\'s title as written",\n'
        '  "coverage": ["each thing the unit says it covers, as written"],\n'
        '  "assessment": ["any assessment statement, as written"],\n'
        '  "activities": ["any suggested activity, as written"],\n'
        '  "vague": ["any coverage entry that is a statement rather than '
        'something a child could be observed doing"]\n'
        "}\n\n"
        "Copy coverage wording across verbatim. Flag a vague entry in the "
        "'vague' list; do not rewrite it in 'coverage'."
    )


def validate_scheme_plan(payload):
    """Check an extracted plan before anything is built on it.

    Deliberately strict about coverage: everything downstream -- the unit
    spine, the coverage map, the gap list -- treats this as the record of what
    the school agreed to teach. An empty or malformed coverage list must fail
    here, loudly, rather than produce a unit that quietly covers nothing.
    """
    if not isinstance(payload, dict):
        raise SchemePlanError("The extracted plan is not an object.")

    title = str(payload.get("unit_title", "")).strip()
    if not title:
        raise SchemePlanError("The plan has no unit title.")

    raw_coverage = payload.get("coverage")
    if not isinstance(raw_coverage, list) or not raw_coverage:
        raise SchemePlanError("The plan lists no coverage.")

    coverage = []
    for item in raw_coverage:
        if not isinstance(item, str):
            raise SchemePlanError(
                f"Coverage entries must be plain text; got {type(item).__name__}."
            )
        if item.strip():
            coverage.append(item.strip())

    # Blanks are dropped quietly, but dropping every entry is not the same
    # thing as a unit that covers nothing -- say so rather than returning an
    # empty plan that reads as valid.
    if not coverage:
        raise SchemePlanError("Every coverage entry was blank.")

    return SchemePlan(
        unit_title=title,
        coverage=coverage,
        assessment=_clean_list(payload.get("assessment")),
        activities=_clean_list(payload.get("activities")),
    )


def _clean_list(value):
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def vague_coverage_items(coverage):
    """Coverage entries that are not teachable as written.

    A hint for the teacher's eye, never a verdict: nothing in this module
    rejects a unit for being vague, and the reason is always shown so she can
    disagree with it. Returns `(item, reason)` pairs.
    """
    flagged = []
    for item in coverage:
        text = item.strip().lower()
        if not text:
            continue

        if any(text.startswith(p) or f" {p}" in text for p in _TEACHER_FACING):
            flagged.append((
                item,
                "Describes what children will know rather than what they will do, "
                "so there is nothing to observe or assess.",
            ))
            continue

        if not any(v in text for v in _CHILD_VERBS):
            flagged.append((
                item,
                "Names a topic but no action, so it cannot be taught or assessed "
                "as written.",
            ))
    return flagged
