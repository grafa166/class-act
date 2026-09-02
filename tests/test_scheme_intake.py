"""Reading the plan the teacher has to follow.

Boost's long- and medium-term plans exist and must be followed, but they are
too thin to teach from. So the tool takes them as a constraint: the coverage
and order are kept because she is accountable for them, and the teaching is
rebuilt.

She should not have to retype any of it. Three ways in -- paste the text,
upload the file the subject leader circulated, or photograph the printed page,
because a photocopy in a folder is the realistic case. PDFs and photographs go
to Claude as document and image blocks rather than through a text extractor:
a scanned or photographed plan has no text layer for a parser to find.

None of these tests touch the network.
"""

import base64

import pytest

from planning.scheme_intake import (
    MAX_UPLOAD_BYTES,
    SchemePlan,
    SchemePlanError,
    UnreadableUploadError,
    blocks_for_upload,
    build_extraction_prompt,
    vague_coverage_items,
    validate_scheme_plan,
)

GOOD = {
    "unit_title": "Rocks and Soils",
    "coverage": [
        "types of rock",
        "properties",
        "fossils",
        "soil formation",
    ],
    "assessment": ["children know that rocks have different properties"],
    "activities": ["rock sorting", "fossil worksheet", "soil jar"],
}


class TestReadingUploads:
    def test_a_pdf_becomes_a_document_block(self):
        """Not text-extracted. A photocopied plan has no text layer."""
        blocks = blocks_for_upload("plan.pdf", b"%PDF-1.4 fake")
        assert blocks[0]["type"] == "document"
        assert blocks[0]["source"]["media_type"] == "application/pdf"

    def test_a_photograph_becomes_an_image_block(self):
        blocks = blocks_for_upload("plan.jpg", b"\xff\xd8\xff fake jpeg")
        assert blocks[0]["type"] == "image"
        assert blocks[0]["source"]["media_type"] == "image/jpeg"

    def test_png_is_recognised_separately_from_jpeg(self):
        blocks = blocks_for_upload("plan.png", b"\x89PNG fake")
        assert blocks[0]["source"]["media_type"] == "image/png"

    def test_base64_carries_no_newlines(self):
        """The API rejects wrapped base64, and b64encode is not the trap --
        textwrap-style wrapping added by a helper is."""
        blocks = blocks_for_upload("plan.pdf", b"x" * 500)
        assert "\n" not in blocks[0]["source"]["data"]

    def test_the_payload_round_trips(self):
        raw = b"some bytes that must survive"
        blocks = blocks_for_upload("plan.pdf", raw)
        assert base64.b64decode(blocks[0]["source"]["data"]) == raw

    def test_plain_text_is_passed_through_as_text(self):
        blocks = blocks_for_upload("plan.txt", "Rocks and Soils\nCoverage: ...".encode())
        assert blocks[0]["type"] == "text"
        assert "Rocks and Soils" in blocks[0]["text"]

    def test_an_unsupported_type_is_refused_by_name(self):
        with pytest.raises(UnreadableUploadError, match="xlsx"):
            blocks_for_upload("plan.xlsx", b"...")

    def test_an_oversized_upload_is_refused_before_it_is_encoded(self):
        with pytest.raises(UnreadableUploadError, match="too large"):
            blocks_for_upload("plan.pdf", b"x" * (MAX_UPLOAD_BYTES + 1))

    def test_an_empty_upload_is_refused(self):
        with pytest.raises(UnreadableUploadError):
            blocks_for_upload("plan.pdf", b"")

    def test_extension_matching_ignores_case(self):
        assert blocks_for_upload("PLAN.PDF", b"%PDF")[0]["type"] == "document"


class TestExtractionPrompt:
    def _prompt(self, **kw):
        return build_extraction_prompt(
            scheme="Boost", subject="Science", year_group="Year 3", **kw
        )

    def test_it_names_the_scheme_and_year(self):
        p = self._prompt()
        assert "Boost" in p and "Year 3" in p and "Science" in p

    def test_it_forbids_inventing_coverage(self):
        """The whole point is fidelity to what the school agreed to teach."""
        low = self._prompt().lower()
        assert "do not invent" in low or "only what" in low

    def test_it_asks_for_the_vague_items_to_be_flagged(self):
        assert "vague" in self._prompt().lower()

    def test_it_requests_json_only(self):
        assert "json" in self._prompt().lower()


class TestValidation:
    def test_a_good_payload_becomes_a_scheme_plan(self):
        plan = validate_scheme_plan(GOOD)
        assert isinstance(plan, SchemePlan)
        assert plan.unit_title == "Rocks and Soils"
        assert len(plan.coverage) == 4

    def test_coverage_may_not_be_empty(self):
        """No coverage means nothing to be accountable to -- reject it."""
        with pytest.raises(SchemePlanError, match="coverage"):
            validate_scheme_plan({**GOOD, "coverage": []})

    def test_a_missing_unit_title_is_rejected(self):
        with pytest.raises(SchemePlanError):
            validate_scheme_plan({**GOOD, "unit_title": "   "})

    def test_coverage_must_be_strings_not_nested_objects(self):
        with pytest.raises(SchemePlanError):
            validate_scheme_plan({**GOOD, "coverage": [{"item": "rocks"}]})

    def test_a_non_dict_payload_is_rejected(self):
        with pytest.raises(SchemePlanError):
            validate_scheme_plan(["rocks"])

    def test_assessment_and_activities_are_optional(self):
        plan = validate_scheme_plan(
            {"unit_title": "Rocks", "coverage": ["types of rock"]}
        )
        assert plan.assessment == [] and plan.activities == []

    def test_blank_coverage_entries_are_dropped_not_kept(self):
        plan = validate_scheme_plan({**GOOD, "coverage": ["rocks", "  ", ""]})
        assert plan.coverage == ["rocks"]

    def test_dropping_blanks_cannot_empty_the_coverage_silently(self):
        with pytest.raises(SchemePlanError):
            validate_scheme_plan({**GOOD, "coverage": ["  ", ""]})


class TestVagueness:
    def test_a_statement_with_no_verb_for_the_child_is_flagged(self):
        """'Children know that rocks have different properties' is a statement,
        not an objective -- nothing in it says what a child would do."""
        flagged = vague_coverage_items(["children know that rocks have properties"])
        assert flagged

    def test_a_bare_topic_label_is_flagged(self):
        assert vague_coverage_items(["properties"])

    def test_a_teachable_objective_is_not_flagged(self):
        assert not vague_coverage_items(
            ["compare and group rocks by their physical properties"]
        )

    def test_flagging_explains_itself(self):
        """A flag the teacher cannot argue with is worse than no flag."""
        (item, reason), = vague_coverage_items(["properties"])
        assert item == "properties"
        assert reason.strip()

    def test_it_is_a_hint_not_a_verdict(self):
        """Documented behaviour: nothing here rejects a unit. The teacher
        decides -- this only surfaces what to look at."""
        assert isinstance(vague_coverage_items(["properties"]), list)
