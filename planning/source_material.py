"""The text the teacher brings, and what each kind of worksheet can do with it.

She asked for this and called it game changing: upload a document or paste an
extract, then choose what to do with it — use it exactly, simplify it, make
questions from it, or build scaffolds around it.

**On reproducing her text.** `planning/anchors.py` records that publisher
content is never reproduced by this app. That rule is about the app shipping
White Rose, Boost or Lighting the Path material it does not own. This is the
opposite case and it does not reopen that decision: she supplies the extract,
for her own class, and the app neither stores it nor passes it on. Confirmed
with Graeme 2026-09-15.

**Held text is a property, not a flag.** Paste, Word and plain text give us the
words. A PDF or a photograph reaches Claude as an opaque block and we never see
what it says — so those routes can build from a source but can never reproduce
it word for word or check a name against it. `is_held` is derived from whether
there is any text, so there is no separate flag to forget to set.

⚠️ **PDFs and photographs are not transcribed by the model into held text, and
must not be.** A hallucinated name in a transcript would whitelist itself: the
name check's own haystack would vouch for the spoiler. That is silent, and it
fails in the loose direction. A real text-layer extractor is a defensible later
step; a model transcript never is.

**A drill has nowhere to put a text.** Refusing a times-tables sheet a source
is better than accepting one and ignoring it, because a refusal is visible and
can name the types that would have worked.
"""

import copy
import dataclasses
import io
import re

from pypdf import PdfReader, PdfWriter

from llm.prompts import list_worksheet_types
from planning.scheme_intake import UnreadableUploadError, blocks_for_upload

# About four thousand words — six printed pages, and comfortably more than the
# chapter extract or medium-term plan page this was built for. The limit exists
# because the reply has to carry the text back plus its questions and answers,
# and an output budget is a harder ceiling than an input one.
MAX_SOURCE_CHARS = 16_000

# ⚠️ **A page ceiling, read off the Anthropic API reference on 2026-09-21 for
# the model this app actually calls** (`claude-haiku-4-5-20251001`): a PDF
# document block may run to 600 pages, but only **100** on a 200K-context
# model, which this is. Our own 20 MB upload cap (`MAX_UPLOAD_BYTES`) bites
# before the API's 32 MB one, and a scanned page is an *image*, so a long scan
# exhausts the context window well before either. Refusing here names the
# number that fits; letting it go names nothing she can act on.
MAX_PAGES_AT_ONCE = 100


class SourceMaterialError(ValueError):
    """What she supplied cannot be used the way she asked for it."""


@dataclasses.dataclass(frozen=True)
class SourceMaterial:
    """Her material, and whether we hold the words or only a picture of them.

    ⚠️ Never name a field `source`. `UnitSpine.source`, `CoupledWorksheet.source`
    and `SchemeReading.source` all already mean *provenance* — "AI-drafted, check
    before teaching". One word with two meanings is how the wrong one ends up
    printed on a worksheet.
    """

    text: str = ""
    origin: str = ""
    blocks: tuple = ()

    @property
    def is_held(self):
        """True when we have her actual words, not just something to show Claude."""
        return bool(self.text.strip())

    @property
    def words(self):
        return len(self.text.split())


# --------------------------------------------------------------------------
# What each kind of worksheet can do with a text
# --------------------------------------------------------------------------

PRINTS_THE_SOURCE = "prints_the_source"
BUILDS_FROM_THE_SOURCE = "builds_from_the_source"
NOT_FROM_A_TEXT = "not_from_a_text"

# Measured live 2026-09-15 (`scripts/probe_source_types.py`): both of these
# reproduced a supplied text word for word and drew every question from it.
# ⚠️ `problem_solving` did so only when the source suited it — given a story
# extract it silently invented a shopping scenario instead. That is why an
# ignored source has to be caught rather than papered over.
SOURCE_CAPABILITY = {
    "reading_comprehension": PRINTS_THE_SOURCE,
    "problem_solving": PRINTS_THE_SOURCE,
    "cloze": BUILDS_FROM_THE_SOURCE,
    "word_bank": BUILDS_FROM_THE_SOURCE,
    "sentence_builder": BUILDS_FROM_THE_SOURCE,
    "matching": BUILDS_FROM_THE_SOURCE,
    "investigation": BUILDS_FROM_THE_SOURCE,
    "calculation_practice": NOT_FROM_A_TEXT,
    "fraction_practice": NOT_FROM_A_TEXT,
    "times_tables": NOT_FROM_A_TEXT,
}

