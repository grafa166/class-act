"""Break each guard on purpose, and see exactly which tests notice.

A test that passes either way proves nothing, and a guard with no test at all
looks identical to one with ten. Neither is visible on a green suite, which is
where every expensive defect in this project has hidden.

So: undo one thing a guard does, run the whole suite, list what failed, put it
back. Read the output as a table of *what each test is actually pinning*.

    .venv/bin/python scripts/mutate.py

Three shapes of result, and all three are findings:

- **The tests you expected, and only those.** The guard is pinned.
- **`NOTHING FAILED`.** Nothing in the suite can tell that change from no
  change. On 2026-09-03 this found a prompt test that matched a sentence
  elsewhere in the prompt, so it passed whether or not the thing it was written
  for was there.
- **Fewer tests than you expected, or different ones.** The tests are passing
  for a reason other than the one they claim. The same run found that the
  anti-fabrication tests rejected a stitched-together quote because of the
  order the pieces happen to come out in, not because each piece is searched on
  its own — so searching the whole sheet as one blob left almost all of them
  passing.

The mutations that matter most are the ones marked SOFTENED. Three of the five
times a guard here has refused correct work, the tempting fix was to widen the
check, and widening it is how the fabrication it was built to catch gets back
in. These prove the teeth are still there.

⚠️ **A mutation is a literal quotation of the source, so editing the code will
stale one.** That is not a problem — the entry prints `MUTATION DID NOT APPLY`
and the run carries on. Re-copy the lines from the file and move on; a stale
entry costs a minute and a silent one costs a lesson.
"""

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# {label: (file, exact source to replace, what to replace it with)}
MUTATIONS = {
    # ---- the worksheet coupling ----
    "the sheet's header is searchable again (only the claims stripped)": (
        "planning/worksheet.py",
        'NOT_A_TASK = ("evidence", "objective", "success_criteria", "title")',
        'NOT_A_TASK = ("evidence",)',
    ),
    "the evidence refusal names only the first fault it meets": (
        "planning/worksheet.py",
        "        if faults:\n            problems.extend(faults)",
        "        if faults:\n            raise WorksheetCouplingError(faults[0])",
    ),
    "the evidence refusal describes the fault instead of instructing": (
        "planning/worksheet.py",
        'f"...which does not appear anywhere on the worksheet.\\n"\n'
        '                f"{_HOW_TO_QUOTE}"',
        'f"...which does not appear anywhere on the worksheet."',
    ),
    "a refused sheet is thrown away rather than asked for again": (
        "planning/worksheet.py",
        "    payload = ask(prompt)\n    try:\n        return check(payload)",
        "    payload = ask(prompt)\n    if True:\n        return check(payload)\n"
        "    try:\n        return check(payload)",
    ),
    "an unrenderable sheet is given an untested second attempt too": (
        "planning/worksheet.py",
        "    except WorksheetCouplingError as refused:\n        logger.warning(",
        "    except ValueError as refused:\n        logger.warning(",
    ),
    "the prompt stops saying a table column is quoted by its heading": (
        "planning/worksheet.py",
        '"COLUMN HEADING \\u2014 quote the heading exactly as you wrote it, brackets "',
        '"TABLE \\u2014 say so however you like, brackets "',
    ),
    "the prompt stops showing the description beside the quote": (
        "planning/worksheet.py",
        '"       \\u2014 this is a description, and it is refused.",',
        '"       \\u2014 this one is refused.",',
    ),
    "SOFTENED: the sheet is searched as one blob instead of separate tasks": (
        "planning/worksheet.py",
        "    return [_normalise(piece) for piece in _strings_in(tasks)]",
        '    return [" ".join(_normalise(p) for p in _strings_in(tasks))]',
    ),
    "SOFTENED: a long enough run of the quote appearing on the sheet is enough": (
        "planning/worksheet.py",
        "    normalised = _normalise(quote)\n    if normalised in piece:\n        return True",
        "    normalised = _normalise(quote)\n    if normalised in piece:\n        return True\n"
        "    if any(\n"
        "        normalised[start:start + 30] in piece\n"
        "        for start in range(max(1, len(normalised) - 30))\n"
        "    ):\n        return True",
    ),
    "the refusal stops handing back the sheet's own lines": (
        "planning/worksheet.py",
        'f"{_HOW_TO_QUOTE}"\n'
        "                + _copy_one_of_these(_lines_to_copy(quote, payload, worksheet_type))",
        'f"{_HOW_TO_QUOTE}"',
    ),
    "a too-short quote is not shown the line it sits in": (
        "planning/worksheet.py",
        'f"does not say which part of the sheet you mean."\n'
        "                + _copy_one_of_these(_lines_to_copy(quote, payload, worksheet_type))",
        'f"does not say which part of the sheet you mean."',
    ),
    "SOFTENED: a fabricated quote is handed lines to copy anyway": (
        "planning/worksheet.py",
        "    return [line for line in found if _long_enough(line)]",
        "    return [line for line, _ in lines if _long_enough(line)]",
    ),
    "a line too short to be a quote is offered anyway": (
        "planning/worksheet.py",
        "    return [line for line in found if _long_enough(line)]",
        "    return list(found)",
    ),
    "the lines offered include the fragments a sentence is stored in": (
        "planning/worksheet.py",
        "            yield blanked, (filled, blanked)\n            return",
        "            yield blanked, (filled, blanked)",
    ),
    "the offer stops saying to take only one of them": (
        "planning/worksheet.py",
        '"printed on its own. Copy ONE of them exactly, and nothing else:\\n"',
        '"printed on its own:\\n"',
    ),
    "a capped list of lines stops saying it was capped": (
        "planning/worksheet.py",
        '+ (f"\\n  ...and {left} more of the sheet\'s lines like these." if left else "")',
        '+ ""',
    ),
    # ---- the worksheet's shape ----
    "the worksheet request goes out unconstrained again": (
        "planning/worksheet.py",
        "    schema = get_worksheet_schema(worksheet_type)",
        "    schema = None",
    ),
    "SOFTENED: the quote may be found in a key no generator prints": (
        "planning/worksheet.py",
        "        if k not in NOT_A_TASK and (printed is None or k in printed)",
        "        if k not in NOT_A_TASK",
    ),
    "a sheet with nothing printable blames the quote instead": (
        "planning/worksheet.py",
        "    if not sheet:",
        "    if False:",
    ),
    "an investigation may invent a section nothing prints": (
        "planning/worksheet_schema.py",
        '        "additionalProperties": False,',
        '        "additionalProperties": True,',
    ),
    "the map of what reaches the page drifts from the generator": (
        "planning/worksheet_schema.py",
        '        "conclusion_prompts",\n        "success_criteria",\n    },',
        '        "success_criteria",\n    },',
    ),
    "a cloze sheet loses the shape its passage comes back in": (
        "planning/worksheet_schema.py",
        '                "paragraphs": _array_of(_array_of(_PIECE)),',
        '                "paragraphs": _array_of(_STRING),',
    ),
    "a word-bank sentence loses the gaps between its fragments": (
        "planning/worksheet_schema.py",
        '"sentences": _array_of(_object({"pieces": _array_of(_PIECE)}, ("pieces",))),',
        '"sentences": _array_of(_STRING),',
    ),
    "an investigation sheet loses the field a child writes prose in": (
        "planning/worksheet_schema.py",
        '    "conclusion_prompts": _array_of(_STRING, at_least_one=True),',
        "",
    ),
    # ---- the worksheet she prints ----
    "the printed sheet is built from something other than the checked one": (
        "planning/worksheet_document.py",
        "        content=sheet.content,",
        '        content={**sheet.content, "sections": []},',
    ),
    "the objective on the sheet stops being the lesson's": (
        "planning/worksheet_document.py",
        "        objective=sheet.objective,",
        '        objective="",',
    ),
    "the worksheet file name stops being scrubbed": (
        "planning/worksheet_document.py",
        '    title = "".join(\n'
        "        character for character in str(unit_title).strip()\n"
        "        if character.isalnum() or character in \" -_&'\"\n"
        "    ).strip()",
        "    title = str(unit_title).strip()",
    ),
    "the answer key and the child's copy get the same file name": (
        "planning/worksheet_document.py",
        '    ending = "worksheet answers" if answers else "worksheet"',
        '    ending = "worksheet"',
    ),
    "a kind of sheet loses its generator": (
        "planning/worksheet_document.py",
        '    "investigation": generate_investigation_worksheet,\n',
        "",
    ),
    # ---- the library ----
    "a saved lesson loses its steps on the way back": (
        "planning/library.py",
        '    (Lesson, "steps"): LessonStep,',
        "",
    ),
    "a saved worksheet loses the evidence it was built on": (
        "planning/library.py",
        '    (CoupledWorksheet, "evidence"): EvidenceClaim,',
        "",
    ),
    "re-planning a unit forgets which lessons she taught": (
        "planning/library.py",
        '                    set_={"lesson": row["lesson"], "worksheet": row["worksheet"]},',
        '                    set_={"lesson": row["lesson"], "worksheet": row["worksheet"],\n'
        '                          "status": "planned"},',
    ),
    "a lesson she removed stays in the library": (
        "planning/library.py",
        "        db.execute(\n            delete(LESSONS).where(\n"
        "                LESSONS.c.unit_id == unit_id, LESSONS.c.number.notin_(numbers)\n"
        "            )\n        )",
        "        pass",
    ),
    "a deleted unit leaves its lessons behind (the cascade is switched off)": (
        "planning/library.py",
        'cursor.execute("PRAGMA foreign_keys = ON")',
        'cursor.execute("PRAGMA foreign_keys = OFF")',
    ),
    # ⚠️ Blind unless the suite is pointed at a real Postgres. That is the
    # finding, not a gap to shrug at: the store speaks to two databases and
    # only one of them is exercised by default. Run
    #   LIBRARY_TEST_URL=postgresql://... .venv/bin/python -m pytest tests/test_library.py
    # and this one is caught.
    "the hosted database is given the wrong kind of upsert": (
        "planning/library.py",
        'postgres_insert if library.dialect.name == "postgresql" else sqlite_insert',
        "sqlite_insert",
    ),
    "any word at all is accepted for what happened to a lesson": (
        "planning/library.py",
        "    if status not in STATUSES:",
        "    if False:",
    ),
    # ---- the lesson ----
    "a missing step field refuses on the spot again": (
        "planning/lesson.py",
        "                problems.append(\n"
        "                    f\"Step {position} does not say {name.replace('_', ' ')}. \"\n"
        '                    f"That is the difference between a plan and an outline."\n'
        "                )",
        "                raise LessonError(\n"
        "                    f\"Step {position} does not say {name.replace('_', ' ')}. \"\n"
        '                    f"That is the difference between a plan and an outline."\n'
        "                )",
    ),
    "the timing refusal short-circuits the field faults again": (
        "planning/lesson.py",
        "    refusal = _timing_refusal(uncosted, steps, lesson_minutes)\n"
        "    if refusal is not None:\n        problems.append(str(refusal))",
        "    refusal = _timing_refusal(uncosted, steps, lesson_minutes)\n"
        "    if refusal is not None:\n        raise refusal",
    ),
    "the timing refusal drops how many minutes have to move": (
        "planning/lesson.py",
        'f"{lesson_minutes}, so {abs(over)} minutes have to "\n'
        "            f\"{'come out' if over > 0 else 'go in'}.\"",
        'f"{lesson_minutes}."',
    ),
    "the timing refusal drops what each step currently costs": (
        "planning/lesson.py",
        '        + f"\\n{breakdown}\\n"\n',
        '        + " "\n',
    ),
    # ---- the lesson plan document ----
    "the plan document drops the misconceptions": (
        "generators/lesson_plan.py",
        "    _misconceptions(doc, lesson)\n",
        "",
    ),
    "the plan document stops drawing boxes": (
        "generators/lesson_plan.py",
        "    properties = paragraph._p.get_or_add_pPr()\n"
        "    borders = OxmlElement(\"w:pBdr\")",
        "    if paragraph is not None:\n        return\n"
        "    properties = paragraph._p.get_or_add_pPr()\n"
        "    borders = OxmlElement(\"w:pBdr\")",
    ),
    "the plan document goes back to Comic Sans": (
        "generators/lesson_plan.py",
        'LESSON_PLAN_FONT = "Arial"',
        'LESSON_PLAN_FONT = "Comic Sans MS"',
    ),
    "the plan document uses a colour outside the agreed palette": (
        "generators/lesson_plan.py",
        'BLUE_FILL = "F2F6FC"',
        'BLUE_FILL = "E8F5E9"',
    ),
    "one style is used for the objective and for everything like it": (
        "generators/lesson_plan.py",
        '        _say(doc, misconception["misconception"], "Item")',
        '        _say(doc, misconception["misconception"], "Objective")',
    ),
    "the plan prints a worksheet heading whether or not there is one": (
        "generators/lesson_plan.py",
        "    if worksheet is not None:\n        _the_worksheet(doc, worksheet)",
        '    _say(doc, "The worksheet, and what it proves", "Section")\n'
        "    if worksheet is not None:\n        _the_worksheet(doc, worksheet)",
    ),
    "the plan prints another lesson's worksheet without objecting": (
        "generators/lesson_plan.py",
        "    if worksheet is not None and worksheet.objective.strip() != lesson.objective.strip():",
        "    if False:",
    ),
    # ---- the worksheet typography ----
    "the worksheets go back to Comic Sans": (
        "generators/styles.py",
        "FONT_NAME = 'Arial'",
        "FONT_NAME = 'Comic Sans MS'",
    ),
    "one word type loses the symbol that replaced its colour": (
        "generators/styles.py",
        "        'symbol': '\\u26A1',   # ⚡\n        'label': 'Doing word',",
        "        'symbol': '',   #\n        'label': 'Doing word',",
    ),
    "two word types on one sheet share a mark again": (
        "generators/styles.py",
        "        'symbol': '\\U0001F511',   # 🔑\n        'label': 'Key Word',",
        "        'symbol': '\\u2B50',   # ⭐\n        'label': 'Key Word',",
    ),
    "a word card stops showing which kind of word it is": (
        "generators/components.py",
        "        run = p.add_run(f'{wt[\"symbol\"]} {part[\"part\"]}')",
        "        run = p.add_run(part['part'])",
    ),
    "a badge goes back to saying it in colour": (
        "generators/components.py",
        "        'inference': ('Think and Infer', BLUE_FILL_HEX, BLUE_HEX),",
        "        'inference': ('Think and Infer', 'E3F2FD', '1565C0'),",
    ),
    "the sheet tells a child to match the colours again": (
        "generators/cloze.py",
        "'Fill in the blanks below. Match the symbol '",
        "'Fill in the blanks below. Match the colour and symbol '",
    ),
    "the font goes back onto every run": (
        "generators/components.py",
        "    if not font_name:\n        return\n    rPr = run._element.get_or_add_rPr()",
        "    font_name = font_name or FONT_NAME\n    rPr = run._element.get_or_add_rPr()",
    ),
    "the download file name stops being scrubbed": (
        "generators/lesson_plan.py",
        "    title = \"\".join(\n"
        "        character for character in str(unit_title).strip()\n"
        "        if character.isalnum() or character in \" -_&'\"\n"
        "    ).strip()",
        "    title = str(unit_title).strip()",
    ),
}


