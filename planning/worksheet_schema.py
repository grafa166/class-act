"""The shape of each kind of worksheet, sent with the request rather than asked for in it.

The lesson path was given a schema on 2026-09-03 and this one deliberately was
not, for a reason worth keeping: three of the four worksheet defects were the
coupling guard refusing correct work, because the same content legitimately
comes back in different shapes. A cloze passage arrives as `paragraphs`, a list
of lists of fragments; a word-bank sentence arrives as `pieces` with the gaps
between them. **One** closed schema across all ten types would not merely refuse
those — with `additionalProperties: false` it would make them impossible to
write, and there would be no artefact left to work out why.

Per type, that objection goes away. `paragraphs` is what a cloze sheet *is*, and
it does not have to be legal on a times-tables sheet. So there are ten schemas
here, each mirroring its own prompt in `llm/prompts.py` field for field, and
each checked in `tests/test_worksheet_schema.py` against content the generators
are already known to render — the fixtures for all ten types, and every raw
reply ever saved under `live-runs/`.

## What reading the artefacts changed

This was going to be about JSON validity, as it was for lessons. It is not.
Across every saved worksheet reply — 87 evidence claims — **six quoted text that
no generator prints.** Both investigation sheets on the 2026-09-03 11:51 run
answered all three of their criteria out of `sorting_section`, `job_section` and
`explanation_section`: keys the investigation prompt never asks for and the
investigation generator has never heard of. The coupling check passed them,
because the quotes really were in the reply. They were not on the worksheet.
The teacher would have been told the sheet evidenced her criteria and handed one
that evidenced none of them.

The same two replies are the only two of eight that dropped
`conclusion_prompts`, which is exactly where that writing would have gone. Told
to change the sheet rather than the criterion, the model added tasks — correctly
— and put them somewhere nothing would print them. `additionalProperties: false`
is what makes that unwritable, and it is why this file has teeth beyond parsing.

## The three rules these follow

**Each mirrors its own prompt, field for field.** A field the prompt asks for
and the schema omits cannot be returned at all, and the sheet comes back quietly
missing it. `test_every_field_the_prompt_asks_for_is_writable` derives both
sides rather than listing them, so a prompt that gains a field fails a test
instead of losing that field live.

**Each is constant.** The compiled grammar is cached for 24 hours and keyed on
the schema, so one built per sheet would pay the compile on every lesson of a
unit. That is also why the objective is not pinned with `const`, which was the
tempting version: `_check_the_objective` already refuses a drifted one, for free.

**Required means the generator would crash without it, and nothing more.**
Everything required here is either a field the coupling reads or a field a
generator reaches for with square brackets — the ones that raise. Every other
judgement stays in `llm/validation.py` and `planning/worksheet.py`, where a
shortfall becomes a sentence the teacher can read rather than a request the API
refuses before a worksheet exists. `success_criteria` is the deliberate case:
the sheet prints hers whatever comes back, a word-bank sheet dropped the field
on three live runs at no cost, and demanding it back would only give a reworded
one somewhere to come from.
"""

from llm.validation import REQUIRED_KEYS

# ── the pieces every schema is built from ───────────────────────────────────

_STRING = {"type": "string"}
_INTEGER = {"type": "integer"}
_STRINGS = {"type": "array", "items": _STRING}

# Nullable, not absent. The prompts ask for a literal null in places -- a cloze
# section with no reminder, an investigation at expected level with no
# prediction choices -- and the model writes one. A schema that only allowed the
# key to be missing would refuse the exact shape the prompt requested.
_MAYBE_STRING = {"anyOf": [_STRING, {"type": "null"}]}
_MAYBE_STRINGS = {"anyOf": [_STRINGS, {"type": "null"}]}


def _object(properties, required=()):
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(required),
    }


def _array_of(item, at_least_one=False):
    array = {"type": "array", "items": item}
    if at_least_one:
        # Supported for 0 and 1 only. "At least two" is not something a schema
        # can say here, so anything of that kind stays in the validator.
        array["minItems"] = 1
    return array


