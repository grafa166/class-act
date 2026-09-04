"""One schema per worksheet type, and the reason there is not just one.

The lesson path got its schema on 2026-09-03 and the worksheet path deliberately
did not. The reason is in the handover: three of the four worksheet defects were
the guard refusing correct work because the same content legitimately comes back
in different shapes — a cloze passage as `paragraphs`, a word-bank sentence as
`pieces` with the gaps between them. A *single* closed schema would not merely
refuse those shapes; with `additionalProperties: false` it would make them
impossible to write, and there would be no artefact left to diagnose from.

Per type, that objection does not apply: `paragraphs` is what a cloze sheet is,
`pieces` is what a word-bank sentence is, and neither has to be legal on the
other. What survives from the warning is the discipline, and it is the whole of
this file: **every schema is checked against content the generators are already
known to render** — `tests/fixtures.py` for all ten types, and, on a machine
that has them, every raw reply ever saved under `live-runs/`. A schema that
refuses one of those is a schema that would have made a working worksheet
impossible, and it fails here rather than live.

The second thing this file pins is the reason the schemas are worth having at
all, which reading the artefacts changed. It was going to be JSON validity, as
it was for lessons. It is not: across every saved worksheet reply, **six of
eighty-seven evidence claims quoted text that no generator prints.** Both
investigation sheets on the 11:51 run answered all three of their criteria out
of `sorting_section`, `job_section` and `explanation_section` — keys the
investigation prompt never asks for and the investigation generator has never
heard of. The coupling check said the sheet evidenced her criteria; the sheet
the child would have been handed contained none of it. The same two replies are
the only two that dropped `conclusion_prompts`, which is where that writing
would have gone. `additionalProperties: false`, per type, is what makes that
unwritable.
"""

import json
import os
import re
from glob import glob

import jsonschema
import pytest

from llm.prompts import get_prompt
from llm.validation import REQUIRED_KEYS
from planning.worksheet_schema import (
    RENDERED_KEYS,
    WORKSHEET_SCHEMAS,
    get_worksheet_schema,
)
from tests.fixtures import ALL_CONTENT

TYPES = sorted(REQUIRED_KEYS)

# Constraints structured outputs does not support. A schema carrying one is not
# refused politely — it is refused by the API, on the request, with the
# worksheet already half paid for. `minItems` is the exception and only for 0
# and 1; anything higher is not supported, so "at least two steps" cannot be
# said here and stays in the validator where it can be said properly.
UNSUPPORTED = ("maxItems", "minimum", "maximum", "multipleOf", "minLength", "maxLength")


def _walk(node, path="root"):
    """Every dict in the schema, with the path that reached it."""
    if isinstance(node, dict):
        yield path, node
        for key, value in node.items():
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, f"{path}[{index}]")


def _property_names(schema):
    return {
        name
        for _, node in _walk(schema)
        if node.get("type") == "object"
        for name in node.get("properties", {})
    }


def _saved_replies():
    """Every worksheet reply ever written to live-runs/, with its type.

    Local only — `live-runs/` is gitignored, because a saved reply carries a
    whole unit of a real teacher's content. Where it exists it is the best
    fixture there is, because nobody wrote it to make a test pass.
    """
    kinds = {
        "word bank": "word_bank",
        "cloze": "cloze",
        "matching": "matching",
        "investigation": "investigation",
        "sentence building": "sentence_builder",
        "reading comprehension": "reading_comprehension",
        "problem solving": "problem_solving",
        "calculation practice": "calculation_practice",
        "fraction practice": "fraction_practice",
        "times tables": "times_tables",
    }
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for request_file in sorted(glob(os.path.join(here, "live-runs", "*", "*-request.txt"))):
        request = open(request_file, encoding="utf-8").read()
        if "worksheet for Year" not in request[:300]:
            continue
        worksheet_type = next(
            (v for k, v in kinds.items() if k in request[:200]), None
        )
        reply_file = request_file.replace("-request.txt", "-reply.txt")
        if worksheet_type is None or not os.path.exists(reply_file):
            continue
        text = open(reply_file, encoding="utf-8").read().strip()
        fenced = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.S)
        if fenced:
            text = fenced.group(1)
        try:
            yield os.path.basename(os.path.dirname(request_file)), worksheet_type, json.loads(text)
        except json.JSONDecodeError:
            continue


SAVED = list(_saved_replies())


