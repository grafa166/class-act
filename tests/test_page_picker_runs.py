"""The page picker driven as a real screen, not read as text.

⚠️ **The property this file exists for cannot be read off the source.** The trap
is that a cut made once at upload looks identical in the code to one made on
every rerun — and the difference is the whole feature: she picks pages 4 to 6,
the screen says pages 4 to 6, and the whole chapter goes anyway.

So this runs the panel's PDF path through a real Streamlit script, changes the
page numbers the way she would, and reads back what is actually attached for
Claude. `AppTest` cannot drive a file uploader, so the upload itself is a stand
-in with the three things `_take_the_pdf` uses — `name`, `size` and
`getvalue()`. Everything downstream of it is the real code.
"""

import base64

import pytest
from streamlit.testing.v1 import AppTest

from tests.test_source_pages import a_pdf_of, pages_of

TIMEOUT = 30

BOX, SCAN, CAME_FROM = "ws_source_text", "ws_source_scan", "ws_source_from"


def _the_screen():
    """The panel's PDF path, as a script, with a six-page chapter uploaded."""
    import streamlit as st

    from source_panel import _take_the_pdf
    from tests.test_page_picker_runs import _A_FAKE_UPLOAD

    refused = _take_the_pdf(
        _A_FAKE_UPLOAD(), "ws_source_text", "ws_source_scan", "ws_source_from", "ws"
    )
    if refused:
        st.error(refused)


class _A_FAKE_UPLOAD:
    """What `st.file_uploader` hands back, reduced to what the panel reads."""

    name = "chapter-1.pdf"

    def __init__(self):
        self.data = a_pdf_of(
            "PAGE ONE", "PAGE TWO", "PAGE THREE", "PAGE FOUR", "PAGE FIVE", "PAGE SIX"
        )
        self.size = len(self.data)

    def getvalue(self):
        return self.data


def _what_was_attached(at):
    material = at.session_state[SCAN]
    assert material is not None, "nothing was attached for Claude to read"
    return material


def _pages_attached(at):
    material = _what_was_attached(at)
    return pages_of(base64.b64decode(material.blocks[0]["source"]["data"]))


@pytest.fixture
def screen():
    at = AppTest.from_function(_the_screen, default_timeout=TIMEOUT)
    at.run()
    assert not at.exception, f"the panel raised: {at.exception}"
    return at


class TestSheIsAskedWhichPages:
    def test_there_are_two_page_numbers_to_set(self, screen):
        labels = [number.label for number in screen.number_input]
        assert labels == ["First page", "Last page"], labels

    def test_they_start_on_the_whole_document(self, screen):
        """Narrowing is something she does on purpose. A picker that quietly
        sent page 1 only would be its own defect."""
        assert [number.value for number in screen.number_input] == [1, 6]

    def test_the_whole_document_is_what_goes_until_she_narrows_it(self, screen):
        assert len(_pages_attached(screen)) == 6


class TestChangingTheRangeChangesWhatIsSent:
    """🚨 The defect the whole feature is built to close, driven end to end."""

    def test_only_the_pages_she_set_are_attached_after_a_rerun(self, screen):
        screen.number_input[0].set_value(2).run()
        screen.number_input[1].set_value(4).run()
        assert not screen.exception, f"the panel raised: {screen.exception}"
        assert _pages_attached(screen) == ["PAGE TWO", "PAGE THREE", "PAGE FOUR"]

    def test_the_pages_she_left_out_are_not_on_the_wire(self, screen):
        screen.number_input[0].set_value(2).run()
        screen.number_input[1].set_value(4).run()
        sent = " ".join(_pages_attached(screen))
        assert "PAGE ONE" not in sent, "a page she excluded was sent anyway"
        assert "PAGE FIVE" not in sent and "PAGE SIX" not in sent, (
            "the pages the children have not reached were sent anyway"
        )

    def test_the_origin_she_reads_matches_what_was_sent(self, screen):
        """The origin is printed above the sheet. If it can drift from the
        bytes, it is worse than saying nothing at all."""
        screen.number_input[0].set_value(3).run()
        screen.number_input[1].set_value(5).run()
        material = _what_was_attached(screen)
        assert material.origin == "chapter-1.pdf, pages 3–5"
        assert _pages_attached(screen) == ["PAGE THREE", "PAGE FOUR", "PAGE FIVE"]

    def test_widening_it_again_brings_the_pages_back(self, screen):
        """A cut that is only ever applied once would pass every narrowing test
        above and fail this one."""
        screen.number_input[1].set_value(2).run()
        assert len(_pages_attached(screen)) == 2
        screen.number_input[1].set_value(6).run()
        assert len(_pages_attached(screen)) == 6

    def test_a_range_that_runs_backwards_is_said_on_the_screen(self, screen):
        screen.number_input[0].set_value(5).run()
        screen.number_input[1].set_value(2).run()
        assert screen.error, "a backwards range was accepted in silence"
        assert screen.session_state[SCAN] is None, (
            "the refusal is on the screen and the old document is still attached"
        )


