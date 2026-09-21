"""Names on the sheet that are not in the text she supplied.

Her one hard constraint, in her words: *"if I upload only part of a story/text,
the lesson planner should only use what I've supplied and not assume or reveal
later parts."*

🚨 **No deterministic check can prove a text is spoiler-free, and this one does
not pretend to.** *"Later, Alice discovers the key belongs to her father"* uses
only names the extract already contains, and nothing here can see the spoiler
in it. What is testable is narrower and still worth having: **content that
introduces a named entity absent from her text.** `THE_HONEST_LABEL` says
exactly that much on screen, pass or fail, and never more.

⚠️ **Report-only.** Nothing here refuses a sheet. A refusal on a false positive
is the teacher told her correct worksheet is wrong — invisible on a green suite
and visible to her.

**Why the detector is structural rather than a word list.** A list of the words
that open an instruction — *Later, Challenge, Extension, Task, Write, Draw,
Think, Why, Remember* — can never know the next word somebody writes. So the
rule is about position instead: **a single capitalised word at the start of a
segment is a candidate only if the same word also appears mid-sentence
somewhere else in the reply.** Spoilers live inside questions; false positives
live at the front of instructions. That keeps *Alice* in "What do you think
Alice does next?" and drops all nine of the above for free.

⚠️ **Two matchers in `planning/worksheet.py` must not be used here**, and both
would fail in the loose direction, which is the worse one:

- `_says_the_same` walks word stretches at arbitrary distance, so
  `Ben Weatherstaff` would "match" *"…bent down… the weather stayed fair…"* and
  the guard's own haystack would vouch for the spoiler.
- `_segments_of` deletes bracketed choices as gaps — and a developing-level
  cloze sheet **prints** those, so a name inside one is on the page.

`_normalise` is imported rather than copied, because the one thing worse than
two matchers is two definitions of one matcher.

## What the corpus measured, 2026-09-20

`scripts/sweep_unseen_names.py`, no API calls, over all 133 saved replies. 🚨
**It cannot say anything about the detection rate** — not one saved reply was
generated from a teacher's source, so there is no case in it where a name
*should* be caught. It is a false-refusal census and nothing else, and it is
blind to `reading_comprehension` and `problem_solving`, which have **zero**
samples and are the two types this whole feature rests on.

On the 54 worksheet replies — the only surface this phase renders on — the
detector raised **72 candidates, 40 of them unsupported, across 23 of 54
replies**, down from 1,183 before the census was read. Every reduction was a
structural rule in the list above, not an entry on a word list. What remains is
mostly what the check is *for*: `Planet Terra`, `Planet Ancient Rock`,
`Asteroid X` and `Moon` are proper nouns the model invented, and on a sheet
built from her chapter they are exactly the finding she needs.

⚠️ **Two known false positives are left standing, deliberately.** A title-cased
phrase naming a section of the sheet (*"Hardness Challenge section"*) survives
because the lower-case noun after it breaks the heading veto; and an adjective
in a slash-separated column (*"Rock name / Rough / Smooth"*) survives because a
slash is **not** treated as a boundary. Making the slash a boundary was tried
and rejected: it costs the second half of `[Ben/Dickon]` on a cloze sheet,
which is a false *pass*, and a false pass is the worse of the two. Both live on
the lesson surface, which nothing checks until Phase 5.
"""

import dataclasses
import re

from generators.styles import THEMES
from planning.source_material import _TYPOGRAPHY
from planning.worksheet import _normalise

# What she is told when the check ran. Word for word from the plan: the first
# sentence is the claim, the second is the limit of it, and the third is the
# standing rule that output is labelled AI-drafted and never verified.
THE_HONEST_LABEL = (
    "**Only what you supplied is used.** Every name on this sheet is checked "
    "against your text. **This is not a promise the sheet is spoiler-free** — a "
    "question can give away something later using only words your text already "
    "contains, and no check can see that. AI-drafted — check before teaching."
)

# ⚠️ And what she is told when it did not run. These two must never read the
# same: "checked and clean" and "nothing looked at it" are the pair this whole
# design exists to keep apart.
NAMES_CANNOT_BE_CHECKED = (
    "The names on this sheet have not been checked against your document, "
    "because nothing here can read it — only Claude can. A PDF or a photograph "
    "reaches Claude as a picture of a page."
)


# --------------------------------------------------------------------------
# Reading the reply
# --------------------------------------------------------------------------