# Her words, from the message that asked for this.
WORKSHEET_ACTIONS = {
    "use_exactly": "Use the source exactly",
    "adapt": "Simplify or adapt it",
    "questions_from": "Create questions from it",
    "scaffolds_around": "Create scaffolds around it",
}

_BUILD_ONLY = ("adapt", "questions_from", "scaffolds_around")

_ACTIONS_BY_CAPABILITY = {
    PRINTS_THE_SOURCE: tuple(WORKSHEET_ACTIONS),
    BUILDS_FROM_THE_SOURCE: _BUILD_ONLY,
    NOT_FROM_A_TEXT: (),
}


def _readable(worksheet_type):
    return worksheet_type.replace("_", " ")


def actions_for(worksheet_type, source_material=None):
    """What she may ask for, given this kind of sheet and what she supplied.

    Narrowed twice: by what the sheet can render, and then by whether we hold
    her words at all. A photograph cannot be reproduced word for word because
    nothing here knows what it says.
    """
    capability = SOURCE_CAPABILITY.get(worksheet_type)
    if capability is None:
        return {}

    allowed = _ACTIONS_BY_CAPABILITY[capability]
    if source_material is not None and not source_material.is_held:
        allowed = tuple(a for a in allowed if a != "use_exactly")
    return {action: WORKSHEET_ACTIONS[action] for action in allowed}


def check_the_pairing(worksheet_type, source_action):
    """Refuse a combination that cannot work, before a token is spent on it.

    Every refusal names what would have worked instead. A sheet that quietly
    ignored her text would be worse: she would print thirty copies before
    anyone noticed.
    """
    if source_action not in WORKSHEET_ACTIONS:
        raise SourceMaterialError(
            f"{source_action!r} is not something this can do with a text. "
            f"The choices are: {', '.join(WORKSHEET_ACTIONS.values())}."
        )

    capability = SOURCE_CAPABILITY.get(worksheet_type)
    if capability is NOT_FROM_A_TEXT:
        can_print = ", ".join(
            _readable(t) for t, c in SOURCE_CAPABILITY.items() if c is PRINTS_THE_SOURCE
        )
        raise SourceMaterialError(
            f"A {_readable(worksheet_type)} sheet is a drill, so there is nowhere on it "
            f"to put a text. To use your own text, choose {can_print}, or one of the "
            f"sheets that builds tasks from it."
        )

    if source_action not in _ACTIONS_BY_CAPABILITY.get(capability, ()):
        can_print = ", ".join(
            _readable(t) for t, c in SOURCE_CAPABILITY.items() if c is PRINTS_THE_SOURCE
        )
        others = ", ".join(WORKSHEET_ACTIONS[a] for a in _BUILD_ONLY)
        raise SourceMaterialError(
            f"A {_readable(worksheet_type)} sheet has nowhere to print your text whole, "
            f"so it cannot use it exactly. The sheets that can are: {can_print}. "
            f"On this one you can still: {others}."
        )


# --------------------------------------------------------------------------
# Getting her words in
# --------------------------------------------------------------------------


