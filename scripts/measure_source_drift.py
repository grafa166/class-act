"""How far a printed passage sits from the text she supplied — measured, not guessed.

`with_the_source_in_place` has to tell two things apart:

- **Drift.** The model reproduced her text but tidied it — a smart quote, an
  ellipsis, a dropped last paragraph. Her text is substituted back in and the
  sheet is correct.
- **A wholesale ignore.** The model wrote about something else entirely and the
  source never reached the page. Measured live on 2026-09-15: a story extract
  fed to a maths word-problem sheet produced a worksheet about buying oxygen
  tanks, with no error. Substituting her text into *that* reply prints her
  story above questions that have nothing to do with it — which is exactly the
  incoherence the adversarial pass killed the first design over.

A threshold between those two cannot be picked by taste, so this measures it.
No API calls: everything here is a reply already on disk.

    .venv/bin/python scripts/measure_source_drift.py

⚠️ **Read what this census is and is not.** The negative side is broad — 133
saved replies, every one of them prose the model wrote without her text in
front of it. The positive side is **one** real sample: the single
reading-comprehension reply that reproduced a supplied text. Everything else on
the positive side is that one reply with drift applied to it by hand, which
measures the metric, not the model. So this can say with confidence where an
ignored source lands, and only where one reproduction landed.
"""

import difflib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROBE = ROOT / "live-runs" / "2026-09-15-232726-probe-source-types"

# The extract the probe supplied. The Secret Garden, public domain.
SOURCE = (PROBE / "reading_comprehension-02-with-source-reply.json")


def _words(text):
    return re.findall(r"[a-z0-9']+", str(text).lower())


def probe_overlap(source, printed):
    """The probe's own measure, kept so its 13% stays comparable."""
    here, there = set(_words(printed)), set(_words(source))
    return len(here & there) / max(1, len(here))


def content_overlap(source, printed):
    """The same, with the short words dropped — no stopword list to maintain."""
    here = {w for w in _words(printed) if len(w) > 3}
    there = {w for w in _words(source) if len(w) > 3}
    return len(here & there) / max(1, len(here))


# ⚠️ Imported, never re-implemented. A threshold set by a measurement of one
# thing and applied to another is how a guard ends up looking right and being
# blind — so the guard's own function is the one this census runs.
from planning.source_material import how_much_of_it_is_hers as bigram_containment  # noqa: E402


def sequence_ratio(source, printed):
    a = " ".join(_words(source))
    b = " ".join(_words(printed))
    return difflib.SequenceMatcher(None, a, b).ratio()


METRICS = {
    "probe_overlap": probe_overlap,
    "content_overlap": content_overlap,
    "bigram_containment": bigram_containment,
    "sequence_ratio": sequence_ratio,
}


# --------------------------------------------------------------------------
# The samples
# --------------------------------------------------------------------------

def load(path):
    text = path.read_text().strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except Exception:
        return None


def prose_of(payload):
    """Every stretch of prose in a reply, as one blob.

    A coupled reply has no `passage` — the two types that print prose whole
    have zero samples in the corpus, which is the blindness Phase 7 names. What
    these replies do give is 133 samples of *prose the model wrote with her
    text nowhere in sight*, which is precisely the negative case.
    """
    found = []

    def walk(value):
        if isinstance(value, str):
            if len(value.split()) >= 8:
                found.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)
    return "\n\n".join(found)


def the_supplied_text():
    """Her text, taken from the probe request rather than retyped."""
    request = (PROBE / "reading_comprehension-02-with-source-request.txt").read_text()
    body = request.split("<<<SOURCE", 1)[1].split("SOURCE>>>", 1)[0]
    return body.strip()


def drifted(text):
    """The ways a genuine reproduction comes back changed, and none of them lies.

    Every one of these is the model having reproduced her text. A guard that
    refuses any of them refuses correct work, which is the failure mode that
    reaches her as being told her own text is wrong.
    """
    paragraphs = text.split("\n\n")
    # ⚠️ **A fixture that does not contain the thing being varied measures
    # nothing.** The "typography tidied" row below curls apostrophes in an
    # extract that has none, so for its first three days it reported 1.000
    # while the comparison it was supposed to be testing scored 0.000 on a real
    # curled apostrophe. The `TYPOGRAPHY_AND_SCRIPT` block further down exists
    # because of that, and runs against text that actually contains the
    # characters in question.
    return {
        "typography tidied (see the warning above)": text.replace("'", "’").replace("--", "—"),
        "whitespace collapsed": " ".join(text.split()),
        "last paragraph dropped": "\n\n".join(paragraphs[:-1]),
        "first paragraph only": paragraphs[0],
        "one sentence dropped": text.replace("It was true, too. ", ""),
        "lightly tidied wording": (
            text.replace("disagreeable-looking", "disagreeable looking")
            .replace("familiarly", "clearly")
            .replace("gay people", "cheerful people")
        ),
    }


# ⚠️ **Written by hand, not by the model.** No adapted reply exists — *simplify
# or adapt* has never been run live. This is one plausible Year 3 rewrite of the
# extract, kept only to show the order of magnitude a real adaptation lands at,
# which is far below a reproduction and far above an ignored source. It is not
# evidence about what the model does, and no threshold may be set from it.
ADAPTED_BY_HAND = """Mary Lennox was sent to Misselthwaite Manor to live with her uncle. Everybody
said she was the most disagreeable-looking child they had ever seen. It was true. She had a thin
little face, a thin little body, thin light hair and a sour expression.

Her hair was yellow and her face was yellow too. She had been born in India and she had always
been ill. Her father worked for the English Government and was always busy and ill himself. Her
mother was very beautiful, but she only cared about going to parties.

When Mary was a baby she cried a lot and was often poorly, so she was kept out of the way. When
she learned to walk she was kept out of the way as well. The only people she remembered seeing
were her Ayah and the other servants."""


