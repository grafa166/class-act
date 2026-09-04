"""Run the whole flow against the real API, and keep every raw reply.

A test cannot see a prompt defect. Every unit test in this repo uses a fake
that returns whatever it was told to return, so a test can only ever prove that
our code does what we wrote it to do — never that Claude reads the instruction
the way we meant it. Seven defects have been found here, all of them live, none
of them reachable from a test: a coverage line silently moved instead of copied,
coverage vouched for on a lesson that never taught it, a connection dropped on a
long request, and four on the worksheet coupling.

Two rules this script exists to enforce.

**Run the whole flow, not one step of it.** Spine, then every lesson, then a
worksheet for each. One of the seven was invisible on a single lesson and only
appeared when three ran back to back.

**Save the raw reply before parsing it.** Three of the four worksheet defects
produced an identical error message — "the quote is not on the sheet" — from
three different causes, two of which were the guard refusing correct work.
Reading the artefact settled each in a minute; guessing from the message would
have fixed none of them. A reply that fails to parse is gone otherwise.

Every request, schema and reply lands in a timestamped folder under
`live-runs/`, numbered in the order they were sent.

    .venv/bin/python scripts/live_run.py
    .venv/bin/python scripts/live_run.py --lessons 2 --no-worksheets
"""

import argparse
import datetime as dt
import itertools
import json
import logging
import pathlib
import sys
import time
import traceback

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import llm.client as client_module  # noqa: E402
from planning.lesson import generate_lesson  # noqa: E402
from planning.spine import (  # noqa: E402
    coverage_map,
    coverage_never_taught,
    generate_spine,
)
from planning.worksheet import (  # noqa: E402
    generate_worksheet_for_lesson,
    repeated_task_shapes,
)

# The unit she is actually teaching, and the National Curriculum lines it is
# accountable for. Deliberately the same unit as earlier live runs, so the
# lesson-loss rate is comparable rather than merely reassuring.
SUBJECT = "Science"
YEAR_GROUP = "Year 3"
UNIT_TITLE = "Rocks and Soils"
OUTCOME = (
    "Children group rocks by their properties and say which rock they would "
    "choose for a job, and why."
)
COVERAGE = (
    "compare and group together different kinds of rocks on the basis of their "
    "appearance and simple physical properties",
    "describe in simple terms how fossils are formed when things that have "
    "lived are trapped within rock",
    "recognise that soils are made from rocks and organic matter",
)

# One per lesson, rotated, because a unit that is the same task four times over
# is its own defect and the sameness check should have something to see.
WORKSHEET_TYPES = ("word_bank", "cloze", "investigation", "matching")

LESSON_MINUTES = 60


class Repairs(logging.Handler):
    """Every ask-once-more, and whether it worked, kept with the results.

    A lesson or a worksheet that fails its own checks is asked for a second
    time carrying the reason. Whether that is working is the number that
    matters about it, and until this was added it only existed as logging
    interleaved with the printed output — so a run's saved results said how
    many lessons were lost and nothing about how many were saved.
    """

    def __init__(self):
        super().__init__(level=logging.INFO)
        self.log = []

    def emit(self, record):
        message = record.getMessage()
        if "repair" not in message.lower():
            return
        # Two entries per repair, not one: "asked" when it fired and "saved"
        # when the second attempt passed. A repair that fired and was refused
        # again leaves only the "asked", which is what the count needs.
        saved = record.levelno < logging.WARNING
        self.log.append({"outcome": "saved" if saved else "asked", "note": message})
        print(f"    {'repaired' if saved else 'asking again'}")

    def install(self):
        for name in ("planning.lesson", "planning.worksheet"):
            logger = logging.getLogger(name)
            logger.setLevel(logging.INFO)
            logger.addHandler(self)