def _maybe(node):
    return {"anyOf": [node, {"type": "null"}]}


# ── what the coupling reads ─────────────────────────────────────────────────

# One claim per criterion: where on the sheet it is evidenced, the words printed
# there, and what the child leaves behind. All four are read by
# `_check_the_evidence`, and a sheet without this array is refused outright --
# so it is required here, where it costs nothing, rather than discovered after
# a whole worksheet has been written.
_EVIDENCE = _array_of(
    _object(
        {
            "criterion": _STRING,
            "where": _STRING,
            "quote": _STRING,
            "pupil_writes": _STRING,
        },
        ("criterion", "where", "quote", "pupil_writes"),
    ),
    at_least_one=True,
)

_COUPLING = {
    "objective": _STRING,
    "success_criteria": _STRINGS,
    "evidence": _EVIDENCE,
}


# ── shapes shared between types ─────────────────────────────────────────────

# A fragment of a sentence with a gap in it. The same shape carries a cloze
# passage (`sections[].paragraphs[][]`) and a word-bank sentence
# (`activities[].sentences[].pieces[]`) -- both of which the coupling guard was
# taught to read after they were refused live on 2026-09-02.
#
# `type` is required and closed to the two values `add_cloze_paragraph` knows.
# It reads `piece['type']` with brackets, and renders nothing at all for a third
# value -- so a sheet with an invented piece type loses that text silently. The
# rest are optional because a text piece and a blank carry different ones, and
# `choices` is only there at developing level.
_PIECE = _object(
    {
        "type": {"type": "string", "enum": ["text", "blank"]},
        "text": _STRING,
        "word_type": _STRING,
        "answer": _STRING,
        "hint": _MAYBE_STRING,
        "choices": _MAYBE_STRINGS,
    },
    ("type",),
)

# A labelled group of vocabulary. `definition` is developing-level only and the
# prompt says to omit the key entirely otherwise, so it must not be required.
_WORD_GROUP = _object(
    {
        "word_type": _STRING,
        "label": _STRING,
        "words": _array_of(
            _object({"word": _STRING, "definition": _MAYBE_STRING}, ("word",))
        ),
    },
    ("word_type", "label", "words"),
)

# The question shape shared by reading comprehension and problem solving.
_QUESTION = _object(
    {
        "number": _INTEGER,
        "question": _STRING,
        "question_type": _STRING,
        "marks": _INTEGER,
        "lines": _INTEGER,
        "answer": _STRING,
        "word_bank": _MAYBE_STRINGS,
    },
    ("question",),
)


# ── the ten ─────────────────────────────────────────────────────────────────

_CLOZE = {
    "title": _STRING,
    # `reminder` is required and nullable rather than optional: the generator
    # reads `section['reminder']` with brackets and would raise on a section
    # that left it out, while the prompt explicitly asks for a null when there
    # is nothing to say.
    "sections": _array_of(
        _object(
            {
                "title": _STRING,
                "reminder": _MAYBE_STRING,
                "paragraphs": _array_of(_array_of(_PIECE)),
            },
            ("title", "reminder", "paragraphs"),
        )
    ),
    "word_bank": _array_of(_WORD_GROUP),
}

_WORD_BANK = {
    "title": _STRING,
    "categories": _array_of(_WORD_GROUP),
    "activities": _array_of(
        _object(
            {
                "title": _STRING,
                "instructions": _STRING,
                "sentences": _array_of(_object({"pieces": _array_of(_PIECE)}, ("pieces",))),
            },
            ("title", "instructions", "sentences"),
        )
    ),
}

_MATCHING = {
    "title": _STRING,
    "activities": _array_of(
        _object(
            {
                "title": _STRING,
                "instructions": _STRING,
                "pairs": _array_of(_object({"left": _STRING, "right": _STRING}, ("left", "right"))),
            },
            ("title", "instructions", "pairs"),
        )
    ),
    "bonus_activity": _maybe(
        _object(
            {"title": _STRING, "instructions": _STRING, "lines": _INTEGER},
            ("title", "instructions"),
        )
    ),
}