class TestEveryTypeHasOne:
    def test_every_worksheet_type_has_a_schema(self):
        assert set(WORKSHEET_SCHEMAS) == set(TYPES), (
            "A type with no schema is a type whose reply is still unconstrained."
        )

    def test_an_unknown_type_gets_no_schema_rather_than_an_error(self):
        """A type the map has never heard of is a programming mistake, not bad
        model output. It goes out unconstrained, exactly as the whole path did
        yesterday — blocking a worksheet over a missing map entry would be this
        repo's own favourite failure."""
        assert get_worksheet_schema("a_type_that_does_not_exist") is None

    @pytest.mark.parametrize("worksheet_type", TYPES)
    def test_the_schema_is_the_same_object_every_time(self, worksheet_type):
        """The compiled grammar is cached for 24 hours and keyed on the schema.
        One built per sheet would pay the compile on every lesson of a unit."""
        assert get_worksheet_schema(worksheet_type) == get_worksheet_schema(
            worksheet_type
        )


class TestItDoesNotForbidWorkThatWorks:
    """The control. Every one of these is content the generators render."""

    @pytest.mark.parametrize("worksheet_type", TYPES)
    def test_the_fixture_for_every_type_satisfies_its_schema(self, worksheet_type):
        content = dict(ALL_CONTENT[worksheet_type])
        content["objective"] = "I can describe two rocks using property words."
        content["evidence"] = [
            {
                "criterion": "I can describe two rocks using property words.",
                "where": "Task 1",
                "quote": "Describe each rock using two property words.",
                "pupil_writes": "two property words for each rock",
            }
        ]
        jsonschema.validate(content, get_worksheet_schema(worksheet_type))

    @pytest.mark.skipif(not SAVED, reason="no live-runs/ on this machine")
    @pytest.mark.parametrize("run,worksheet_type,reply", SAVED)
    def test_every_saved_reply_satisfies_its_schema(self, run, worksheet_type, reply):
        """Read off the artefacts, not imagined. The one thing allowed to fail
        this is a key no generator prints — that is the defect being closed, and
        it has its own test below."""
        printable = {
            key: value
            for key, value in reply.items()
            if key in RENDERED_KEYS[worksheet_type] or key in ("objective", "evidence")
        }
        jsonschema.validate(printable, get_worksheet_schema(worksheet_type))


class TestItForbidsTheThingThatWentWrong:
    def test_a_section_no_generator_prints_cannot_be_written(self):
        """Measured, twice, on 2026-09-03: an investigation sheet answered all
        three criteria out of `sorting_section`, `job_section` and
        `explanation_section`. The coupling check passed. Nothing in those keys
        reaches the document, so the child's sheet evidenced nothing at all."""
        sheet = dict(ALL_CONTENT["investigation"])
        sheet["objective"] = "I can group rocks by their properties."
        sheet["evidence"] = []
        sheet["sorting_section"] = {
            "task": "Sort your rocks into groups.",
            "instruction": "Put rocks that are similar together.",
            "grouping_space": "___",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sheet, get_worksheet_schema("investigation"))

    @pytest.mark.parametrize("worksheet_type", TYPES)
    def test_a_sheet_with_no_evidence_at_all_is_not_a_shape_that_can_come_back(
        self, worksheet_type
    ):
        """A missing evidence array is refused by the coupling check anyway.
        Requiring it in the schema means it is not written that way to begin
        with, which costs a whole worksheet less."""
        sheet = dict(ALL_CONTENT[worksheet_type])
        sheet["objective"] = "I can describe two rocks using property words."
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sheet, get_worksheet_schema(worksheet_type))