# Where a capital letter stops meaning anything: a new line, the end of a
# sentence, and the start of a quotation. ⚠️ The third is not decoration — a
# word after an opening quote is capitalised by exactly the same convention as
# a word after a full stop, so without it *"Later the robin came back."* reads
# as mid-sentence and the capital is taken for a name.
_SENTENCE_ENDS = ".!?:;"

# Two more that do a full stop's job on a worksheet, both measured over the
# corpus 2026-09-20: a spaced dash between the halves of a heading
# (*"Hook - What is a rock?"*, *"Plenary - Can you explain it?"*) and the pipe
# between two cells of a table (*"Rock name | Scratches?"*). Without them the
# word after the mark reads as mid-sentence, which is the position that makes a
# capital mean something — `What`, `Can` and `Scratches` were candidates in
# eleven, seven and several replies respectively.
_ALSO_A_BOUNDARY = "|"

# A full stop that is not the end of anything. Without these, `Mrs. Medlock`
# puts `Medlock` at the start of a segment, where it needs corroborating before
# it counts — a name quietly lost, which is the loose direction.
_ABBREVIATIONS = frozenset(
    {"mr", "mrs", "ms", "dr", "prof", "rev", "st", "sgt", "no", "vs", "etc", "fig"}
)

# An honorific is a closed class and names nobody — the same argument as
# `_NEVER_A_NAME` below. ⚠️ Found by running a realistic sheet rather than by a
# test: `Mrs. Medlock` arrived as **two** findings, because the full stop broke
# the run, and `Mrs` on its own would then fire on any extract that happens not
# to use it. Both halves are fixed — the stop no longer breaks the run, and the
# honorific is supported, so `Mrs. Medlock` beside a text naming `Medlock` is
# not a new name.
_HONORIFICS = ("Mr", "Mrs", "Ms", "Miss", "Dr", "Prof", "Rev", "Sir", "Lady", "Lord")

# The words title case leaves in lower case: articles, coordinating
# conjunctions and prepositions. Used only to recognise a heading, never to
# decide whether something is a name.
#
# ⚠️ **Verbs are not on this list and must not be**, however short they are.
# Title case capitalises them — *"Who Is Alice?"* — so a lower-case `is` is
# evidence the segment is a sentence rather than a heading. With `is` treated as
# minor, *"Who is Alice?"* was read as a title and vetoed whole: a comprehension
# question about a name nobody supplied, silently passed. Caught 2026-09-20 by
# the test that asserts a finding reaches the flags.
_MINOR_WORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "nor", "but", "so", "yet", "as", "at",
        "by", "for", "from", "in", "into", "of", "off", "on", "onto", "out",
        "over", "per", "to", "up", "upon", "with", "within", "vs",
    }
)

# 🔑 **The one list in here that is allowed to be a list, because it is a
# closed class.** The plan is right that the words which open an instruction
# cannot be enumerated — somebody writes a new one tomorrow. English function
# words are the opposite: articles, pronouns, auxiliaries, interrogatives,
# conjunctions, prepositions, demonstratives and quantifiers are a fixed set
# that has not grown in centuries, and not one of them names anything.
#
# ⚠️ Measured: after every structural fix above, this was the whole remaining
# tail of the census — `Is` in seven replies, `The` in six, `So` in five, plus
# `What`, `We`, `It`, `Did`, `More`, `Because`. Each fired because the same
# word is used mid-sentence somewhere on the sheet — *"What I observe by
# touching (Is it hard or soft?"* — which is corroboration the rule was built
# to trust and cannot tell apart from a name.
_NEVER_A_NAME = _MINOR_WORDS | frozenset(
    {
        # pronouns and determiners
        "i", "me", "my", "mine", "myself", "we", "us", "our", "ours", "you",
        "your", "yours", "he", "him", "his", "she", "her", "hers", "it", "its",
        "they", "them", "their", "theirs", "this", "that", "these", "those",
        "who", "whom", "whose", "which", "what", "whatever", "whoever",
        # auxiliaries and the copula
        "am", "is", "are", "was", "were", "be", "been", "being", "do", "does",
        "did", "done", "have", "has", "had", "can", "could", "shall", "should",
        "will", "would", "may", "might", "must", "let",
        # interrogatives, conjunctions and the rest of the closed class
        "when", "where", "why", "how", "if", "then", "than", "because",
        "while", "until", "unless", "although", "though", "since", "before",
        "after", "not", "no", "yes", "all", "any", "both", "each", "every",
        "few", "many", "more", "most", "much", "some", "such", "there", "here",
        "now", "also", "just", "only", "very", "too", "again", "once",
    }
)