class Recorder:
    """Writes each request, its schema and its raw reply to disk, in order.

    Hooked into `_request_json` and `_extract_json_from_text` rather than into
    any one generator, so the spine, the lessons and the worksheets are all
    captured by the same code and none can be forgotten. The reply is written
    *before* it is handed to the parser — that is the whole point.
    """

    def __init__(self, folder):
        self.folder = folder
        self.counter = itertools.count(1)
        self.current = 0
        self.log = []

    def install(self):
        original_request = client_module._request_json
        original_extract = client_module._extract_json_from_text

        def request(content, system_prompt, model, max_tokens, timeout,
                    stream=False, schema=None):
            self.current = next(self.counter)
            self._write("request.txt", self._as_text(content))
            self._write("system.txt", system_prompt)
            self._write(
                "schema.json",
                json.dumps(schema, indent=2) if schema else "(no schema sent)",
            )
            started = time.monotonic()
            try:
                result = original_request(
                    content, system_prompt, model, max_tokens, timeout,
                    stream, schema,
                )
            except Exception as exc:
                self._note(time.monotonic() - started, f"{type(exc).__name__}: {exc}")
                raise
            self._note(time.monotonic() - started, "parsed")
            return result

        def extract(text):
            # Before parsing. A reply that fails to parse is gone otherwise,
            # and an error message alone has settled none of these.
            self._write("reply.txt", text)
            return original_extract(text)

        client_module._request_json = request
        client_module._extract_json_from_text = extract

    def _as_text(self, content):
        if isinstance(content, str):
            return content
        return json.dumps(content, indent=2, default=str)

    def _write(self, name, text):
        path = self.folder / f"{self.current:02d}-{name}"
        path.write_text(text if isinstance(text, str) else str(text))

    def _note(self, seconds, outcome):
        reply = self.folder / f"{self.current:02d}-reply.txt"
        size = len(reply.read_text()) if reply.exists() else 0
        self.log.append(
            {"call": self.current, "seconds": round(seconds, 1),
             "reply_chars": size, "outcome": outcome}
        )
        print(f"    call {self.current}: {seconds:5.1f}s, {size:>6,} chars, {outcome}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lessons", type=int, default=4)
    parser.add_argument("--no-worksheets", action="store_true")
    args = parser.parse_args()

    stamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    folder = pathlib.Path(__file__).resolve().parent.parent / "live-runs" / stamp
    folder.mkdir(parents=True, exist_ok=True)
    print(f"Raw replies: {folder}\n")

    recorder = Recorder(folder)
    recorder.install()
    repairs = Repairs()
    repairs.install()

    # The same list object the handler appends to, so a run that dies early
    # still reports the second attempts it had already made.
    results = {
        "spine": None, "lessons": {}, "worksheets": {},
        "failures": [], "repairs": repairs.log,
    }

    print(f"Spine — {args.lessons} lessons of {UNIT_TITLE}")
    try:
        spine = generate_spine(
            subject=SUBJECT,
            year_group=YEAR_GROUP,
            lesson_count=args.lessons,
            outcome=OUTCOME,
            coverage=COVERAGE,
            unit_title=UNIT_TITLE,
        )
    except Exception as exc:
        print(f"  SPINE FAILED: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        _report(folder, recorder, results)
        return 1

    results["spine"] = [lesson.objective for lesson in spine.lessons]
    for lesson in spine.lessons:
        print(f"  {lesson.number}. {lesson.objective}")

    # The two honesty surfaces the screen shows her, checked here too. Neither
    # rejects anything, so a run that only watched for exceptions would call a
    # unit clean while the screen was telling her a scheme line is only ever
    # assessed and never taught — which is the artefact she hands a subject
    # leader. Left out of the first version of this script; added the same day.
    mapping = coverage_map(spine, COVERAGE)
    gaps = [line for line, lessons in mapping.items() if not lessons]
    assessed_only = coverage_never_taught(spine, COVERAGE)
    results["coverage_gaps"] = gaps
    results["assessed_but_never_taught"] = assessed_only
    for line in gaps:
        print(f"  GAP — no lesson teaches: {line}")
    for line in assessed_only:
        print(f"  ASSESSED BUT NEVER TAUGHT: {line}")
    if not gaps and not assessed_only:
        print(f"  Coverage: all {len(COVERAGE)} lines taught before the assessment.")

    print("\nLessons")
    written = {}
    for planned in spine.lessons:
        print(f"  Lesson {planned.number} of {len(spine.lessons)}")
        try:
            written[planned.number] = generate_lesson(
                spine=spine,
                number=planned.number,
                subject=SUBJECT,
                year_group=YEAR_GROUP,
                lesson_minutes=LESSON_MINUTES,
                coverage=planned.covers,
                outcome=OUTCOME,
            )
            print(f"    OK — {len(written[planned.number].steps)} steps")
        except Exception as exc:
            print(f"    LOST: {type(exc).__name__}: {exc}")
            results["failures"].append(
                {"where": f"lesson {planned.number}",
                 "error": f"{type(exc).__name__}: {exc}"}
            )
    results["lessons"] = {n: lesson.objective for n, lesson in written.items()}

    sheets = []
    if not args.no_worksheets and written:
        print("\nWorksheets")
        for position, (number, lesson) in enumerate(sorted(written.items())):
            kind = WORKSHEET_TYPES[position % len(WORKSHEET_TYPES)]
            print(f"  Lesson {number} — {kind}")
            try:
                sheet = generate_worksheet_for_lesson(
                    lesson=lesson,
                    worksheet_type=kind,
                    subject=SUBJECT,
                    year_group=YEAR_GROUP,
                    topic=UNIT_TITLE,
                    earlier_objectives=[
                        written[earlier].objective
                        for earlier in sorted(written)
                        if earlier < number
                    ],
                )
                sheets.append(sheet)
                results["worksheets"][number] = kind
                print(f"    OK — {len(sheet.evidence)} criteria evidenced")
            except Exception as exc:
                print(f"    LOST: {type(exc).__name__}: {exc}")
                results["failures"].append(
                    {"where": f"worksheet {number} ({kind})",
                     "error": f"{type(exc).__name__}: {exc}"}
                )

    if sheets:
        for reason in repeated_task_shapes(sheets):
            print(f"\n  Flagged: {reason}")

    _report(folder, recorder, results)

    expected_lessons = len(spine.lessons)
    fired = sum(1 for r in repairs.log if r["outcome"] == "asked")
    saved = sum(1 for r in repairs.log if r["outcome"] == "saved")
    print(
        f"\nLessons: {len(written)} of {expected_lessons}. "
        f"Worksheets: {len(sheets)} of {len(written) if not args.no_worksheets else 0}. "
        f"Second attempts: {fired} asked, {saved} saved."
    )
    return 0 if not results["failures"] else 1


def _report(folder, recorder, results):
    (folder / "calls.json").write_text(json.dumps(recorder.log, indent=2))
    (folder / "results.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    sys.exit(main())
