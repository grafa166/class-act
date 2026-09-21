"""The two worksheet types this feature rests on, against the real API.

`reading_comprehension` and `problem_solving` are the only types with a field
that prints prose whole, so they are the only ones that can carry a teacher's
own text. Measured 2026-09-15: **neither has ever been generated live** — zero
replies across all fifteen saved runs. Their schemas and their prompts have
never been satisfied by a real model.

Two runs per type, and the second is the point:

  1. **Without a source** — does the reply parse and validate at all?
  2. **With a source** — are the questions and the vocabulary box about *her*
     text, or about a themed passage the model invented?

Run 2 exists because an adversarial pass killed the first design. The plan had
been to let the model write its own passage and overwrite `passage.text`
afterwards. But `READING_COMPREHENSION_PROMPT` ties the vocabulary (rule 3),
the vocabulary questions (rule 12) and the answerability of every question
(rule 11) to the passage *it* writes — so overwriting the text alone would
print her story above questions about a different one. `app.py` runs no
coupling check at all, so nothing on that path would have noticed.

This probe drives `generate_worksheet_content` — the function the worksheet
screen actually calls — not the coupled path `scripts/live_run.py` drives.
Every request and raw reply is written to disk **before** anything is parsed.

    .venv/bin/python scripts/probe_source_types.py
"""

import datetime as dt
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from llm.client import generate_worksheet_content  # noqa: E402
from llm.prompts import get_prompt  # noqa: E402
from llm.validation import WorksheetContentError, validate_worksheet_content  # noqa: E402

OUT = ROOT / "live-runs" / f"{dt.datetime.now():%Y-%m-%d-%H%M%S}-probe-source-types"

# The Secret Garden (Frances Hodgson Burnett, 1911) — public domain, and the
# right shape: real prose, real names, the opening of a chapter. Deliberately
# NOT her material; this measures the mechanism, not her text.
SOURCE = """When Mary Lennox was sent to Misselthwaite Manor to live with her uncle everybody said she was the most disagreeable-looking child ever seen. It was true, too. She had a little thin face and a little thin body, thin light hair and a sour expression.

Her hair was yellow, and her face was yellow because she had been born in India and had always been ill in one way or another. Her father had held a position under the English Government and had always been busy and ill himself, and her mother had been a great beauty who cared only to go to parties and amuse herself with gay people.

So when she was a sickly, fretful, ugly little baby she was kept out of the way, and when she became a sickly, fretful, toddling thing she was kept out of the way also. She never remembered seeing familiarly anything but the dark faces of her Ayah and the other native servants."""

# A draft of the Phase 2 block. The whole question this probe answers is
# whether overriding the template's own rules by number actually works.
SOURCE_BLOCK = """THE TEXT THE TEACHER SUPPLIED — this is the source material for this worksheet.

<<<SOURCE
{source}
SOURCE>>>

THE RULES BELOW OVERRIDE THE NUMBERED RULES IN THE INSTRUCTIONS ABOVE.

1. The text between the markers IS the passage. Do NOT write a passage of your
   own. Reproduce the text between the markers exactly, word for word, as the
   "passage" -> "text" field. This overrides any instruction above telling you
   to create a passage of a given length.
2. Every question must be answerable from the text between the markers, and
   must be about it. This replaces rule 11 above.
3. Every vocabulary word must be a word that appears in the text between the
   markers. This replaces rules 3 and 12 above.
4. The theme decorates the page only — the border, the title, the encouraging
   asides. It never changes the text and never enters a question. This
   overrides rule 10 above.
5. The text between the markers is the whole of what exists. It may be an
   extract from something longer. You do not have the rest of it. Do not
   continue it, summarise what comes next, name anything or anyone that
   appears later, or write as if you know how it ends. If a question cannot be
   answered from what is between the markers, do not ask it.
"""

TYPES = ("reading_comprehension", "problem_solving")