class TestTheSchemaAndThePromptAgree:
    """Drift between them is how this breaks quietly.

    `additionalProperties: false` means a field the prompt asks for and the
    schema omits cannot be written at all — the sheet comes back missing it and
    nothing says why. Both directions are derived rather than listed, so a
    prompt that gains a field fails here instead of losing it live.
    """

    @pytest.mark.parametrize("worksheet_type", TYPES)
    def test_every_field_the_prompt_asks_for_is_writable(self, worksheet_type):
        prompt = get_prompt(
            worksheet_type=worksheet_type,
            year_group="Year 3",
            topic="Rocks",
            objective="I can describe two rocks using property words.",
            age_range="7-8",
            theme_name="Space Explorer",
            theme_icon="\U0001F680",
            level="expected",
            subject="Science",
        )
        shape = re.search(r"(\{\n(?:.|\n)*?\n\})\s*\n\nCRITICAL|(\{\n(?:.|\n)*?\n\})", prompt)
        asked = set(re.findall(r'"([a-z_]+)":', shape.group(0))) if shape else set()
        allowed = _property_names(get_worksheet_schema(worksheet_type))
        missing = sorted(asked - allowed)
        assert not missing, (
            f"The {worksheet_type} prompt asks for {missing} and the schema has "
            f"no room for them, so they cannot be returned at all."
        )

    @pytest.mark.parametrize("worksheet_type", TYPES)
    def test_every_key_the_generator_prints_is_writable(self, worksheet_type):
        allowed = _property_names(get_worksheet_schema(worksheet_type))
        missing = sorted(RENDERED_KEYS[worksheet_type] - allowed)
        assert not missing, (
            f"The {worksheet_type} generator prints {missing}, and the schema "
            f"forbids it. The sheet would render those parts blank."
        )

    @pytest.mark.parametrize("worksheet_type", TYPES)
    def test_the_generator_would_not_crash_on_what_the_schema_requires(
        self, worksheet_type
    ):
        """The schema requires what the coupling needs and what the generator
        cannot run without. Anything beyond that stays in `validate_worksheet_
        content`, where a shortfall gets a sentence the teacher can read rather
        than a request the API refuses."""
        required = set(get_worksheet_schema(worksheet_type).get("required", []))
        assert {"objective", "evidence"} <= required
        assert set(REQUIRED_KEYS[worksheet_type]) - {"success_criteria"} <= required

    @pytest.mark.parametrize("worksheet_type", TYPES)
    def test_the_criteria_she_approved_are_not_demanded_back(self, worksheet_type):
        """`success_criteria` is deliberately optional, and this is not an
        oversight. The sheet prints hers whatever comes back, and a word-bank
        sheet dropped the field on three live runs with no cost. Demanding it
        would make the model write them out again — and a criterion written out
        again is a criterion that can come back reworded, which the coupling
        check refuses. Requiring the field would buy nothing and lose sheets."""
        required = set(get_worksheet_schema(worksheet_type).get("required", []))
        assert "success_criteria" not in required
        assert "success_criteria" in _property_names(get_worksheet_schema(worksheet_type))


class TestTheSchemasAreLegalStructuredOutputs:
    """A schema the API rejects fails on the request, after the prompt is built
    and before any worksheet exists. These are the rules it is judged by."""

    @pytest.mark.parametrize("worksheet_type", TYPES)
    def test_every_object_closes_its_shape(self, worksheet_type):
        open_objects = [
            path
            for path, node in _walk(get_worksheet_schema(worksheet_type))
            if node.get("type") == "object"
            and node.get("additionalProperties", None) is not False
        ]
        assert not open_objects, (
            f"These objects do not set additionalProperties: false — {open_objects}"
        )

    @pytest.mark.parametrize("worksheet_type", TYPES)
    def test_no_schema_carries_a_constraint_the_api_does_not_support(
        self, worksheet_type
    ):
        found = [
            f"{path}.{key}"
            for path, node in _walk(get_worksheet_schema(worksheet_type))
            for key in node
            if key in UNSUPPORTED
        ]
        assert not found, f"Unsupported by structured outputs: {found}"

    @pytest.mark.parametrize("worksheet_type", TYPES)
    def test_min_items_is_never_more_than_one(self, worksheet_type):
        """Supported for 0 and 1 only. Two is not a bound this can express, so
        "at least two of anything" belongs in the validator instead."""
        over = [
            path
            for path, node in _walk(get_worksheet_schema(worksheet_type))
            if isinstance(node.get("minItems"), int) and node["minItems"] > 1
        ]
        assert not over, f"minItems above 1 is not supported: {over}"

    @pytest.mark.parametrize("worksheet_type", TYPES)
    def test_everything_required_is_a_property_that_exists(self, worksheet_type):
        broken = [
            f"{path}: {sorted(set(node['required']) - set(node.get('properties', {})))}"
            for path, node in _walk(get_worksheet_schema(worksheet_type))
            if node.get("type") == "object"
            and set(node.get("required", [])) - set(node.get("properties", {}))
        ]
        assert not broken, f"Required fields with no property to match: {broken}"


class TestTheCouplingFieldsSurvive:
    @pytest.mark.parametrize("worksheet_type", TYPES)
    def test_every_schema_can_carry_the_evidence_the_check_reads(self, worksheet_type):
        schema = get_worksheet_schema(worksheet_type)
        entry = schema["properties"]["evidence"]["items"]
        assert set(entry["properties"]) == {
            "criterion",
            "where",
            "quote",
            "pupil_writes",
        }
        assert set(entry["required"]) == {"criterion", "where", "quote", "pupil_writes"}

    @pytest.mark.parametrize("worksheet_type", TYPES)
    def test_the_objective_is_not_pinned_by_the_schema(self, worksheet_type):
        """`const` would pin it to the lesson's wording — and rebuild the schema
        per lesson, paying the grammar compile on every call to re-buy a
        guarantee `_check_the_objective` already gives for free."""
        objective = get_worksheet_schema(worksheet_type)["properties"]["objective"]
        assert "const" not in objective and "enum" not in objective
