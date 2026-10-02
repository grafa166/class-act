"""The two new boxes, against the real API.

A test cannot see a prompt defect -- fifteen of fifteen in this repo were found
only live. Four questions, each one a way the new blocks could fail that no
fake reply can show:

  A. **Do the three levels survive a task and barriers?** The three calls
     differ only by `level`. Counted in the returned JSON, not in a render.
  B. **Cause the failure: a task that names a number.** "Answer six questions"
     at all three levels. If the counts collapse to six, the block telling the
     model not to take a number from her words does nothing.
  C. **Do word meanings come back on an expected cloze?** The level rules say
     leave them out; the limited-English barrier says put them in. The block
     says the support wins. Does it?
  D. **Cause the failure: a task that asks for what the source law forbids.**
     "Write the next chapter", with her extract. The source law sits last and
     should win. Read the reply, and run the name check over it.

Drives `generate_worksheet_content` -- the function the worksheet screen calls.
Every request and raw reply is written to disk BEFORE anything is parsed.

    .venv/bin/python scripts/probe_two_boxes.py
"""

import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from llm.client import generate_worksheet_content  # noqa: E402
from llm.prompts import get_prompt  # noqa: E402
from llm.validation import validate_worksheet_content  # noqa: E402
from planning.source_material import (  # noqa: E402
    request_with,
    room_for_the_source,
    source_from_text,
    with_the_source_in_place,
)
from planning.source_names import with_the_names_checked  # noqa: E402
from planning.support import with_the_barriers_answered  # noqa: E402

OUT = ROOT / "live-runs" / f"{dt.datetime.now():%Y-%m-%d-%H%M%S}-probe-two-boxes"
LEVELS = ("developing", "expected", "greater_depth")

# The Secret Garden (1911), public domain. The same extract the source probe used.
SOURCE = """When Mary Lennox was sent to Misselthwaite Manor to live with her uncle everybody said she was the most disagreeable-looking child ever seen. It was true, too. She had a little thin face and a little thin body, thin light hair and a sour expression.

Her hair was yellow, and her face was yellow because she had been born in India and had always been ill in one way or another. Her father had held a position under the English Government and had always been busy and ill himself, and her mother had been a great beauty who cared only to go to parties and amuse herself with gay people.

So when she was a sickly, fretful, ugly little baby she was kept out of the way, and when she became a sickly, fretful, toddling thing she was kept out of the way also. She never remembered seeing familiarly anything but the dark faces of her Ayah and the other native servants."""

COMMON = dict(
    year_group="Year 3",
    topic="A story opening",
    objective="retrieve and record information from a text",
    age_range="7-8",
    theme_name="Space Explorer",
    theme_icon="\U0001F680",
    subject="English",
)


def ask(label, prompt, max_tokens, source=None):
    (OUT / f"{label}-request.txt").write_text(prompt)
    try:
        reply = generate_worksheet_content(
            request_with(prompt, source),
            max_tokens=max_tokens,
            subject="English",
            stream=source is not None,
        )
    except Exception as exc:
        (OUT / f"{label}-error.txt").write_text(f"{type(exc).__name__}: {exc}")
        print(f"  {label}: CALL FAILED: {type(exc).__name__}: {exc}")
        return None
    (OUT / f"{label}-reply.json").write_text(json.dumps(reply, indent=2, ensure_ascii=False))
    return reply


def three_levels(label, worksheet_type, **extra):
    counts = {}
    for level in LEVELS:
        prompt = get_prompt(worksheet_type=worksheet_type, level=level, **COMMON, **extra)
        reply = ask(f"{label}-{level}", prompt, 6144)
        if reply is None:
            continue
        validate_worksheet_content(worksheet_type, reply)
        raw = len(reply.get("questions", []))
        after = with_the_barriers_answered(reply, worksheet_type, extra.get("barriers", ()))
        lines = [q.get("lines") for q in after.content.get("questions", [])]
        counts[level] = raw
        print(f"  {level:14} questions returned {raw:2}  after barriers {len(after.content['questions']):2}  lines {lines}")
    distinct = len(set(counts.values()))
    print(f"  -> {distinct} different question counts across {len(counts)} levels")
    return counts


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"artefacts: {OUT}\n")
    results = {}

    print("=== A. three levels, with a task and three barriers ===")
    results["A"] = three_levels(
        "A-task-and-barriers",
        "reading_comprehension",
        task="Find out what Mary is like from what the story says about her.",
        barriers=("limited_english", "comprehension", "writing_length"),
    )

    print("\n=== B. cause the failure: a task that names a number ===")
    results["B"] = three_levels(
        "B-task-names-a-number",
        "reading_comprehension",
        task="Answer six questions about Mary.",
    )

    print("\n=== C. word meanings on an expected cloze, limited English ticked ===")
    prompt = get_prompt(worksheet_type="cloze", level="expected", barriers=("limited_english",), **COMMON)
    reply = ask("C-cloze-meanings", prompt, 4096)
    if reply is not None:
        outcome = with_the_barriers_answered(reply, "cloze", ("limited_english",))
        print(f"  {outcome.notes[0]}")
        results["C"] = outcome.notes[0]

    print("\n=== D. cause the failure: 'write the next chapter', with her extract ===")
    source = source_from_text(SOURCE, origin="the text you pasted")
    task = "Write the next chapter of the story, about what happens when Mary arrives at the Manor."
    prompt = get_prompt(
        worksheet_type="reading_comprehension",
        level="expected",
        source_material=source,
        source_action="questions_from",
        task=task,
        **COMMON,
    )
    reply = ask(
        "D-next-chapter",
        prompt,
        room_for_the_source(6144, "reading_comprehension", source),
        source=source,
    )
    if reply is not None:
        outcome = with_the_source_in_place(reply, "reading_comprehension", source, "questions_from")
        outcome = with_the_names_checked(
            outcome, source, (COMMON["topic"], COMMON["objective"], "English", "Space Explorer", task)
        )
        print(f"  passage word for word: {outcome.substituted}")
        print(f"  name-check flags: {len(outcome.flags)}")
        for flag in outcome.flags:
            print(f"    - {flag.splitlines()[0][:140]}")
        for q in outcome.content.get("questions", []):
            print(f"    Q{q.get('number')}: {q.get('question')}")
        results["D"] = {"flags": list(outcome.flags), "substituted": outcome.substituted}

    (OUT / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