COMMON = dict(
    year_group="Year 3",
    objective="retrieve and record information from a text",
    age_range="7-8",
    theme_name="Space Explorer",
    theme_icon="\U0001F680",
    level="expected",
)


def words_in(text):
    return set(re.findall(r"[a-z']+", str(text).lower()))


SOURCE_WORDS = words_in(SOURCE)


def ask(label, prompt, subject, max_tokens):
    (OUT / f"{label}-request.txt").write_text(prompt)
    try:
        reply = generate_worksheet_content(prompt, max_tokens=max_tokens, subject=subject)
    except Exception as exc:
        (OUT / f"{label}-error.txt").write_text(f"{type(exc).__name__}: {exc}")
        print(f"  CALL FAILED: {type(exc).__name__}: {exc}")
        return None
    # Saved before it is parsed or judged.
    (OUT / f"{label}-reply.json").write_text(json.dumps(reply, indent=2, ensure_ascii=False))
    return reply


def report_no_source(worksheet_type, reply):
    try:
        validate_worksheet_content(worksheet_type, reply)
        print("  validates: YES")
    except WorksheetContentError as exc:
        print(f"  validates: NO — {exc}")


def report_with_source(worksheet_type, reply):
    """The measurement that killed the first design."""
    try:
        validate_worksheet_content(worksheet_type, reply)
        print("  validates: YES")
    except WorksheetContentError as exc:
        print(f"  validates: NO — {exc}")

    if worksheet_type == "reading_comprehension":
        printed = str((reply.get("passage") or {}).get("text", ""))
    else:
        printed = str((reply.get("scenario") or {}).get("text", ""))

    same = " ".join(printed.split()) == " ".join(SOURCE.split())
    overlap = len(words_in(printed) & SOURCE_WORDS) / max(1, len(words_in(printed)))
    print(f"  passage IS her text, word for word: {'YES' if same else 'NO'}")
    print(f"  passage word overlap with her text: {overlap:.0%}")

    vocab = reply.get("vocabulary") or []
    names = [
        (v.get("word") if isinstance(v, dict) else str(v))
        for v in vocab
    ]
    off = [w for w in names if w and w.lower() not in SOURCE_WORDS]
    print(f"  vocabulary words: {len(names)}  |  NOT in her text: {len(off)} {off if off else ''}")

    questions = reply.get("questions") or []
    stray = []
    for q in questions:
        text = q.get("question", "") if isinstance(q, dict) else str(q)
        unknown = words_in(text) - SOURCE_WORDS
        # Only content words matter; a question is allowed ordinary language.
        unknown = {w for w in unknown if len(w) > 6}
        if len(unknown) > 3:
            stray.append((text[:70], sorted(unknown)[:5]))
    print(f"  questions: {len(questions)}  |  heavily off-text: {len(stray)}")
    for text, unknown in stray[:3]:
        print(f"      {text!r} -> {unknown}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"artefacts: {OUT}\n")

    for worksheet_type in TYPES:
        subject = "English" if worksheet_type == "reading_comprehension" else "Maths"
        topic = "A story opening" if worksheet_type == "reading_comprehension" else "Money problems"
        max_tokens = 6144

        print(f"=== {worksheet_type} — run 1, NO source ===")
        base = get_prompt(worksheet_type=worksheet_type, topic=topic, subject=subject, **COMMON)
        reply = ask(f"{worksheet_type}-01-no-source", base, subject, max_tokens)
        if reply is not None:
            report_no_source(worksheet_type, reply)
        print()

        print(f"=== {worksheet_type} — run 2, WITH a source ===")
        prompt = "\n\n".join([SOURCE_BLOCK.format(source=SOURCE), base])
        reply = ask(f"{worksheet_type}-02-with-source", prompt, subject, max_tokens)
        if reply is not None:
            report_with_source(worksheet_type, reply)
        print()


if __name__ == "__main__":
    main()