def as_paragraphs(text):
    """Paragraph breaks, in the one form the page can actually draw.

    ⚠️ `add_reading_passage` splits on a blank line and only on a blank line
    (`generators/components.py:835`), so a text with single newlines is drawn
    as one unbroken block — on the worksheet type that matters most.

    If she already uses blank lines, they are the breaks and single newlines
    inside a paragraph are soft wrapping. If there is not a blank line in the
    whole text, then every newline she typed is a break she meant.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if re.search(r"\n[ \t]*\n", text):
        pieces = re.split(r"\n[ \t]*\n+", text)
        pieces = [" ".join(piece.split()) for piece in pieces]
    else:
        pieces = [" ".join(line.split()) for line in text.split("\n")]
    return "\n\n".join(piece for piece in pieces if piece)


def source_from_text(text, origin):
    """Her words, checked and tidied into what the page can draw."""
    tidied = as_paragraphs(text or "")
    if not tidied:
        raise SourceMaterialError(
            "There is no text to work from. Paste an extract, or upload a document."
        )
    if len(tidied) > MAX_SOURCE_CHARS:
        over = len(tidied) - MAX_SOURCE_CHARS
        raise SourceMaterialError(
            f"That text is about {len(tidied.split()):,} words, which is roughly "
            f"{len(' '.join(tidied[:over].split()).split()):,} words more than fits on "
            f"one worksheet. Use the part of it you are teaching from."
        )
    return SourceMaterial(text=tidied, origin=origin)


def pages_in(filename, data):
    """How many pages a PDF has, or `None` when there is nothing to choose.

    `None` covers three cases on purpose — it is not a PDF, it is a PDF nothing
    here can open, or the bytes are damaged — because all three lead to the
    same place: no page picker, and the file travels exactly as it does today.

    ⚠️ **A scanner this cannot parse must not cost her the upload.** Her English
    material is scans, so refusing one here would refuse her main route on a
    fault that has nothing to do with the teaching. A guard that refuses correct
    work is worse than no guard. The panel says out loud that the pages could
    not be counted, so the wider file is visible rather than silent.
    """
    if not str(filename).lower().endswith(".pdf"):
        return None
    try:
        return len(PdfReader(io.BytesIO(data)).pages)
    except Exception:
        # Deliberately everything. pypdf raises its own errors for the damage it
        # recognises and whatever the standard library raises for the damage it
        # does not, and the answer is the same either way: no picker.
        return None


def cut_to_pages(data, first, last):
    """Just the pages she has reached, as a PDF, 1-based and inclusive.

    🚨 **This is her one hard constraint, made structural.** *"If I upload only
    part of a story/text, the lesson planner should only use what I've supplied
    and not assume or reveal later parts."* The pages outside the range are not
    described to the model, or withheld from it by instruction — they never
    leave this machine, so there is nothing to reveal.

    ⚠️ Not a prompt sentence, deliberately. An adversarial pass killed exactly
    that shape: her constraint defended by a line at the end of a request to a
    small fast model that has read the class novel.

    Raises:
        SourceMaterialError: a range this PDF does not have, one that runs
            backwards, or more pages than the model reads at once. Every one
            names the real page count, since that is the fact she is missing.
    """
    try:
        reader = PdfReader(io.BytesIO(data))
        total = len(reader.pages)
    except Exception as exc:
        raise SourceMaterialError(
            "Nothing here could open that PDF to take pages out of it. Upload it "
            "again, or photograph the pages you want instead."
        ) from exc

    if first > last:
        raise SourceMaterialError(
            f"Page {first} comes after page {last}, so that range runs backwards. "
            f"Put the first page you want first."
        )
    if first < 1 or last > total:
        raise SourceMaterialError(
            f"That PDF has {total} page{'s' if total != 1 else ''}, so there is no "
            f"page {last if last > total else first} in it. Choose a first and last "
            f"page between 1 and {total}."
        )

    wanted = last - first + 1
    if wanted > MAX_PAGES_AT_ONCE:
        raise SourceMaterialError(
            f"That is {wanted} pages. Claude reads at most {MAX_PAGES_AT_ONCE} pages "
            f"at a time, so choose a shorter run — pages {first} to "
            f"{first + MAX_PAGES_AT_ONCE - 1} would fit."
        )

    writer = PdfWriter()
    for page in reader.pages[first - 1:last]:
        writer.add_page(page)
    narrowed = io.BytesIO()
    writer.write(narrowed)
    return narrowed.getvalue()


def _named_pages(filename, first, last):
    """The file and the pages inside it, as she reads it above the sheet.

    ⚠️ Load-bearing rather than decoration. `_say_what_was_done_with_her_text`
    prints the origin above every sheet, so this is the only place the
    narrowing is visible to her — and a narrowing she cannot see is one she
    cannot trust or correct.
    """
    if first == last:
        return f"{filename}, page {first}"
    return f"{filename}, pages {first}–{last}"


def read_upload(filename, data, pages=None):
    """One uploaded file, as either her words or something to show Claude.

    Reuses `blocks_for_upload`, so how a Word document becomes text keeps
    exactly one definition — the document-order body walk in
    `planning/scheme_intake.py` that keeps table rows intact.

    Args:
        pages: `(first, last)` for a PDF she has cut down, 1-based and
            inclusive, or `None` for the whole file. **Cut first, then build
            the blocks**: the narrowing has to happen to the bytes, not to the
            instructions wrapped around them.
    """
    origin = filename
    if pages is not None:
        first, last = pages
        data = cut_to_pages(data, first, last)
        origin = _named_pages(filename, first, last)

    try:
        blocks = blocks_for_upload(filename, data)
    except UnreadableUploadError as exc:
        raise SourceMaterialError(str(exc)) from exc

    if blocks and blocks[0].get("type") == "text":
        return source_from_text(blocks[0]["text"], origin=origin)

    # A PDF or a photograph. Claude can read it; we cannot — and cutting it to
    # a page range does not change that, so the name check still says so.
    return SourceMaterial(text="", origin=origin, blocks=tuple(blocks))


def _matrix_is_complete():
    """Every type declared, and none invented. Asserted by the tests."""
    known = set(list_worksheet_types())
    return not (known - set(SOURCE_CAPABILITY)) and not (set(SOURCE_CAPABILITY) - known)


# --------------------------------------------------------------------------
# Her text on the page, and the reply that never used it
# --------------------------------------------------------------------------

# The one field on each sheet that prints prose whole. A sheet that builds
# tasks from a text has no such field, so there is nothing here to compare —
# see `with_the_source_in_place`.
WHERE_THE_PROSE_GOES = {
    "reading_comprehension": ("passage", "text"),
    "problem_solving": ("scenario", "text"),
}

# The three actions that ask for her text back on the page. `adapt` asks for a
# rewrite, so putting her original back would throw the work away.
REPRODUCES_HER_TEXT = ("use_exactly", "questions_from", "scaffolds_around")

# ⚠️ **Both measured, and neither is a matter of taste.**
# `scripts/measure_source_drift.py`, run 2026-09-16 over the four probe replies
# and 133 saved replies:
#
#   every reply written without her text in front of it   0.000 – 0.032
#   a Year 3 rewrite of the same extract, written by hand         0.570
#   every genuine reproduction, drift and all             0.972 – 1.000
#
# So the refusal line sits three times above the worst ignore ever measured and
# five times below the loosest plausible rewrite; the substitution line sits
# below every reproduction and above the rewrite. Between them is a band
# nothing has measured, and a reply that lands there is flagged, not judged.
TOO_FAR_FROM_HER_TEXT = 0.10
CLOSE_ENOUGH_TO_SUBSTITUTE = 0.90

# What to tell her when a sheet came back with none of her text in it. The
# fault is the pairing she made, not the number the comparison produced — she
# can act on "this text belongs on a different sheet" and cannot act on
# "similarity 0.015".
WHAT_TO_TRY_INSTEAD = {
    "problem_solving": (
        "A story or a passage of prose belongs on a reading comprehension sheet. A problem "
        "solving sheet needs a text with the numbers already in it — prices, amounts, "
        "measurements, times."
    ),
    "reading_comprehension": (
        "A reading comprehension sheet needs prose a child can read and answer questions "
        "about. A list of sums or a table of figures belongs on a problem solving sheet."
    ),
}


# Why each of the three unchecked cases is unchecked. ⚠️ They are not the same
# sentence on screen: a photograph genuinely cannot be read, while a
# fill-in-the-gaps sheet can be read perfectly well and simply is not the kind
# of sheet that prints a text whole. Telling her the second in the words of the
# first says the app failed when it did exactly the right thing.
CANNOT_READ_IT = (
    "Claude can read this, but nothing here can, so the sheet has not been checked "
    "against it."
)
DOES_NOT_PRINT_IT_WHOLE = (
    "This kind of sheet builds tasks from your text rather than printing it whole, so "
    "there is no passage to check against it."
)
NO_PASSAGE_CAME_BACK = "The sheet came back with no passage on it to check."


@dataclasses.dataclass(frozen=True)
class SourceOutcome:
    """The sheet, and what was actually done to it — never what was intended.

    ⚠️ `source_checked` is the one field that must never be optimistic.
    Everything downstream reads it to decide whether the screen may say her
    text was checked, and a guard that runs on an empty haystack and reports
    green is the failure this whole design is built against: every test passes,
    and she is told something was verified that nothing looked at.

    `why_not_checked` is the other half of that: "not checked" and "checked and
    fine" must never render as the same thing, so an unchecked outcome always
    carries the reason it was not.

    ⚠️ **`names_checked` is a second, independent axis and must not be folded
    into the first.** `source_checked` asks whether her passage was compared
    with what got printed, which only two kinds of sheet do at all.
    `names_checked` asks whether the names on the sheet were compared with her
    text, which every sheet can do as long as we hold her words. A cloze sheet
    is `source_checked=False` and `names_checked=True`; a photographed chapter
    is the other way round on both. Collapsing them loses the name check on
    five of the seven types that take a source. See `planning/source_names.py`.
    """

    content: dict
    source_checked: bool = False
    substituted: bool = False
    similarity: float = 0.0
    origin: str = ""
    flags: tuple = ()
    why_not_checked: str = ""
    names_checked: bool = False
    why_names_not_checked: str = ""


# The characters a model changes without changing a word. ⚠️ Curly quotes are
# the common case by a mile: tidying `can't` into `can’t` is the single most
# ordinary thing that happens to a reproduced passage, and before these were
# normalised it scored **0.000** — a pure typography drift, refused.
_TYPOGRAPHY = {
    "‘": "'", "’": "'", "‛": "'", "ʼ": "'",
    "“": '"', "”": '"',
    "–": "-", "—": "-", "−": "-",
    "…": "...", " ": " ",
}


def _words(text):
    """Her words, whatever alphabet they are written in.

    ⚠️ `\\w` rather than `[a-z]`, and it is load-bearing. Matching only Latin
    letters dropped every accented character and every non-Latin script, which
    fails in **both** directions at once: measured 2026-09-18, two entirely
    unrelated Chinese passages scored **1.000** because nothing was left of
    either but their numbering, and an accented French line compared as
    fragments rather than as words.
    """
    text = str(text).lower()
    for odd, plain in _TYPOGRAPHY.items():
        text = text.replace(odd, plain)
    return re.findall(r"[\w']+", text)


def _word_pairs(text):
    words = _words(text)
    return set(zip(words, words[1:]))


def how_much_of_it_is_hers(source_text, printed):
    """What share of the printed passage's word pairs came out of her text.

    **Pairs, not words, and measured against the printed side.** Two unrelated
    pieces of English share most of their common words, so counting words alone
    puts an invented passage at 13% rather than near zero — measured. Counting
    pairs puts it at 1.5%. And dividing by the printed side rather than hers
    means a reproduction that stops halfway still scores 1.0, because every
    pair on the page did come from her: a short reproduction is drift to be
    corrected, not a different text.

    ⚠️ One definition, deliberately. `scripts/measure_source_drift.py` imports
    this rather than carrying its own copy, so the thresholds above can never
    come to be set by a measurement of a different thing.
    """
    printed_pairs = _word_pairs(printed)
    if printed_pairs:
        return len(printed_pairs & _word_pairs(source_text)) / len(printed_pairs)

    # Too short to contain a single pair. ⚠️ Returning 0.0 here refused the
    # shortest possible *perfect* reproduction — measured 2026-09-18: "Go!"
    # reproduced as "Go!" scored 0.000 and was refused. Fall back to the words
    # themselves; a one-word passage has no phrasing to compare, and the words
    # are all the evidence that exists.
    printed_words = set(_words(printed))
    if not printed_words:
        return 0.0
    return len(printed_words & set(_words(source_text))) / len(printed_words)


def vocabulary_not_in_the_passage(content, printed):
    """The words in the box that are not on the page beside it.

    The template's rules 3 and 12 made checkable — vocabulary comes from the
    passage, and a vocabulary question asks about a word that appears in it.
    Whole words and case-insensitive: `SOUR` and `sour` are not a difference a
    reader would see, and neither is a word sitting next to a comma.
    """
    printed_words = set(_words(printed))
    absent = []
    for entry in content.get("vocabulary") or []:
        word = entry.get("word") if isinstance(entry, dict) else entry
        if not word:
            continue
        if not all(_is_on_the_page(part, printed_words) for part in _words(word)):
            absent.append(str(word))
    return tuple(absent)


def _is_on_the_page(word, printed_words):
    """Whole words, and the ends of whole words — but never the middles.

    ⚠️ The inflection case is the one that matters and the one that nearly got
    this wrong in both directions. A box listing `servant` beside a passage
    that says `servants` is a word a child can find, and refusing that sheet
    would be refusing correct work. A box listing `ant` beside the same passage
    is not, and a plain substring test would have accepted it — which is how a
    check like this quietly stops meaning anything.

    So: an exact word, or a word on the page that *starts with* it, and only
    when there is enough of it for that to say something.
    """
    if word in printed_words:
        return True
    return len(word) >= 4 and any(page.startswith(word) for page in printed_words)


def _vocabulary_flags(content, printed):
    """Said out loud, not refused — see `vocabulary_not_in_the_passage`."""
    stray = vocabulary_not_in_the_passage(content, printed)
    if not stray:
        return ()
    return (
        f"The vocabulary box lists {', '.join(stray)}, which "
        f"{'do' if len(stray) > 1 else 'does'} not appear in the passage on this sheet. "
        f"The children will not be able to find {'them' if len(stray) > 1 else 'it'}.",
    )


def with_the_source_in_place(content, worksheet_type, source_material, source_action):
    """Her text back on the page, or a refusal that names what went wrong.

    Called unconditionally in `app.py` — without a source it does nothing, so
    there is no branch anybody can forget to write.

    Measured live on 2026-09-15: given a story extract, a maths word-problem
    sheet invented a space-shopping scenario and used none of the source, with
    no error of any kind. Substituting her story into that reply would have
    printed it above eight questions about oxygen tanks. So this is a guard
    that sometimes corrects, not a substitution that sometimes checks.

    ⚠️ No argument has a default. A call site that forgets the source is a
    `TypeError` at once rather than a sheet that quietly checks nothing.
    """
    if source_material is None:
        return SourceOutcome(content=content)

    # A PDF or a photograph: Claude can read it, we cannot. There is no
    # haystack, so there is nothing to claim.
    if not source_material.is_held:
        return SourceOutcome(
            content=content,
            origin=source_material.origin,
            why_not_checked=CANNOT_READ_IT,
        )

    # A sheet that builds tasks from a text prints mostly its own instructions,
    # so comparing it to her extract would refuse correct work — and nothing
    # has measured what a correct one scores.
    where = WHERE_THE_PROSE_GOES.get(worksheet_type)
    if where is None:
        return SourceOutcome(
            content=content,
            origin=source_material.origin,
            why_not_checked=DOES_NOT_PRINT_IT_WHOLE,
        )

    section, field = where
    printed = str((content.get(section) or {}).get(field) or "")
    if not printed.strip():
        return SourceOutcome(
            content=content,
            origin=source_material.origin,
            why_not_checked=NO_PASSAGE_CAME_BACK,
        )

    closeness = how_much_of_it_is_hers(source_material.text, printed)

    # 🚨 **Only the actions that ask for her text back may refuse.** She asked
    # for `adapt` to rewrite the text, and a thorough rewrite shares almost
    # nothing with the original: measured 2026-09-18, "The exhausted infant
    # slumbered peacefully." rewritten as "The tired baby slept well." — a
    # correct Year 3 simplification — scored 0.000 and was refused. Nothing has
    # ever measured what a real adaptation scores, so there is no threshold to
    # refuse one on, and a guard that refuses correct work is worse than no
    # guard at all. An adaptation is flagged instead, below.
    if closeness < TOO_FAR_FROM_HER_TEXT and source_action in REPRODUCES_HER_TEXT:
        instead = WHAT_TO_TRY_INSTEAD.get(worksheet_type) or (
            "The sheets that can print a text whole are: "
            + ", ".join(
                _readable(t) for t, c in SOURCE_CAPABILITY.items() if c is PRINTS_THE_SOURCE
            )
            + "."
        )
        raise SourceMaterialError(
            f"A {_readable(worksheet_type)} sheet could not build from the text you gave it. "
            f"What came back is not about your text at all, so it is not the sheet you asked "
            f"for. {instead}"
        )

    if source_action in REPRODUCES_HER_TEXT and closeness >= CLOSE_ENOUGH_TO_SUBSTITUTE:
        if printed == source_material.text:
            # Nothing was changed, so a word off the page is the model's own
            # mistake rather than one this app introduced. She is told and
            # keeps the sheet — throwing away correct work over a word form
            # like `slumbering` for `slumbered` is the worse failure.
            return SourceOutcome(
                content=content,
                source_checked=True,
                similarity=closeness,
                origin=source_material.origin,
                flags=_vocabulary_flags(content, printed),
            )
        corrected = copy.deepcopy(content)
        corrected[section][field] = source_material.text

        # 🚨 Her text is now the passage, so the vocabulary box has to be about
        # *her* text. A box still describing the passage we just deleted is the
        # incoherence an adversarial pass predicted before this was built, and
        # it is refused rather than flagged **only here** — because this is the
        # one path where the app itself caused it.
        stray = vocabulary_not_in_the_passage(corrected, source_material.text)
        if stray:
            raise SourceMaterialError(
                f"The vocabulary box on this sheet is about a different passage: "
                f"{', '.join(stray)} {'do' if len(stray) > 1 else 'does'} not appear in "
                f"your text. The words have to come from your text, because that is what "
                f"the children will be reading. Try generating it again."
            )

        return SourceOutcome(
            content=corrected,
            source_checked=True,
            substituted=True,
            similarity=closeness,
            origin=source_material.origin,
        )

    # ⚠️ Flagged on **every** action, not only the reproducing ones. The middle
    # of the measured gap is not knowledge: nothing here can tell a thorough
    # rewrite from a sheet that used none of her text. Saying nothing on the
    # one action that cannot be measured is how an unrelated passage reaches
    # her in silence.
    if source_action in REPRODUCES_HER_TEXT:
        flags = (
            "Some of this passage is not from the text you supplied. It has been left as it "
            "came back rather than replaced — read it before you print it.",
        )
    else:
        flags = (
            "This has been rewritten, so it is meant to read differently from your text. "
            "Nothing here can tell a good rewrite from a sheet that ignored your text, so "
            "read it before you print it.",
        )
    return SourceOutcome(
        content=content,
        source_checked=True,
        similarity=closeness,
        origin=source_material.origin,
        flags=flags,
    )


# --------------------------------------------------------------------------
# Getting her text there, and getting it back
# --------------------------------------------------------------------------

# ⚠️ **An output ceiling, and a hard one.** The reply has to carry her text back
# *as well as* its questions, its model answers and its vocabulary box, and
# `_reject_incomplete` refuses a truncated reply rather than rendering it short.
#
# Checked against the Anthropic API reference 2026-09-18 for the model this app
# actually calls (`claude-haiku-4-5-20251001`): its ceiling is 64,000 output
# tokens, but a reply above roughly 16,000 has to be **streamed** or the server
# closes the connection — which is exactly what happened here on 2026-09-02.
# So 16,384 is the line, not the model's ceiling, and `app.py` streams whenever
# a source is present.
#
# The arithmetic below is deliberately generous: about three characters per
# token rather than the usual four, because names and punctuation cost more
# than prose. At `MAX_SOURCE_CHARS` the longest source we accept needs roughly
# 5,300 tokens on top of the base budget, which leaves room under the line —
# so the length limit and this ceiling cannot disagree.
MAX_REPLY_TOKENS = 16_384
_CHARS_PER_TOKEN = 3


def room_for_the_source(base_tokens, worksheet_type, source_material):
    """The output budget, with room for her text to come back inside it.

    Only the sheets that print a text whole need it: a sheet that builds tasks
    takes what it needs and reproduces nothing.

    ⚠️ A scan gets no extra room, because nothing here knows how long it is.
    That fails loudly rather than quietly — a reply that runs out of budget is
    refused as truncated, not rendered short.
    """
    if source_material is None or not source_material.is_held:
        return base_tokens
    if SOURCE_CAPABILITY.get(worksheet_type) is not PRINTS_THE_SOURCE:
        return base_tokens
    room = base_tokens + -(-len(source_material.text) // _CHARS_PER_TOKEN)
    return min(room, MAX_REPLY_TOKENS)


def request_with(prompt, source_material):
    """The prompt, or the prompt with her document in front of it.

    Held text is already inside the prompt — `llm/prompts.py` puts it between
    the markers. A PDF or a photograph has no text to put there, so it travels
    as itself, ahead of the instructions: `llm/client.py` documents that
    ordering, and `planning/scheme_intake.py` builds the blocks.
    """
    if source_material is None or source_material.is_held or not source_material.blocks:
        return prompt
    return [*source_material.blocks, {"type": "text", "text": prompt}]
