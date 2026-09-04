"""Every worksheet reply ever saved, replayed through the guard as it stands.

Costs no API calls. Answers one question the live runs cannot: of the refusals
in the corpus, which ones would now be handed the sheet's own lines to copy,
and which are handed nothing by design.

A clean live run reads no refusal, so it verifies nothing about a refusal.
The corpus is the only place enough refusals exist to say anything at all.
"""

import json
import pathlib
import sys
from types import SimpleNamespace

ROOT = pathlib.Path("/Users/graemeheerden/Documents/Claude Code /Class Act")
sys.path.insert(0, str(ROOT))

import planning.worksheet as W  # noqa: E402
from planning.worksheet_schema import get_worksheet_schema  # noqa: E402

KINDS = (
    "word_bank", "cloze", "matching", "investigation", "reading_comprehension",
    "sentence_builder", "times_tables", "calculation_practice",
    "fraction_practice", "problem_solving",
)

# The first line of a worksheet request names the type in prose. Only used
# where no schema was saved beside the reply, i.e. runs before schemas existed.
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
        # "(no schema sent)" is how a call that sent none is recorded.
        raw = schema_path.read_text().strip()
        if raw.startswith("{"):
            saved = json.dumps(json.loads(raw), sort_keys=True)
            for kind, text in SCHEMAS.items():
                if text == saved:
                    return kind, "schema"
    request = reply_path.with_name(reply_path.name.replace("-reply.txt", "-request.txt"))
    if request.exists():
        first = request.read_text()[:300].lower()
        for needle, kind in BY_PROSE:
            if needle in first:
                return kind, "prose"
    return None, None


def lesson_from(payload):
    return SimpleNamespace(
        number=1,
        objective=payload["objective"],
        success_criteria=[
            SimpleNamespace(criterion=c, evidence="as recorded in the original run")
            for c in payload["success_criteria"]
        ],
    )


rows = []
for reply_path in sorted(ROOT.glob("live-runs/*/*-reply.txt")):
    payload = load_json(reply_path.read_text())
    if not isinstance(payload, dict):
        continue
    if not {"evidence", "objective", "success_criteria"} <= set(payload):
        continue
    kind, how = kind_of(reply_path)
    if kind is None:
        rows.append({"path": reply_path, "kind": None})
        continue

    try:
        W.validate_coupled_worksheet(payload, lesson_from(payload), kind)
        verdict, reason = "accepted", ""
    except W.WorksheetCouplingError as exc:
        verdict, reason = "refused", str(exc)
    except Exception as exc:  # a shape the guard cannot even read
        verdict, reason = "unreadable", f"{type(exc).__name__}: {exc}"

    claims = payload.get("evidence") or []
    offers = []
    for claim in claims:
        quote = claim.get("quote", "")
        try:
            lines = W._lines_to_copy(quote, payload, kind)
        except Exception:
            lines = []
        offers.append({"quote": quote, "lines": lines})

    rows.append({
        "path": reply_path, "kind": kind, "how": how, "verdict": verdict,
        "reason": reason, "claims": len(claims), "offers": offers,
    })

worksheets = [r for r in rows if r.get("kind")]
unknown = [r for r in rows if not r.get("kind")]
accepted = [r for r in worksheets if r["verdict"] == "accepted"]
refused = [r for r in worksheets if r["verdict"] == "refused"]
unreadable = [r for r in worksheets if r["verdict"] == "unreadable"]

print(f"worksheet replies found:  {len(worksheets)}")
print(f"  identified by schema:   {sum(1 for r in worksheets if r['how'] == 'schema')}")
print(f"  identified by prose:    {sum(1 for r in worksheets if r['how'] == 'prose')}")
print(f"  kind not identifiable:  {len(unknown)}")
print(f"total evidence claims:    {sum(r['claims'] for r in worksheets)}")
print()
print(f"accepted:   {len(accepted)}")
print(f"refused:    {len(refused)}")
print(f"unreadable: {len(unreadable)}")
print()

with_lines = []
for r in refused:
    offered = [o for o in r["offers"] if o["lines"]]
    print(f"--- {r['path'].parent.name}/{r['path'].name}  [{r['kind']}]")
    first = r["reason"].strip().splitlines()[0] if r["reason"] else ""
    print(f"    refused: {first[:130]}")
    if offered:
        with_lines.append(r)
        for o in offered:
            print(f"    quote  : {o['quote'][:90]!r}")
            for line in o["lines"][: W.MOST_LINES_TO_OFFER]:
                print(f"      offers: {line[:90]!r}")
    else:
        print("    offers : nothing — quote appears nowhere on the sheet (by design)")
    print()

print("=" * 70)
print(f"refusals that WOULD carry lines: {len(with_lines)} of {len(refused)}")
print(f"refusals handed nothing:         {len(refused) - len(with_lines)} of {len(refused)}")