# Text that actually contains apostrophes, accents and a non-Latin script —
# the cases the Secret Garden extract cannot exercise. Each row is (label, her
# text, what came back, what the guard should do).
TYPOGRAPHY_AND_SCRIPT = [
    ("apostrophes curled, nothing else", "I can't go. We won't wait.",
     "I can’t go. We won’t wait.", "keep"),
    ("dashes and ellipsis tidied", "She waited -- and waited...",
     "She waited — and waited…", "keep"),
    ("an accented line reproduced exactly", "Éléa rêve d'un jardin secret.",
     "Éléa rêve d'un jardin secret.", "keep"),
    ("accents dropped in reproduction", "Éléa rêve d'un jardin secret.",
     "Elea reve d'un jardin secret.", "keep"),
    ("a non-Latin line reproduced exactly", "小猫睡觉。小狗跑步。",
     "小猫睡觉。小狗跑步。", "keep"),
    ("two unrelated non-Latin lines", "小猫睡觉。小狗跑步。",
     "火箭升空。宇航员登月。", "refuse"),
    ("the shortest possible reproduction", "Go!", "Go!", "keep"),
    ("the shortest possible substitution", "Go!", "Stop!", "refuse"),
]


def report_typography_and_script():
    print()
    print("text the main extract cannot exercise — apostrophes, accents, other scripts")
    width = max(len(label) for label, _, _, _ in TYPOGRAPHY_AND_SCRIPT)
    worst_keep, best_refuse = 1.0, 0.0
    for label, hers, printed, expected in TYPOGRAPHY_AND_SCRIPT:
        score = bigram_containment(hers, printed)
        if expected == "keep":
            worst_keep = min(worst_keep, score)
        else:
            best_refuse = max(best_refuse, score)
        print(f"  {expected.upper():<7} {label:{width}}  {score:>6.3f}")
    print(f"  lowest keep {worst_keep:.3f}   highest refuse {best_refuse:.3f}   "
          f"gap {worst_keep - best_refuse:+.3f}")


def main():
    source = the_supplied_text()
    print(f"her text: {len(source.split())} words, {len(source)} characters\n")

    rows = []

    # --- the two real with-source replies ---------------------------------
    reading = load(PROBE / "reading_comprehension-02-with-source-reply.json")
    printed = str((reading.get("passage") or {}).get("text", ""))
    rows.append(("REPRODUCED  reading_comprehension, source supplied (REAL)", printed, "keep"))

    solving = load(PROBE / "problem_solving-02-with-source-reply.json")
    printed = str((solving.get("scenario") or {}).get("text", ""))
    rows.append(("IGNORED     problem_solving, source supplied (REAL)", printed, "refuse"))

    # --- the model's own passage, written with no source at all -----------
    for label, path, field in (
        ("reading_comprehension", "reading_comprehension-01-no-source-reply.json", "passage"),
        ("problem_solving", "problem_solving-01-no-source-reply.json", "scenario"),
    ):
        payload = load(PROBE / path)
        printed = str((payload.get(field) or {}).get("text", ""))
        rows.append((f"IGNORED     {label}, no source at all (REAL)", printed, "refuse"))

    # --- drift applied by hand to the one real reproduction ---------------
    for label, text in drifted(source).items():
        rows.append((f"DRIFT       {label} (CONSTRUCTED)", text, "keep"))

    # Shown, but excluded from the gap below: an adaptation is a rewrite, so it
    # is neither a reproduction to substitute nor an ignore to refuse.
    rows.append(("ADAPTED     a Year 3 rewrite (BY HAND, no live sample)", ADAPTED_BY_HAND, "-"))

    width = max(len(label) for label, _, _ in rows)
    header = "  ".join(f"{name:>18}" for name in METRICS)
    print(f"{'':{width}}  {header}")
    for label, printed, _ in rows:
        scores = "  ".join(f"{fn(source, printed):>18.3f}" for fn in METRICS.values())
        print(f"{label:{width}}  {scores}")

    report_typography_and_script()

    # --- the broad negative census ----------------------------------------
    print()
    census = []
    for path in sorted(ROOT.glob("live-runs/*/*-reply.txt")):
        payload = load(path)
        if not isinstance(payload, dict):
            continue
        prose = prose_of(payload)
        if len(prose.split()) < 30:
            continue
        census.append((path, prose))

    print(f"negative census: {len(census)} saved replies, none written with her text present")
    for name, fn in METRICS.items():
        scores = sorted(fn(source, prose) for _, prose in census)
        worst = scores[-1]
        at95 = scores[int(len(scores) * 0.95)]
        print(
            f"  {name:>18}  median {scores[len(scores) // 2]:.3f}  "
            f"95th {at95:.3f}  WORST {worst:.3f}"
        )

    print()
    print("=" * 78)
    print("The gap to read: WORST negative must sit well below the LOWEST drift row.")
    for name, fn in METRICS.items():
        keeps = [fn(source, printed) for _, printed, verdict in rows if verdict == "keep"]
        refuses = [fn(source, printed) for _, printed, verdict in rows if verdict == "refuse"]
        refuses += [fn(source, prose) for _, prose in census]
        print(
            f"  {name:>18}  lowest keep {min(keeps):.3f}   "
            f"highest refuse {max(refuses):.3f}   "
            f"gap {min(keeps) - max(refuses):+.3f}"
        )


if __name__ == "__main__":
    main()