# 🔑 **Short on purpose, and everything else is derived.** The rule that buys
# safety here is positional, not lexical; this list is only for the handful of
# words a worksheet prints as content rather than as prose, where position
# cannot help. Themes come from `THEMES` and subjects from the curriculum
# rather than being copied here, so neither can start flagging sheets when one
# is added.
#
# ⚠️ **These two lines are a priori and the corpus did not ask for them** — one
# Science unit prints no dates, so nothing here measured a day or a month. They
# are closed sets that plainly name nothing, and they are recorded as a guess
# rather than as a finding. Everything the census *did* ask for became a
# structural rule above instead of an entry here.
ALWAYS_ALLOWED = (
    "True", "False", "Yes", "No",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December",
)


def _plain_typography(text):
    """The characters a model changes without changing a word.

    One definition with `planning/source_material.py`, which is where the
    measurement that justifies it lives: a reproduction with its apostrophes
    curled scored **0.000** before these were normalised.
    """
    for odd, plain in _TYPOGRAPHY.items():
        text = text.replace(odd, plain)
    return text


def _words_for_matching(text):
    """`_normalise`, plus the one step it does not do: punctuation to a space.

    Whole words, case-insensitive. Single characters are dropped: `Mary's`
    leaves a bare `s` behind, and a haystack that happens to contain no
    apostrophe at all would otherwise refuse her own character's name.
    """
    plain = re.sub(r"[^\w\s]|_", " ", _normalise(_plain_typography(str(text))))
    return frozenset(word for word in plain.split() if len(word) > 1)


