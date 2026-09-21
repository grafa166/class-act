"""Cutting an uploaded PDF to the pages the children have reached.

She reveals a text gradually across lessons: *"I reveal the text gradually
across lessons and only want the planner to use what the children have reached
so far."* Today the whole file goes to Claude, and a scan is the one route where
the name check cannot run — so a chapter uploaded for lesson two can be drawn on
for lesson six and nothing would catch it.

🚨 **The cut is structural, and that is the whole point.** It is not a sentence
in the prompt asking the model to use only pages 4 to 6; the other pages never
leave this machine. So every test here reads the produced PDF *back* and asks
which pages are in it. Counting bytes, or counting pages alone, would pass a cut
that took the wrong three pages — and a fixture that does not contain the thing
being varied measures nothing, which is the mistake this repo has made twice.
Every page of the fixture therefore says which page it is.
"""

import base64
import io

import pytest
from pypdf import PdfReader

from planning.source_material import (
    MAX_PAGES_AT_ONCE,
    SourceMaterialError,
    cut_to_pages,
    pages_in,
    read_upload,
)


def a_pdf_of(*texts):
    """A real PDF, one line of text per page, saying which page it is.

    Hand-built rather than drawn with a library: it keeps the tests free of a
    second dependency, and every page carries a distinguishing word, which is
    the property the cut has to be measured against.
    """
    count = len(texts)
    page_ids = [3 + 2 * i for i in range(count)]
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids ["
        + b" ".join(b"%d 0 R" % i for i in page_ids)
        + b"] /Count %d >>" % count,
    ]
    for index, text in enumerate(texts):
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
            b"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 "
            b"/BaseFont /Helvetica >> >> >> /Contents %d 0 R >>"
            % (page_ids[index] + 1)
        )
        stream = b"BT /F1 18 Tf 20 150 Td (" + text.encode("ascii") + b") Tj ET"
        objects.append(
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
        )

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"

    start = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (len(objects) + 1)
    out += b"startxref\n%d\n%%%%EOF\n" % start
    return bytes(out)


def pages_of(data):
    """What each page of a PDF says, in order."""
    return [page.extract_text().strip() for page in PdfReader(io.BytesIO(data)).pages]


A_CHAPTER = a_pdf_of(
    "PAGE ONE", "PAGE TWO", "PAGE THREE", "PAGE FOUR", "PAGE FIVE", "PAGE SIX"
)


class TestTheFixtureItself:
    """The control. Every assertion below is about which pages survived a cut,
    and that means nothing unless the pages were telling apart to begin with."""

    def test_the_fixture_is_a_pdf_with_six_distinguishable_pages(self):
        assert pages_of(A_CHAPTER) == [
            "PAGE ONE", "PAGE TWO", "PAGE THREE", "PAGE FOUR", "PAGE FIVE", "PAGE SIX"
        ]


class TestHowManyPagesThereAreToChooseBetween:
    def test_a_pdf_says_how_many_pages_it_has(self):
        assert pages_in("chapter-1.pdf", A_CHAPTER) == 6

    def test_a_one_page_pdf_says_one(self):
        """One page is a number, not a refusal — the panel is what decides
        there is nothing to choose between, and it needs to be told which."""
        assert pages_in("worksheet.pdf", a_pdf_of("ONLY PAGE")) == 1

    def test_a_photograph_has_no_pages_to_choose_between(self):
        assert pages_in("page.jpg", b"\xff\xd8\xff\xe0 not really a photo") is None

    def test_a_word_document_has_no_pages_to_choose_between(self):
        assert pages_in("plan.docx", b"PK\x03\x04 not really a document") is None

    def test_a_pdf_nothing_here_can_open_offers_no_choice_rather_than_refusing(self):
        """⚠️ The false-refusal direction, and it is the one that would hurt.

        Her English material is scans, and a scanner that writes a PDF this
        cannot parse must not cost her the upload. No count means no picker and
        the whole file is sent, which is exactly what happens today.
        """
        assert pages_in("scan.pdf", b"%PDF-1.4 truncated here") is None


class TestCuttingItToThePagesSheHasReached:
    def test_only_the_pages_she_chose_come_out(self):
        assert pages_of(cut_to_pages(A_CHAPTER, 2, 4)) == [
            "PAGE TWO", "PAGE THREE", "PAGE FOUR"
        ]

    def test_the_pages_before_the_range_are_not_in_what_comes_out(self):
        """🚨 The failure this feature exists to prevent, stated directly."""
        assert "PAGE ONE" not in " ".join(pages_of(cut_to_pages(A_CHAPTER, 2, 4)))

    def test_the_pages_after_the_range_are_not_in_what_comes_out(self):
        """🚨 And the half that matters most: nothing the children have not
        reached yet can be drawn on, because it never leaves this machine."""
        later = " ".join(pages_of(cut_to_pages(A_CHAPTER, 2, 4)))
        assert "PAGE FIVE" not in later and "PAGE SIX" not in later

    def test_one_page_on_its_own_is_a_range_like_any_other(self):
        assert pages_of(cut_to_pages(A_CHAPTER, 3, 3)) == ["PAGE THREE"]