class TestThePdfLeavesTheBoxAlone:
    def test_the_box_stays_empty_because_nothing_here_reads_a_scan(self, screen):
        assert screen.session_state[BOX] == ""

    def test_what_she_types_beside_it_survives_a_rerun(self, screen):
        """⚠️ The reason `_take_the_upload` is stamped once per file in the
        first place. The cut had to come out from behind that stamp without
        taking this with it."""
        screen.session_state[BOX] = "Mary Lennox was sent to Misselthwaite Manor."
        screen.number_input[1].set_value(3).run()
        assert screen.session_state[BOX] == (
            "Mary Lennox was sent to Misselthwaite Manor."
        )


class TestAPdfWithOnePageInIt:
    def test_nothing_is_asked_and_the_file_goes_as_it_is(self):
        def one_page():
            import streamlit as st

            from source_panel import _take_the_pdf
            from tests.test_page_picker_runs import _A_ONE_PAGE_UPLOAD

            refused = _take_the_pdf(
                _A_ONE_PAGE_UPLOAD(),
                "ws_source_text",
                "ws_source_scan",
                "ws_source_from",
                "ws",
            )
            if refused:
                st.error(refused)

        at = AppTest.from_function(one_page, default_timeout=TIMEOUT)
        at.run()
        assert not at.exception, f"the panel raised: {at.exception}"
        assert not at.number_input, "a picker with one possible answer was offered"
        material = at.session_state[SCAN]
        assert material.origin == "worksheet.pdf"
        assert (
            base64.b64decode(material.blocks[0]["source"]["data"])
            == _A_ONE_PAGE_UPLOAD().getvalue()
        )


class _A_ONE_PAGE_UPLOAD(_A_FAKE_UPLOAD):
    name = "worksheet.pdf"

    def __init__(self):
        self.data = a_pdf_of("ONLY PAGE")
        self.size = len(self.data)


class TestAScanNothingHereCanOpen:
    """⚠️ The false-refusal direction. Her English material is scans, and one
    this cannot parse must still reach Claude the way it does today."""

    def test_it_says_so_and_sends_the_file_anyway(self):
        def damaged():
            import streamlit as st

            from source_panel import _take_the_pdf
            from tests.test_page_picker_runs import _A_DAMAGED_UPLOAD

            refused = _take_the_pdf(
                _A_DAMAGED_UPLOAD(),
                "ws_source_text",
                "ws_source_scan",
                "ws_source_from",
                "ws",
            )
            if refused:
                st.error(refused)

        at = AppTest.from_function(damaged, default_timeout=TIMEOUT)
        at.run()
        assert not at.exception, f"the panel raised: {at.exception}"
        assert not at.number_input, "a picker was offered over a file nothing could read"
        said = " ".join(caption.value for caption in at.caption)
        assert "count the pages" in said, (
            "the picker vanished with nothing on screen saying why, which reads "
            "as the app being broken"
        )
        assert at.session_state[SCAN] is not None, "the upload was lost"


class _A_DAMAGED_UPLOAD(_A_FAKE_UPLOAD):
    name = "scan.pdf"

    def __init__(self):
        self.data = b"%PDF-1.4 the scanner stopped here"
        self.size = len(self.data)
