"""Every saved reply, run through the name check as it stands. No API calls.

In the shape of `scripts/sweep_refusals.py`, and kept for the same reason: the
sweeps that produced "87 claims" and "78 of 78" were thrown away, so none of it
is re-derivable. The rule is to sweep the corpus *before* adding a guard, and
that is not a thing to rewrite from scratch each time.

🚨 **READ WHAT THIS CANNOT TELL YOU BEFORE READING WHAT IT CAN.**

**1. It cannot tell you the detection rate.** Not one reply in the corpus was
generated from a teacher's source — the feature did not exist when they were
made — so there is no case here where a name *should* be caught. Nothing in this
output is evidence that the check finds anything. It is a **false-refusal
census** and nothing else: it answers "how often would this fire on ordinary
worksheet prose", which is the failure that would reach her as being told her
correct sheet is wrong.

**2. It is blind to the two types the whole feature rests on.** The corpus is
one Science unit, and `reading_comprehension` and `problem_solving` — the only
two that print dense prose full of capitalised names, and the hardest case for
a detector — are counted below and the count is the point. A clean census here
is evidence about the easy half, and must not be reported as more.

**3. A candidate here is not necessarily wrong.** These replies had no source,
so "not in her text" is true of nearly every name in them by construction. What
to read this for is the **structural** false positive — an instruction word, a
section heading, a theme label — because those would fire whatever she supplied.
Sort by how many replies a candidate appears in: a name in one reply is that
worksheet's subject matter, a word in forty is a hole in the detector.

    .venv/bin/python scripts/sweep_unseen_names.py
"""

import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import planning.source_names as N  # noqa: E402
from planning.source_names import names_on, supported_words  # noqa: E402
from planning.worksheet_schema import get_worksheet_schema  # noqa: E402

KINDS = (
    "word_bank", "cloze", "matching", "investigation", "reading_comprehension",
    "sentence_builder", "times_tables", "calculation_practice",
    "fraction_practice", "problem_solving",
)

BY_PROSE = (
    ("word bank", "word_bank"),
    ("cloze", "cloze"),
    ("matching", "matching"),
    ("investigation", "investigation"),
    ("reading comprehension", "reading_comprehension"),
    ("sentence builder", "sentence_builder"),
    ("times table", "times_tables"),
    ("calculation", "calculation_practice"),
    ("fraction", "fraction_practice"),
    ("problem solving", "problem_solving"),
)

SCHEMAS = {k: json.dumps(get_worksheet_schema(k), sort_keys=True) for k in KINDS}


def load_json(text):
    """Saved replies predate the schema, so some are wrapped in fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except Exception:
        return None


def kind_of(reply_path):
    schema_path = reply_path.with_name(reply_path.name.replace("-reply.txt", "-schema.json"))
    if schema_path.exists():
        raw = schema_path.read_text().strip()
        if raw.startswith("{"):
            saved = json.dumps(json.loads(raw), sort_keys=True)
            for kind, text in SCHEMAS.items():
                if text == saved:
                    return kind
    request = reply_path.with_name(reply_path.name.replace("-reply.txt", "-request.txt"))
    if request.exists():
        first = request.read_text()[:300].lower()
        for needle, kind in BY_PROSE:
            if needle in first:
                return kind
    return None


def approved_on_that_run(payload):
    """Her words on the run that made this reply: the objective and criteria.

    The nearest thing the corpus has to "anything she typed or approved". There
    was no source, so this is the whole haystack — which is why every subject
    noun in the sheet shows up below, and why the thing to read for is the words
    that are not subject matter.
    """
    approved = []
    for key in ("objective", "title", "topic"):
        if isinstance(payload.get(key), str):
            approved.append(payload[key])
    criteria = payload.get("success_criteria")
    if isinstance(criteria, list):
        approved += [c for c in criteria if isinstance(c, str)]
    return tuple(approved)


replies, by_kind = [], collections.Counter()
for reply_path in sorted(ROOT.glob("live-runs/*/*-reply.txt")):
    payload = load_json(reply_path.read_text())
    if not isinstance(payload, dict):
        continue
    kind = kind_of(reply_path)
    by_kind[kind or "(not identifiable)"] += 1
    approved = approved_on_that_run(payload)
    haystack = supported_words("", approved)
    found = names_on(payload)
    unsupported = [
        (name, where)
        for name, where in found
        if not N._words_for_matching(name) <= haystack
    ]
    replies.append({
        "path": reply_path, "kind": kind,
        "candidates": found, "unsupported": unsupported,
    })

print(f"saved replies read:        {len(replies)}")
print(f"files on disk:             {len(list(ROOT.glob('live-runs/*/*-reply.txt')))}")
print()
print("by worksheet type:")
for kind in KINDS:
    count = by_kind.get(kind, 0)
    blind = "   <-- ZERO SAMPLES; this feature rests on it" if not count else ""
    print(f"  {kind:<24} {count:>4}{blind}")
if by_kind.get("(not identifiable)"):
    print(f"  {'(not identifiable)':<24} {by_kind['(not identifiable)']:>4}")
print()

# ⚠️ **Split, because only one half is the surface this check runs on.** Phase
# 4 renders on the worksheet screen and nowhere else. The rest of the corpus is
# lesson plans and unit spines — real model prose, and worth reading, but a
# candidate raised in one is not a thing any teacher can be shown today. Read
# the worksheet number as the census; read the other as a preview of Phase 5.
SURFACES = (
    ("worksheet replies — THE SURFACE THIS CHECK RUNS ON", lambda r: r["kind"]),
    ("lesson plans and spines — not checked until Phase 5", lambda r: not r["kind"]),
)

for heading, belongs in SURFACES:
    here = [r for r in replies if belongs(r)]
    candidates = sum(len(r["candidates"]) for r in here)
    unsupported = sum(len(r["unsupported"]) for r in here)
    noisy = sum(1 for r in here if r["unsupported"])
    print("=" * 78)
    print(heading)
    print("=" * 78)
    print(f"  replies:                     {len(here)}")
    print(f"  capitalised candidates:      {candidates}")
    print(f"  of those, unsupported:       {unsupported}")
    print(f"  replies with at least one:   {noisy} of {len(here)}")
    print()

    seen_in = collections.Counter()
    example = {}
    for reply in here:
        for name, where in reply["unsupported"]:
            seen_in[name] += 1
            example.setdefault(name, where)

    print("  unsupported candidates, by how many replies they appear in.")
    print("  ⚠️  a name in one reply is that sheet's subject matter; a word in")
    print("      many is a hole in the detector, and is what this sweep is for.")
    for name, count in seen_in.most_common():
        print(f"  {count:>4}  {name}")
        print(f"        {example[name][:92]!r}")
    print()