class TestWhatActuallyTravelsToClaude:
    """The document block is what leaves the machine, so it is what gets read
    back. Asserting on the object we built and not on the bytes we encoded is
    how a narrowing stays true in the tests and false on the wire."""

    def _pdf_out_of(self, material):
        assert material.blocks, "nothing was attached for Claude to read"
        block = material.blocks[0]
        assert block["type"] == "document"
        return base64.b64decode(block["source"]["data"])

    def test_the_document_sent_holds_only_the_pages_she_chose(self):
        material = read_upload("chapter-1.pdf", A_CHAPTER, pages=(2, 3))
        assert pages_of(self._pdf_out_of(material)) == ["PAGE TWO", "PAGE THREE"]

    def test_the_whole_chapter_is_not_what_gets_sent(self):
        """🚨 The `LOOSE:` case. A cut that is made and then thrown away leaves
        every test above green and sends her whole book anyway."""
        material = read_upload("chapter-1.pdf", A_CHAPTER, pages=(2, 3))
        sent = " ".join(pages_of(self._pdf_out_of(material)))
        assert "PAGE ONE" not in sent
        assert "PAGE SIX" not in sent

    def test_without_a_range_the_whole_file_is_sent_exactly_as_it_was(self):
        """The unchanged path: a one-page PDF, or a scanner this cannot parse."""
        material = read_upload("chapter-1.pdf", A_CHAPTER)
        assert self._pdf_out_of(material) == A_CHAPTER

    def test_a_pdf_narrowed_to_pages_is_still_something_we_cannot_read(self):
        """Cutting it does not give us the words. `is_held` stays False, so the
        name check still says out loud that it could not run."""
        material = read_upload("chapter-1.pdf", A_CHAPTER, pages=(2, 3))
        assert not material.is_held
        assert material.text == ""


class TestSheCanSeeWhichPagesWereSent:
    """The origin is printed above every sheet by
    `_say_what_was_done_with_her_text`. Without the page numbers in it the
    narrowing is invisible, and an invisible guarantee is not one."""

    def test_the_origin_names_the_pages_she_chose(self):
        material = read_upload("chapter-1.pdf", A_CHAPTER, pages=(4, 6))
        assert material.origin == "chapter-1.pdf, pages 4–6"

    def test_a_single_page_is_named_as_one_page(self):
        material = read_upload("chapter-1.pdf", A_CHAPTER, pages=(4, 4))
        assert material.origin == "chapter-1.pdf, page 4"

    def test_without_a_range_the_origin_is_the_file_itself(self):
        material = read_upload("chapter-1.pdf", A_CHAPTER)
        assert material.origin == "chapter-1.pdf"


class TestARangeThatCannotWorkIsRefused:
    """Every refusal names the real page count, because that is the fact she
    needs and the one thing the screen cannot have got wrong."""

    def test_a_page_beyond_the_end_says_how_many_pages_there_are(self):
        with pytest.raises(SourceMaterialError) as refused:
            cut_to_pages(A_CHAPTER, 4, 9)
        assert "6" in str(refused.value)

    def test_a_page_before_the_beginning_is_refused(self):
        with pytest.raises(SourceMaterialError):
            cut_to_pages(A_CHAPTER, 0, 3)

    def test_a_range_that_runs_backwards_is_refused(self):
        with pytest.raises(SourceMaterialError) as refused:
            cut_to_pages(A_CHAPTER, 5, 2)
        assert "5" in str(refused.value) and "2" in str(refused.value)

    def test_the_ceiling_is_the_hundred_pages_this_model_reads(self):
        """⚠️ The number itself, pinned, because every other test here derives
        from it and would follow it wherever it moved.

        Read off the Anthropic API reference on 2026-09-21 for
        `claude-haiku-4-5-20251001`: a PDF block may be 600 pages, but only 100
        on a 200K-context model, and this is one. Raising it does not buy a
        longer chapter — it buys a request the API refuses.
        """
        assert MAX_PAGES_AT_ONCE == 100

    def test_more_pages_than_claude_reads_at_once_names_the_number_that_fits(self):
        """Measured off the API reference 2026-09-21: 100 pages is the ceiling
        on a 200K-context model, which is the model this app calls."""
        book = a_pdf_of(*[f"PAGE {n}" for n in range(1, MAX_PAGES_AT_ONCE + 41)])
        with pytest.raises(SourceMaterialError) as refused:
            cut_to_pages(book, 1, MAX_PAGES_AT_ONCE + 40)
        assert str(MAX_PAGES_AT_ONCE) in str(refused.value)

    def test_exactly_the_ceiling_is_allowed(self):
        """A limit that refuses the value it names is a limit nobody can use."""
        book = a_pdf_of(*[f"PAGE {n}" for n in range(1, MAX_PAGES_AT_ONCE + 1)])
        assert len(pages_of(cut_to_pages(book, 1, MAX_PAGES_AT_ONCE))) == MAX_PAGES_AT_ONCE

    def test_a_range_on_something_that_is_not_a_pdf_is_refused_not_sent_whole(self):
        """The loose direction: falling back to the whole file here would send
        everything after telling her only three pages went."""
        with pytest.raises(SourceMaterialError):
            read_upload("chapter-1.pdf", b"%PDF-1.4 truncated here", pages=(2, 3))