def failing_tests():
    result = subprocess.run(
        [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "--no-header"],
        cwd=ROOT, capture_output=True, text=True,
    )
    caught = sorted(
        line.split("::", 1)[1].strip()
        for line in result.stdout.splitlines()
        if line.startswith("FAILED ")
    )
    # A mutation that will not even compile reports as a collection ERROR, not
    # a FAILED, and would otherwise read as "nothing noticed".
    if any(line.startswith("ERROR ") for line in result.stdout.splitlines()):
        return ["(the mutated file did not import — the mutation is malformed)"]
    return caught


def main():
    unseen = []
    for label, (name, before, after) in MUTATIONS.items():
        target = ROOT / name
        original = target.read_text()
        print(f"\n{label}")
        if before not in original:
            print("   !! MUTATION DID NOT APPLY — fix the mutation, not the code.")
            unseen.append(label)
            continue
        try:
            target.write_text(original.replace(before, after, 1))
            caught = failing_tests()
        finally:
            target.write_text(original)
        if not caught:
            print("   NOTHING FAILED — this change is invisible to the suite.")
            unseen.append(label)
        for test in caught:
            print(f"   {test}")

    print("\nrestored")
    if unseen:
        print(f"\n{len(unseen)} mutation(s) nothing caught or nothing applied:")
        for label in unseen:
            print(f"  - {label}")
    return 1 if unseen else 0


if __name__ == "__main__":
    sys.exit(main())
