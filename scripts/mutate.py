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

    # ---- the text she brings ----
    "any kind of worksheet is allowed a source": (
        "planning/source_material.py",
        "    capability = SOURCE_CAPABILITY.get(worksheet_type)\n"
        "    if capability is NOT_FROM_A_TEXT:",
        "    capability = SOURCE_CAPABILITY.get(worksheet_type)\n"
        "    if False:",
    ),
    "SOFTENED: a fill-in-the-gaps sheet claims it can print the source exactly": (
        "planning/source_material.py",
        '    "cloze": BUILDS_FROM_THE_SOURCE,',
        '    "cloze": PRINTS_THE_SOURCE,',
    ),
    "SOFTENED: a photograph is treated as words we hold": (
        "planning/source_material.py",
        "        return bool(self.text.strip())",
        "        return True",
    ),
    "a worksheet type the matrix has never heard of is allowed a source anyway": (
        "planning/source_material.py",
        "    capability = SOURCE_CAPABILITY.get(worksheet_type)\n"
        "    if capability is None:\n"
        "        return {}",
        "    capability = SOURCE_CAPABILITY.get(worksheet_type, PRINTS_THE_SOURCE)\n"
        "    if False:\n"
        "        return {}",
    ),
    "a source of any length is sent to Anthropic": (
        "planning/source_material.py",
        "    if len(tidied) > MAX_SOURCE_CHARS:",
        "    if False:",
    ),
    "her single line breaks stop becoming paragraphs, so the page runs them together": (
        "planning/source_material.py",
        '        pieces = [" ".join(line.split()) for line in text.split("\\n")]',
        "        pieces = [text]",
    ),
    "an action nobody has heard of is accepted": (
        "planning/source_material.py",
        "    if source_action not in WORKSHEET_ACTIONS:",
        "    if False:",
    ),

    # ---- her text on the page, and the reply that never used it ----
    "a sheet that used none of her text is handed over anyway": (
        "planning/source_material.py",
        "    if closeness < TOO_FAR_FROM_HER_TEXT and source_action in REPRODUCES_HER_TEXT:",
        "    if False:",
    ),
    "SOFTENED: the refusal line drops below every ignored reply ever measured": (
        "planning/source_material.py",
        "TOO_FAR_FROM_HER_TEXT = 0.10",
        "TOO_FAR_FROM_HER_TEXT = 0.005",
    ),
    "SOFTENED: a rewrite is close enough to be overwritten with her original": (
        "planning/source_material.py",
        "CLOSE_ENOUGH_TO_SUBSTITUTE = 0.90",
        "CLOSE_ENOUGH_TO_SUBSTITUTE = 0.50",
    ),
    "SOFTENED: the comparison counts single words instead of phrasing": (
        "planning/source_material.py",
        "    return set(zip(words, words[1:]))",
        "    return {(w,) for w in words}",
    ),
    "a photograph is compared against words we never held": (
        "planning/source_material.py",
        "    if not source_material.is_held:\n"
        "        return SourceOutcome(\n"
        "            content=content,\n"
        "            origin=source_material.origin,\n"
        "            why_not_checked=CANNOT_READ_IT,\n"
        "        )",
        "    if False:\n"
        "        return SourceOutcome(\n"
        "            content=content,\n"
        "            origin=source_material.origin,\n"
        "            why_not_checked=CANNOT_READ_IT,\n"
        "        )",
    ),
    "a sheet that builds tasks from the text is compared to it as if it printed it": (
        "planning/source_material.py",
        # ⚠️ Re-quoted 2026-09-22. It used to carry the `if where is None:` line
        # under this one, and a helper added on 2026-09-21 repeated both — so
        # the replacement landed on the copy and this reported NOTHING FAILED
        # on the first full run ever completed. The lookup now happens once, so
        # one line is the whole guard.
        "    where = WHERE_THE_PROSE_GOES.get(worksheet_type)",
        '    where = WHERE_THE_PROSE_GOES.get(worksheet_type, ("passage", "text"))',
    ),
    "the adaptation she asked for is overwritten with the original": (
        "planning/source_material.py",
        "    if source_action in REPRODUCES_HER_TEXT and closeness >= CLOSE_ENOUGH_TO_SUBSTITUTE:",
        "    if closeness >= CLOSE_ENOUGH_TO_SUBSTITUTE:",
    ),
    "the reply is corrected in place, so the saved artefact stops being evidence": (
        "planning/source_material.py",
        "        corrected = copy.deepcopy(content)",
        "        corrected = content",
    ),
    "a passage half hers and half invented goes to her with nothing said": (
        "planning/source_material.py",
        "    if source_action in REPRODUCES_HER_TEXT:\n"
        "        flags = (\n"
        '            "Some of this passage is not from the text you supplied.',
        "    if False:\n"
        "        flags = (\n"
        '            "Some of this passage is not from the text you supplied.',
    ),
    "an empty passage is reported as checked against her text": (
        "planning/source_material.py",
        "    if not printed.strip():",
        "    if False:",
    ),
    "a vocabulary box about the passage we deleted is printed anyway": (
        "planning/source_material.py",
        "        stray = vocabulary_not_in_the_passage(corrected, source_material.text)\n"
        "        if stray:",
        "        stray = vocabulary_not_in_the_passage(corrected, source_material.text)\n"
        "        if False:",
    ),
    "SOFTENED: a vocabulary word need only appear inside another word": (
        "planning/source_material.py",
        "    return len(word) >= 4 and any(page.startswith(word) for page in printed_words)",
        "    return any(word in page for page in printed_words)",
    ),
    "SOFTENED: a vocabulary word must match the page letter for letter": (
        "planning/source_material.py",
        "    if word in printed_words:\n        return True\n"
        "    return len(word) >= 4 and any(page.startswith(word) for page in printed_words)",
        "    return word in printed_words",
    ),
    "a vocabulary word that is not on the page is never mentioned": (
        "planning/source_material.py",
        "                flags=_vocabulary_flags(content, printed),",
        "                flags=(),",
    ),
    "typography is no longer normalised, so a curled apostrophe is a different word": (
        "planning/source_material.py",
        "    for odd, plain in _TYPOGRAPHY.items():\n        text = text.replace(odd, plain)",
        "    pass",
    ),
    "the comparison goes back to Latin letters only": (
        "planning/source_material.py",
        "    return re.findall(r\"[\\w']+\", text)",
        "    return re.findall(r\"[a-z0-9']+\", text)",
    ),
    "SOFTENED: everything is compared as loose words rather than phrasing": (
        "planning/source_material.py",
        "    printed_pairs = _word_pairs(printed)\n    if printed_pairs:",
        "    printed_pairs = _word_pairs(printed)\n    if False:",
    ),
    "a short reproduction is scored as if it shared nothing": (
        "planning/source_material.py",
        "    printed_words = set(_words(printed))\n    if not printed_words:\n        return 0.0",
        "    printed_words = set(_words(printed))\n    if True:\n        return 0.0",
    ),
    "the rewrite she asked for is refused for not matching her text": (
        "planning/source_material.py",
        "    if closeness < TOO_FAR_FROM_HER_TEXT and source_action in REPRODUCES_HER_TEXT:",
        "    if closeness < TOO_FAR_FROM_HER_TEXT:",
    ),
    "a rewrite that used none of her text is handed over with nothing said": (
        "planning/source_material.py",
        "    else:\n        flags = (\n            \"This has been rewritten,",
        "    elif False:\n        flags = (\n            \"This has been rewritten,",
    ),
    "the three reasons a sheet was not checked collapse into one sentence": (
        "planning/source_material.py",
        "NO_PASSAGE_CAME_BACK = \"The sheet came back with no passage on it to check.\"",
        "NO_PASSAGE_CAME_BACK = CANNOT_READ_IT",
    ),
    "a sheet that prints her text whole is given no room to print it": (
        "planning/source_material.py",
        "    room = base_tokens + -(-len(source_material.text) // _CHARS_PER_TOKEN)\n"
        "    return min(room, MAX_REPLY_TOKENS)",
        "    return base_tokens",
    ),
    "SOFTENED: a source too long to come back is sent anyway": (
        "planning/source_material.py",
        "    return min(room, MAX_REPLY_TOKENS)",
        "    return room",
    ),
    "a photograph is described to Claude instead of shown to it": (
        "planning/source_material.py",
        "    return [*source_material.blocks, {\"type\": \"text\", \"text\": prompt}]",
        "    return prompt",
    ),

    # ---- the name check (report-only) ----
    "SOFTENED: a shouted word is evidence again, so SEND and EAL are names": (
        "planning/source_names.py",
        "    return bool(letters) and letters[0].isupper() and not _is_shouted(token)",
        "    return bool(letters) and letters[0].isupper()",
    ),
    "SOFTENED: a heading is read as prose, so Right Rock is a name": (
        "planning/source_names.py",
        "    words = [token for token, _, _ in tokens if any(c.isalpha() for c in token)]\n"
        "    capitals = [token for token in words if _is_capitalised(token)]",
        "    return False\n"
        "    words = [token for token, _, _ in tokens if any(c.isalpha() for c in token)]\n"
        "    capitals = [token for token in words if _is_capitalised(token)]",
    ),
    "SOFTENED: a lone capital opening a line no longer needs corroborating": (
        "planning/source_names.py",
        "            if alone_at_the_front and run[0].lower() not in mid_sentence:\n"
        "                continue",
        "            if False:\n                continue",
    ),
    "SOFTENED: a vetoed heading vouches for the word it capitalised": (
        "planning/source_names.py",
        "    speaks = [(segment, tokens) for segment, tokens in read\n"
        "              if not _case_carries_nothing(tokens)]",
        "    speaks = [(segment, tokens) for segment, tokens in read]",
    ),
    "SOFTENED: Step 3 and Year 3 are names again": (
        "planning/source_names.py",
        "            if _is_numbered(segment, tokens, position + len(run) - 1):\n"
        "                continue",
        "            if False:\n                continue",
    ),
    "SOFTENED: an article or a pronoun counts as a name": (
        "planning/source_names.py",
        "            if all(word.lower().split(\"'\")[0] in _NEVER_A_NAME for word in run):\n"
        "                continue",
        "            if False:\n                continue",
    ),
    "the opening of a quotation stops being the start of a segment": (
        "planning/source_names.py",
        "            cut = _opens_a_quotation(text, at)",
        "            cut = False",
    ),
    "🚨 LOOSE: a name is matched by a longer word it sits inside": (
        "planning/source_names.py",
        "    return _words_for_matching(name) <= haystack",
        "    return all(\n"
        "        any(word in straw for straw in haystack)\n"
        "        for word in _words_for_matching(name)\n"
        "    )",
    ),
    "🚨 LOOSE: a name is matched by a shorter word inside it": (
        "planning/source_names.py",
        "def _is_supported(name, haystack):",
        "def _is_supported(name, haystack):\n"
        "    return all(\n"
        "        any(straw in word for straw in haystack)\n"
        "        for word in _words_for_matching(name)\n"
        "    )",
    ),
    "🚨 LOOSE: only the top level of the reply is read, not the whole of it": (
        "planning/source_names.py",
        "    if isinstance(value, str):\n        yield value",
        "    if isinstance(value, str):\n        yield value\n"
        "    elif isinstance(value, dict):\n"
        "        for item in value.values():\n"
        "            if isinstance(item, str):\n"
        "                yield item\n"
        "        return",
    ),
    "🚨 LOOSE: a photograph is reported as having had its names checked": (
        "planning/source_names.py",
        "            names_checked=False,\n"
        "            why_names_not_checked=NAMES_CANNOT_BE_CHECKED,",
        "            names_checked=True,",
    ),
    "the findings are counted and then dropped": (
        "planning/source_names.py",
        "        flags=tuple(outcome.flags)\n"
        "        + tuple(f\"{reason}\\n\\nOn this sheet: “{where}”\" for where, reason in findings),",
        "        flags=tuple(outcome.flags),",
    ),
    "an honorific becomes a name, so Mrs fires on every sheet": (
        "planning/source_names.py",
        '    | _words_for_matching(" ".join(_HONORIFICS))',
        "",
    ),
    "the full stop in Mrs. breaks one person into two findings": (
        "planning/source_names.py",
        '    return not gap or gap == "."',
        "    return not gap",
    ),
    "the themes stop being part of what she supplied": (
        "planning/source_names.py",
        "    _theme_words()\n    | _subject_words()",
        "    frozenset()\n    | _subject_words()",
    ),
    "the label stops saying it is not a promise of a spoiler-free sheet": (
        "planning/source_names.py",
        '    "against your text. **This is not a promise the sheet is spoiler-free** — a "',
        '    "against your text. "',
    ),

    # ---- the worksheet screen ----
    "her one hard constraint is defended by nothing but the prompt": (
        "app.py",
        "            outcome = with_the_names_checked(",
        "            outcome = (lambda *a: outcome)(",
    ),
    "what she typed is no longer counted as something she supplied": (
        "app.py",
        "                (\n"
        "                    params['effective_topic'],\n"
        "                    params['effective_objective'],",
        "                (\n"
        "                    '',\n"
        "                    '',",
    ),
    "🚨 LOOSE: the honest label is printed beside a sheet nothing was checked on": (
        "app.py",
        "    if outcome.names_checked:\n"
        "        st.caption(f\"\\U0001F50E {THE_HONEST_LABEL}\")",
        "    if True:\n"
        "        st.caption(f\"\\U0001F50E {THE_HONEST_LABEL}\")",
    ),
    "a finding is swallowed on every sheet that builds from her text": (
        "app.py",
        "    for flag in outcome.flags:\n        st.warning(flag)",
        "    if not outcome.source_checked:\n        return\n"
        "    for flag in outcome.flags:\n        st.warning(flag)",
    ),
    "the findings are nested inside the passage check instead": (
        "app.py",
        "    for flag in outcome.flags:\n        st.warning(flag)",
        "    if outcome.source_checked:\n"
        "        for flag in outcome.flags:\n            st.warning(flag)",
    ),
    # The two faults found on 2026-09-20, each put back. Both were in a tree
    # with 1,267 tests passing, and both crash on the first press of Generate.
    "a function is called that nobody imported": (
        "app.py",
        "    request_with,\n    room_for_the_source,\n",
        "",
    ),
    "a call hands its arguments over in the wrong order": (
        "app.py",
        "                max_tok, params['ws_type_key'], params.get('source_material')",
        "                max_tok, params.get('source_material'), params.get('source_action')",
    ),

    # ---- the worksheet screen (existing) ----
    "a new input is missing from what Regenerate replays": (
        "app.py",
        "            'source_material': source_material,\n",
        "",
    ),
    "the source is never sent with the request at all": (
        "app.py",
        "                request_with(prompt, params.get('source_material')),",
        "                prompt,",
    ),
    "a long reply is asked for in one piece, as it was on 2026-09-02": (
        "app.py",
        "                stream=params.get('source_material') is not None,",
        "                stream=False,",
    ),
    "the guard between the reply and the sheet is skipped": (
        "app.py",
        "            outcome = with_the_source_in_place(\n"
        "                content,\n"
        "                params['ws_type_key'],\n"
        "                params.get('source_material'),\n"
        "                params.get('source_action'),\n"
        "            )\n"
        "            content = outcome.content",
        "            outcome = SourceOutcome(content=content)",
    ),
    "a pairing that cannot work is only refused after the tokens are spent": (
        "app.py",
        "    if params.get('source_material') is not None:\n"
        "        try:\n"
        "            check_the_pairing(params['ws_type_key'], params['source_action'])",
        "    if False:\n"
        "        try:\n"
        "            check_the_pairing(params['ws_type_key'], params['source_action'])",
    ),

    # ---- what the prompt says about her text ----
    "the source is placed after the instructions instead of before them": (
        "llm/prompts.py",
        # ⚠️ Re-quoted 2026-09-22, having gone stale when the PDF fix moved the
        # opening into a variable. It had been silently unapplied ever since,
        # and only a full run says so — every run before this one was filtered.
        "            opening,\n"
        "            base,",
        "            base,\n"
        "            opening,",
    ),
    "the law about later parts of the text is dropped": (
        "llm/prompts.py",
        '    return "\\n\\n".join([overrides, SOURCE_LAW])',
        '    return overrides',
    ),
    "SOFTENED: a sheet that cannot print prose is told to reproduce it whole": (
        "llm/prompts.py",
        "        overrides = BUILDS_OVERRIDES.format(what_to_do=WHAT_TO_DO[source_action])",
        "        overrides = PRINTS_OVERRIDES.format(\n"
        "            what_the_passage_is=WHAT_THE_PASSAGE_IS[source_action]\n"
        "        )",
    ),
    "a photograph is sent with an empty source box and rules pointing into it": (
        "llm/prompts.py",
        "    if source_material.is_held:\n"
        "        opening = SOURCE_OPENING.format(source=source_material.text)",
        "    if True:\n"
        "        opening = SOURCE_OPENING.format(source=source_material.text)",
    ),
    "a prompt with no source quietly gains the source wording anyway": (
        "llm/prompts.py",
        "    if source_material is None:\n        return base",
        "    if False:\n        return base",
    ),

    # ---- the ten prompts, as they were ----
    # ⚠️ Both of these caught NOTHING before `tests/prompts_as_they_were/` existed
    # (measured 2026-10-02). The only guard on the templates was a comparison of two
    # live calls, which cannot see a template edit at all.
    "a differentiation heading is reworded in one template": (
        "llm/prompts.py",
        "DIFFERENTIATION LEVEL RULES - YOU MUST FOLLOW THESE EXACTLY:",
        "DIFFERENTIATION RULES:",
    ),
    "\U0001F6A8 SOFTENED: the most-supported children stop being promised word choices": (
        "llm/prompts.py",
        '- Every blank MUST have a "choices" field with exactly 3 word options',
        '- Blanks may have a "choices" field with some word options',
    ),

    # ---- the pages of it she has reached ----
    "\U0001F6A8 LOOSE: the whole document is sent whatever range she picked": (
        "planning/source_material.py",
        "        data = cut_to_pages(data, first, last)\n"
        "        origin = _named_pages(filename, first, last)",
        "        cut_to_pages(data, first, last)\n"
        "        origin = _named_pages(filename, first, last)",
    ),
    "the origin stops naming the pages, so the narrowing is invisible": (
        "planning/source_material.py",
        "        origin = _named_pages(filename, first, last)",
        "        origin = filename",
    ),
    "a page range the PDF does not have is accepted": (
        "planning/source_material.py",
        "    if first < 1 or last > total:",
        "    if False:",
    ),
    "a page range that runs backwards is accepted": (
        "planning/source_material.py",
        "    if first > last:",
        "    if False:",
    ),
    "SOFTENED: a selection past the model's page ceiling is sent anyway": (
        "planning/source_material.py",
        "    if wanted > MAX_PAGES_AT_ONCE:",
        "    if False:",
    ),
    "SOFTENED: the page ceiling is raised to the one a bigger model has": (
        "planning/source_material.py",
        "MAX_PAGES_AT_ONCE = 100",
        "MAX_PAGES_AT_ONCE = 600",
    ),
    "a scan nothing here can open is refused rather than sent whole": (
        "planning/source_material.py",
        "    try:\n"
        "        return len(PdfReader(io.BytesIO(data)).pages)\n"
        "    except Exception:",
        "    try:\n"
        "        return len(PdfReader(io.BytesIO(data)).pages)\n"
        "    except ZeroDivisionError:",
    ),
    "the page cut is made once at upload instead of on every rerun": (
        "source_panel.py",
        "    if st.session_state.get(came_from) != stamp:\n"
        "        # A PDF leaves the box empty. Once per file, because she may type\n"
        "        # alongside it and a rerun must not wipe what she typed.\n"
        "        st.session_state[box] = \"\"\n"
        "        st.session_state[came_from] = stamp",
        "    if st.session_state.get(came_from) == stamp:\n"
        "        return None\n"
        "    st.session_state[box] = \"\"\n"
        "    st.session_state[came_from] = stamp",
    ),
    "an uploaded PDF goes down the once-per-file path like a Word file": (
        "source_panel.py",
        "            if _is_a_pdf(upload.name):\n"
        "                unreadable = _take_the_pdf(upload, box, scan, came_from, namespace)\n"
        "            else:\n"
        "                unreadable = _take_the_upload(upload, box, scan, came_from)",
        "            unreadable = _take_the_upload(upload, box, scan, came_from)",
    ),
    "\U0001F6A8 LOOSE: the credit line the model invented is printed under her passage": (
        "planning/source_material.py",
        "    content = _without_the_invented_credit(content, where)",
        "    content = content",
    ),
    "the credit line is cleared by editing the reply she was handed": (
        "planning/source_material.py",
        "    without = copy.deepcopy(content)\n"
        "    without[section][THE_CREDIT_LINE] = \"\"\n"
        "    return without",
        "    block[THE_CREDIT_LINE] = \"\"\n"
        "    return content",
    ),
    "nothing says her choice moved when it is no longer offered": (
        "source_panel.py",
        "    if not before or before in offered:\n        return \"\"",
        "    if True:\n        return \"\"",
    ),
    "the moved-choice sentence is worked out and never shown": (
        "source_panel.py",
        "            st.info(moved)",
        "            pass",
    ),
    "a rerun empties the box she has been typing in beside the PDF": (
        "source_panel.py",
        "    if st.session_state.get(came_from) != stamp:",
        "    if True:",
    ),
    "a picker is offered on a file with one page in it": (
        "source_panel.py",
        "    if not total or total < 2:\n        return None",
        "    if not total:\n        return None",
    ),
    # ---- the two boxes: what pupils do, and what is getting in the way ----
    "two boxes: the task block is placed after the source law": (
        "llm/prompts.py",
        "        task_instructions(task) if task else \"\",\n"
        "        barrier_instructions(barriers),\n"
        "        closing,\n",
        "        barrier_instructions(barriers),\n"
        "        closing,\n"
        "        task_instructions(task) if task else \"\",\n",
    ),
    "two boxes: a task typed with no upload is dropped (the early return is back)": (
        "llm/prompts.py",
        "    opening = closing = \"\"\n",
        "    if source_material is None:\n        return base\n    opening = closing = \"\"\n",
    ),
    "two boxes: the task block no longer says the levels decide how much": (
        "llm/prompts.py",
        "- the DIFFERENTIATION LEVEL RULES above, which still decide how many questions there are, how",
        "- the rules above, which still decide how many questions there are, how",
    ),
    "two boxes: the barrier block contradicts the level rules on word meanings": (
        "llm/prompts.py",
        '"hard the thinking is. Where a line here asks for more support than those rules give, "\n'
        '    "the line here wins; nothing here may make the sheet harder."',
        '"hard the thinking is."',
    ),
    "SOFTENED: two boxes: an unknown barrier is sent instead of refused": (
        "llm/prompts.py",
        "    if unknown:\n        raise KeyError(f\"not a barrier this app asks about: {sorted(unknown)}\")\n    lines",
        "    lines",
    ),
    "two boxes: the barrier block follows the order she ticked in": (
        "llm/prompts.py",
        "[BARRIER_SENTENCES[key] for key in BARRIER_SENTENCES if key in ticked]",
        "[BARRIER_SENTENCES[key] for key in barriers]",
    ),
    "two boxes: writing a lot shrinks nothing": (
        "planning/support.py",
        "            space[\"lines\"] = max(1, math.ceil(space[\"lines\"] / 2))",
        "            space[\"lines\"] = space[\"lines\"]",
    ),
    "two boxes: writing a lot can leave no line at all": (
        "planning/support.py",
        "            space[\"lines\"] = max(1, math.ceil(space[\"lines\"] / 2))",
        "            space[\"lines\"] = space[\"lines\"] // 2",
    ),
    "two boxes: a barrier makes the sheet harder (more writing)": (
        "planning/support.py",
        "            space[\"lines\"] = max(1, math.ceil(space[\"lines\"] / 2))",
        "            space[\"lines\"] = space[\"lines\"] * 2",
    ),
    "two boxes: a third of the questions off, collapsing two levels into one": (
        "planning/support.py",
        "len(questions) - QUESTIONS_TAKEN_OFF)",
        "len(questions) - len(questions) // 3)",
    ),
    "SOFTENED: two boxes: writing a lot is claimed on sheets where nothing moves": (
        "planning/support.py",
        "        if worksheet_type in WRITING_SPACE:\n            return PRINTED,",
        "        if True:\n            return PRINTED,",
    ),
    "SOFTENED: two boxes: a barrier with nothing printed claims to be printed": (
        "planning/support.py",
        "        return ASKED, f\"Claude is asked to start sentences for them. {_NOT_CHECKED}\"",
        "        return PRINTED, \"sentence starters are printed.\"",
    ),
    "two boxes: decoding no longer turns the spacing on": (
        "planning/support.py",
        "    return (\"decoding\" in ticked, \"limited_english\" in ticked)",
        "    return (False, \"limited_english\" in ticked)",
    ),
    "two boxes: her reply is edited in place": (
        "planning/support.py",
        "    content = copy.deepcopy(content)\n",
        "",
    ),
    "two boxes: the meanings that came back are not counted": (
        "planning/support.py",
        "            sentence += _meanings_counted(content, worksheet_type)\n",
        "            pass\n",
    ),
    "SOFTENED: two boxes: a free-text box about the child is added to the barriers": (
        "support_panel.py",
        "    if not ticked:\n        return ()\n",
        "    st.text_area(\"Anything else? (optional)\", key=f\"{namespace}_barrier_note\")\n"
        "    if not ticked:\n        return ()\n",
    ),
    "two boxes: what is shown is a second copy, not what is sent": (
        "support_panel.py",
        "        st.code(barrier_instructions(ticked), language=None)",
        "        st.code(\"\\n\".join(BARRIERS[key] for key in ticked), language=None)",
    ),
    "two boxes: the screen stops saying what each sheet can carry": (
        "support_panel.py",
        "        st.caption(f\"**{BARRIERS[key]}** — {sentence}\")",
        "        pass",
    ),
    "two boxes: a pasted text in the task box is sent anyway": (
        "support_panel.py",
        "    if problem and len(task) > TASK_LIMIT:\n        st.warning(problem)\n        return \"\"",
        "    if problem and len(task) > TASK_LIMIT:\n        st.warning(problem)\n        return task",
    ),
    "two boxes: the objective and the task are not shown together": (
        "support_panel.py",
        "        st.info(f\"**Objective:** {objective}\\n\\n**They will:** {task}\")",
        "        pass",
    ),
    "two boxes: her task is not counted as something she supplied": (
        "app.py",
        "                    params.get('task') or '',\n",
        "",
    ),
    "two boxes: the barriers are worked out and the sheet printed without them": (
        "app.py",
        "            outcome = dataclasses.replace(outcome, content=support.content)\n",
        "",
    ),
    "two boxes: the documents are built without the barriers' print switches": (
        "app.py",
        "    extra_spacing = params['extra_spacing'] or barrier_spacing\n",
        "    extra_spacing = params['extra_spacing']\n",
    ),
    "two boxes: the documents are built without the glossary the barriers turn on": (
        "app.py",
        "    eal_glossary = params['eal_glossary'] or barrier_glossary\n",
        "    eal_glossary = params['eal_glossary']\n",
    ),
    "two boxes: the task is missing from what Regenerate replays": (
        "app.py",
        "            'task': task,\n",
        "",
    ),
    "two boxes: the task never reaches the prompt": (
        "app.py",
        "                task=params.get('task'),\n",
        "",
    ),
    "two boxes: the lesson page is silent about the boxes it ignores": (
        "pages/2_Lesson_Plans.py",
        "    st.caption(NOT_ON_THIS_PAGE)\n",
        "",
    ),
    # ---- the daily allowance ----
    "allowance: a press on the last worksheet of the day still makes all three": (
        "app.py",
        "    levels_to_generate, skipped = levels_within_allowance(levels_to_generate)\n",
        "    skipped = []\n",
    ),
    "allowance: the allowance is ignored inside the helper": (
        "access.py",
        "    return list(levels[:room]), list(levels[room:])",
        "    return list(levels), []",
    ),
    "allowance: the levels not made are never mentioned": (
        "app.py",
        "        st.warning(st.session_state.allowance_note)",
        "        pass",
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
    # An optional substring, so a guard just written can be proved in minutes
    # rather than in the two hours the whole file takes. ⚠️ A filtered run is a
    # measurement of the mutations it ran and of nothing else — the full run is
    # still the one that has to be clean before anything ships.
    only = sys.argv[1] if len(sys.argv) > 1 else None
    if only:
        print(f"only the mutations whose label or file contains {only!r}\n")

    unseen = []
    for label, (name, before, after) in MUTATIONS.items():
        if only and only.lower() not in f"{label} {name}".lower():
            continue
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