_INVESTIGATION = {
    "title": _STRING,
    "investigation": _object(
        {
            "question": _STRING,
            "prediction": _STRING,
            "prediction_choices": _MAYBE_STRINGS,
            "variables": _object(
                {"change": _STRING, "measure": _STRING, "keep_same": _STRINGS},
                ("change", "measure", "keep_same"),
            ),
        },
        ("question", "prediction", "variables"),
    ),
    "equipment": _STRINGS,
    "method": _STRINGS,
    "results_table": _object(
        {"columns": _STRINGS, "rows": _INTEGER, "units": _STRINGS}, ("columns",)
    ),
    # The one place on this sheet a child writes in prose, and the field the
    # ghost sections were standing in for: the two replies that invented
    # unprintable sections are the same two -- of eight -- that dropped this.
    #
    # Deliberately *not* required, which is the rule this file follows
    # everywhere: required is what a generator would crash without. Whether the
    # sheet leaves anywhere to write is not a shape question, and the evidence
    # check answers it properly -- a criterion evidenced nowhere printable is
    # refused there, with a reason the model can act on. What this line does is
    # make sure the field exists to be written into, now that inventing one is
    # not an option.
    "conclusion_prompts": _array_of(_STRING, at_least_one=True),
}

_SENTENCE_BUILDER = {
    "title": _STRING,
    "exercises": _array_of(
        _object(
            {
                "title": _STRING,
                "instructions": _STRING,
                "sentence_parts": _array_of(
                    _object({"part": _STRING, "word_type": _STRING}, ("part",))
                ),
                "correct_sentence": _STRING,
            },
            ("title", "instructions", "sentence_parts"),
        )
    ),
    "extension": _maybe(
        _object(
            {"title": _STRING, "instructions": _STRING, "lines": _INTEGER},
            ("title", "instructions"),
        )
    ),
}

_READING_COMPREHENSION = {
    "title": _STRING,
    "passage": _object(
        {"title": _STRING, "text": _STRING, "source_note": _MAYBE_STRING},
        ("title", "text"),
    ),
    "vocabulary": _array_of(
        _object(
            {"word": _STRING, "definition": _STRING, "word_type": _STRING},
            ("word", "definition"),
        )
    ),
    "questions": _array_of(_QUESTION),
}

_PROBLEM_SOLVING = {
    "title": _STRING,
    "scenario": _maybe(
        _object(
            {
                "title": _STRING,
                "text": _STRING,
                "data": _array_of(
                    _object({"label": _STRING, "value": _STRING}, ("label", "value"))
                ),
            },
            ("title", "text"),
        )
    ),
    "questions": _array_of(_QUESTION),
}

_CALCULATION_PRACTICE = {
    "title": _STRING,
    "sections": _array_of(
        _object(
            {
                "title": _STRING,
                "instructions": _STRING,
                "calculations": _array_of(
                    # All three read with brackets. `working_hint` is a hint at
                    # developing level and a null elsewhere, so it is required
                    # and nullable rather than optional.
                    _object(
                        {
                            "question": _STRING,
                            "answer": _STRING,
                            "working_hint": _MAYBE_STRING,
                        },
                        ("question", "answer", "working_hint"),
                    )
                ),
            },
            ("title", "instructions", "calculations"),
        )
    ),
    "challenge": _maybe(
        _object(
            {"title": _STRING, "instructions": _STRING, "lines": _INTEGER},
            ("title", "instructions"),
        )
    ),
}

_FRACTION_PRACTICE = {
    "title": _STRING,
    "sections": _array_of(
        _object(
            {
                "title": _STRING,
                "instructions": _STRING,
                "type": _STRING,
                "exercises": _array_of(
                    _object(
                        {
                            "question": _STRING,
                            "answer": _STRING,
                            "visual_hint": _MAYBE_STRING,
                            "diagram": _maybe(
                                _object(
                                    {"shaded": _INTEGER, "total": _INTEGER},
                                    ("shaded", "total"),
                                )
                            ),
                        },
                        ("question", "answer"),
                    )
                ),
            },
            ("title", "instructions"),
        )
    ),
    "challenge": _maybe(
        _object(
            {"title": _STRING, "instructions": _STRING, "lines": _INTEGER},
            ("title", "instructions"),
        )
    ),
}