def _texts_in(value):
    """Every string in the reply, wherever it is nested.

    Deliberately the whole reply rather than `RENDERED_KEYS`. A name in a model
    answer is a name she reads out to the class, and a filter here could only
    ever make the check see less than she does.
    """
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _texts_in(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _texts_in(item)


def _word_before(text, at):
    end = at
    while end and not text[end - 1].isalnum():
        end -= 1
    start = end
    while start and text[start - 1].isalnum():
        start -= 1
    return text[start:end].lower()


def _ends_a_sentence(text, at):
    after = text[at + 1:at + 2]
    if after and not after.isspace() and after not in "\"'":
        # `3.5`, `10:30`, the first stop of `U.K.` — punctuation inside a word.
        return False
    return not (text[at] == "." and _word_before(text, at) in _ABBREVIATIONS)


def _opens_a_quotation(text, at):
    before = text[at - 1] if at else " "
    after = text[at + 1:at + 2]
    return (before.isspace() or before in "([") and bool(after) and after.isalnum()


def _separates_clauses(text, at):
    """A dash with a space on both sides, doing the job of a full stop."""
    return (
        text[at] == "-"
        and at
        and text[at - 1].isspace()
        and text[at + 1:at + 2].isspace()
    )


def _segments(text):
    """The reply cut where a capital letter stops carrying information."""
    text = _plain_typography(str(text))
    segments, start = [], 0
    for at, character in enumerate(text):
        if character == "\n" or character in _ALSO_A_BOUNDARY:
            cut = True
        elif character in _SENTENCE_ENDS:
            cut = _ends_a_sentence(text, at)
        elif character in "\"'":
            cut = _opens_a_quotation(text, at)
        elif character == "-":
            cut = _separates_clauses(text, at)
        else:
            cut = False
        if cut:
            segments.append(text[start:at + 1])
            start = at + 1
    segments.append(text[start:])
    return [segment for segment in segments if segment.strip()]


def _tokens(segment):
    """`(word, start, end)` for every word, counted character by character.

    ⚠️ Per character rather than `[a-z]`. Matching Latin letters only dropped
    every accented character and every non-Latin script once already, and it
    failed in both directions at the same time.
    """
    tokens, start = [], None
    for at, character in enumerate(segment):
        if character.isalnum() or (character == "'" and start is not None):
            if start is None:
                start = at
        elif start is not None:
            tokens.append((segment[start:at], start, at))
            start = None
    if start is not None:
        tokens.append((segment[start:], start, len(segment)))
    return tokens


def _is_shouted(token):
    """Every letter in capitals — emphasis, or an abbreviation. Never evidence.

    ⚠️ **Measured, and it is the largest single hole the corpus found**: `SEND`
    in 56 of the 133 saved replies and `EAL` in 53, plus `HARD`, `SOFT`, `NOT`,
    `ONE`, `ARE`. A worksheet shouts for emphasis and a lesson plan is full of
    abbreviations, and in both a capital says nothing about whether the word
    names anything.

    ⚠️ This is the plan's ALL-CAPS *segment* veto applied one level down, and it
    **replaces** it rather than sitting beside it: a rule that reaches a shouted
    word inside ordinary prose already reaches every word of a shouted line, so
    keeping both would leave the outer one untestable — a guard whose mutation
    goes quiet is a guard nobody is checking any more.
    """
    letters = [character for character in token if character.isalpha()]
    return bool(letters) and all(character.isupper() for character in letters)


def _is_capitalised(token):
    """A capital that could mean this word names something.

    ⚠️ **`I` was excluded here too and the positive control proved it dead.**
    English capitalises the first person unconditionally, so `If I`, `Now I`,
    `When I`, `I'll` and `I've` were candidates in ninety replies between them —
    a run of two capitals reads as a name rather than as an instruction. That is
    real, and `_NEVER_A_NAME` already closes it: `i` is a pronoun, and a run of
    nothing but function words names nothing. Two mechanisms for one fault is
    how a guard goes quiet, so there is one.
    """
    letters = [character for character in token if character.isalpha()]
    return bool(letters) and letters[0].isupper() and not _is_shouted(token)


def _case_carries_nothing(tokens):
    """The whole-segment veto: Fully Title Cased.

    ⚠️ Without it, the corpus line *"Activity 2: Choose the Right Rock for the
    Job"* yields the candidate "Right Rock" and every sheet is flagged on day
    one. A heading tells you nothing by capitalising a word, because it
    capitalises all of them.
    """
    words = [token for token, _, _ in tokens if any(c.isalpha() for c in token)]
    capitals = [token for token in words if _is_capitalised(token)]
    return (
        len(words) > 1
        and len(capitals) > 1
        and all(
            _is_capitalised(token) or token.lower() in _MINOR_WORDS for token in words
        )
    )


def _still_the_same_name(segment, previous, start):
    """Is the gap between two capitals part of the name, or the end of it?

    Whitespace is. So is an abbreviation's own full stop — `Mrs. Medlock` is one
    person. ⚠️ A comma, a slash or a bracket is not: `[Ben/Dickon]` on a cloze
    sheet is two names, and `Ben, Dickon` is a list rather than a person.
    """
    gap = segment[previous:start].strip()
    return not gap or gap == "."


def _runs_of_capitals(segment, tokens):
    """`(position, words)` for each run of capitals belonging to one name."""
    runs, current, at, previous_end = [], [], None, None
    for position, (token, start, end) in enumerate(tokens):
        if _is_capitalised(token):
            touching = (
                current
                and previous_end is not None
                and _still_the_same_name(segment, previous_end, start)
            )
            if touching:
                current.append(token)
            else:
                if current:
                    runs.append((at, current))
                current, at = [token], position
        elif current:
            runs.append((at, current))
            current, at = [], None
        previous_end = end
    if current:
        runs.append((at, current))
    return runs


def _is_numbered(segment, tokens, last):
    """Is the word after this run a number? Then it is furniture, not a name.

    ⚠️ Measured over the corpus: `Step 3`, `Step 4`, `Activity 1`, `Lesson 1`,
    `Year 3`, `Steps 1, 2 and 3` — between them the largest group left once the
    shouting was dealt with. **Worksheets number everything and nobody numbers
    a person**, so this is a structural rule and not a list of the words that
    happen to get numbered in one Science unit.
    """
    if last + 1 >= len(tokens):
        return False
    following, start, _ = tokens[last + 1]
    return (
        following.isdigit()
        and not segment[tokens[last][2]:start].strip()
    )


def names_on(reply):
    """Every named thing the reply introduces, as `(name, where)` pairs.

    Two passes, because the second needs the whole reply: a lone capital
    opening a segment counts only when the same word is used mid-sentence
    elsewhere. One pass could not know that, and a word list is what one pass
    degenerates into.
    """
    read = [(segment, _tokens(segment))
            for text in _texts_in(reply)
            for segment in _segments(text)]

    # ⚠️ **A vetoed segment may not vouch for anything.** A heading capitalises
    # every word it has, so its second and third words are mid-sentence by
    # position and say nothing by convention — and they were corroborating the
    # very headings the veto had just thrown out. Measured: `Hook`, `Plenary`,
    # `Practice`, `Modelling`, `Is`, `Hard`, `Smooth` and `Soft` were all still
    # firing across the corpus after four other fixes, and all of them for this
    # one reason.
    speaks = [(segment, tokens) for segment, tokens in read
              if not _case_carries_nothing(tokens)]

    mid_sentence = {
        token.lower()
        for _, tokens in speaks
        for position, (token, _, _) in enumerate(tokens)
        if position and _is_capitalised(token)
    }

    found, seen = [], set()
    for segment, tokens in speaks:
        for position, run in _runs_of_capitals(segment, tokens):
            alone_at_the_front = position == 0 and len(run) == 1
            if alone_at_the_front and run[0].lower() not in mid_sentence:
                continue
            if _is_numbered(segment, tokens, position + len(run) - 1):
                continue
            # A run of nothing but function words names nothing. A run that
            # merely *starts* with one still does — *The Rookery* is a place.
            if all(word.lower().split("'")[0] in _NEVER_A_NAME for word in run):
                continue
            name = " ".join(run)
            if name.lower() in seen:
                continue
            seen.add(name.lower())
            found.append((name, " ".join(segment.split())))
    return tuple(found)


# --------------------------------------------------------------------------
# What counts as hers
# --------------------------------------------------------------------------


def _theme_words():
    """Every word of every theme — *Mission*, *Captain's Log*, *Dive Log*.

    Derived rather than copied, so a theme added later cannot start flagging
    sheets that print it.
    """
    words = set()
    for theme in THEMES.values():
        for value in theme.values():
            words |= _words_for_matching(value)
    return words


def _subject_words():
    """The subjects she chooses between. `English` alone was in 47 replies.

    Derived from the curriculum for the same reason as the themes. It is also
    already in `approved` on the worksheet screen — belt and braces, because
    the lesson side reaches this module in a later phase and a subject is hers
    on both.
    """
    from curriculum import SUBJECT_REGISTRY

    return _words_for_matching(" ".join(SUBJECT_REGISTRY))


_ALWAYS_SUPPORTED = frozenset(
    _theme_words()
    | _subject_words()
    | _words_for_matching(" ".join(ALWAYS_ALLOWED))
    | _words_for_matching(" ".join(_HONORIFICS))
)


def supported_words(source_text, approved):
    """Her text, plus everything she typed or approved, plus what every sheet says.

    ⚠️ **Neither argument has a default, deliberately.** The failure this whole
    design is built against is the guard running on an empty haystack and
    reporting green — one call site forgets the source, every test passes, and
    the screen says "checked against your text" when it never was. A forgotten
    argument has to be a `TypeError` at the call site, not a silent skip.
    """
    words = set(_words_for_matching(source_text))
    for piece in approved or ():
        words |= _words_for_matching(piece)
    return frozenset(words | _ALWAYS_SUPPORTED)


def _is_supported(name, haystack):
    """Whole words, all of them. `Alice` is not supported by `Alicia`."""
    return _words_for_matching(name) <= haystack


def _reason(name):
    return (
        f"“{name}” is not in the text you supplied, or in anything you "
        f"typed. The sheet has introduced it — check it is not something from "
        f"later in the story."
    )


def unsupported_names(reply, source_text, approved):
    """`(where, reason)` pairs — the shape `lowered_objective_flags` uses."""
    haystack = supported_words(source_text, approved)
    return tuple(
        (where, _reason(name))
        for name, where in names_on(reply)
        if not _is_supported(name, haystack)
    )


def with_the_names_checked(outcome, source_material, approved):
    """The outcome, with what the name check found — or why it could not run.

    ⚠️ **A different question from `source_checked`, and collapsing the two
    loses the check on five of the seven types that take a source.** Whether her
    passage is printed whole is about the kind of sheet; whether the names can
    be checked is about whether we hold her words at all. A cloze sheet never
    prints a passage and its names are perfectly checkable.
    """
    if source_material is None:
        return outcome

    if not source_material.is_held:
        # 🚨 No haystack, so no claim. And a haystack transcribed from the PDF
        # by the model would be worse than none: a hallucinated name would
        # whitelist itself, and the check's own evidence would vouch for the
        # spoiler.
        return dataclasses.replace(
            outcome,
            names_checked=False,
            why_names_not_checked=NAMES_CANNOT_BE_CHECKED,
        )

    findings = unsupported_names(outcome.content, source_material.text, approved)
    return dataclasses.replace(
        outcome,
        names_checked=True,
        flags=tuple(outcome.flags)
        + tuple(f"{reason}\n\nOn this sheet: “{where}”" for where, reason in findings),
    )