_FACT = _object({"question": _STRING, "answer": _STRING}, ("question", "answer"))

_TIMES_TABLES = {
    "title": _STRING,
    "sections": _array_of(
        _object(
            {
                "title": _STRING,
                "instructions": _STRING,
                "tables_focus": _STRING,
                "facts": _array_of(_FACT),
            },
            ("title", "instructions", "facts"),
        )
    ),
    "speed_challenge": _maybe(
        _object(
            {
                "title": _STRING,
                "instructions": _STRING,
                "time_limit_seconds": _INTEGER,
                "facts": _array_of(_FACT),
            },
            ("title", "instructions", "time_limit_seconds"),
        )
    ),
}


_SHAPES = {
    "cloze": _CLOZE,
    "word_bank": _WORD_BANK,
    "matching": _MATCHING,
    "investigation": _INVESTIGATION,
    "sentence_builder": _SENTENCE_BUILDER,
    "reading_comprehension": _READING_COMPREHENSION,
    "problem_solving": _PROBLEM_SOLVING,
    "calculation_practice": _CALCULATION_PRACTICE,
    "fraction_practice": _FRACTION_PRACTICE,
    "times_tables": _TIMES_TABLES,
}


# The top-level keys each generator actually puts on the page.
#
# Not the same list as `_SHAPES` and not the same as `REQUIRED_KEYS`: this is
# what survives as far as the document, which is the only test of whether a
# child ever sees it. `planning/worksheet.py` searches these and nothing else
# when it checks that a quoted instruction is really on the sheet --
# `tests/test_worksheet_coupling.py` re-derives them from the generator source
# so the two cannot drift apart.
RENDERED_KEYS = {
    "cloze": {"title", "sections", "word_bank", "success_criteria"},
    "word_bank": {"title", "categories", "activities", "success_criteria"},
    "matching": {"title", "activities", "bonus_activity", "success_criteria"},
    "investigation": {
        "title",
        "investigation",
        "equipment",
        "method",
        "results_table",
        "conclusion_prompts",
        "success_criteria",
    },
    "sentence_builder": {"title", "exercises", "extension", "success_criteria"},
    "reading_comprehension": {
        "title",
        "passage",
        "vocabulary",
        "questions",
        "success_criteria",
    },
    "problem_solving": {"title", "scenario", "questions", "success_criteria"},
    "calculation_practice": {"title", "sections", "challenge", "success_criteria"},
    "fraction_practice": {"title", "sections", "challenge", "success_criteria"},
    "times_tables": {"title", "sections", "speed_challenge", "success_criteria"},
}


def _schema_for(worksheet_type, shape):
    """One type's shape, plus the three fields that make it a lesson's sheet.

    Required is the coupling's two, plus whatever the generator cannot run
    without -- `REQUIRED_KEYS`, less `success_criteria`, which by the time a
    generator sees it has been filled in from the lesson regardless of what came
    back.
    """
    needed = set(REQUIRED_KEYS.get(worksheet_type, ())) - {"success_criteria"}
    return _object(
        {**shape, **_COUPLING},
        sorted(needed | {"objective", "evidence"}),
    )


WORKSHEET_SCHEMAS = {
    worksheet_type: _schema_for(worksheet_type, shape)
    for worksheet_type, shape in _SHAPES.items()
}


def get_worksheet_schema(worksheet_type):
    """The schema for this kind of worksheet, or None if there isn't one.

    None means the reply goes out unconstrained, which is exactly how the whole
    worksheet path worked until now — so a type this map has never heard of
    still produces a worksheet. Blocking one over a missing map entry would be
    this repo's own most expensive failure, four times over.
    """
    return WORKSHEET_SCHEMAS.get(worksheet_type)
