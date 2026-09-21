"""The box where she brings her own text, on the worksheet screen.

Run through `app.py` rather than as its own entrypoint, because that is how she
reaches it and because a panel that only works when run directly has been the
shape of two defects in this repo already.
"""

import ast
import pathlib
import re

import pytest
from streamlit.testing.v1 import AppTest

from planning.scheme_intake import UnreadableUploadError, blocks_for_upload
from planning.source_material import SourceMaterial, actions_for
from source_panel import ACCEPTED_FILES, _her_choice_moved, _the_pages_she_wants

APP = pathlib.Path(__file__).resolve().parent.parent / "app.py"
PANEL = pathlib.Path(__file__).resolve().parent.parent / "source_panel.py"
TIMEOUT = 30


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(str(APP), default_timeout=TIMEOUT)
    at.run()
    return at


class TestThePanelIsOnTheScreen:
    def test_the_app_still_loads_with_the_panel_on_it(self, app):
        assert not app.exception, f"app.py raised on load: {app.exception}"

    def test_there_is_somewhere_to_paste_her_own_text(self, app):
        labels = " ".join(t.label for t in app.text_area)
        assert "paste the text" in labels.lower(), "the source box is missing"

    def test_there_is_somewhere_to_upload_a_chapter(self, app):
        assert any(
            "upload" in str(getattr(w, "label", "")).lower()
            for w in app.get("file_uploader")
        ), "the source uploader is missing"

    def test_the_screen_says_the_source_is_sent_to_anthropic(self, app):
        said = " ".join(c.value for c in app.caption if isinstance(c.value, str))
        assert "Anthropic" in said, (
            "nothing on the screen tells her where her text goes"
        )


class TestTheFileTypesOfferedAreOnesWeCanRead:
    """An extension offered by the uploader and refused by the reader is a
    dead end she meets after choosing the file, not before."""

    @pytest.mark.parametrize("extension", ACCEPTED_FILES)
    def test_every_offered_extension_is_one_the_reader_accepts(self, extension):
        try:
            blocks_for_upload(f"x.{extension}", b"not really a file")
        except UnreadableUploadError as refused:
            assert "Cannot read" not in str(refused), (
                f".{extension} is offered on screen and refused by the reader"
            )
        except Exception:
            # Unreadable *content* is fine here — the point is the extension.
            pass


class TestThePagePickerOnAPdf:
    """Which pages of an uploaded PDF get sent, and when she is asked at all.

    ⚠️ **The trap in this file, and it is the whole feature.** `_take_the_upload`
    stamps `name:size` in session state so it runs **once per file** — that
    exists to stop a rerun refilling the box and throwing away her edits. A page
    cut made behind that stamp is made once, at upload, and changing the range
    afterwards would do nothing at all: the screen would say pages 4 to 6 and
    the whole chapter would go. That is a false pass, which is the worse side.
    """

    def _panel(self):
        return ast.parse(PANEL.read_text(encoding="utf-8"))

    def _cuts(self, tree):
        """Every call that hands `read_upload` a page range."""
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "read_upload"
                and any(keyword.arg == "pages" for keyword in node.keywords)
            ):
                yield node

    def _function_holding(self, tree, node):
        for candidate in ast.walk(tree):
            if isinstance(candidate, ast.FunctionDef) and any(
                child is node for child in ast.walk(candidate)
            ):
                return candidate
        return None

    def test_a_one_page_pdf_offers_nothing_to_choose_between(self):
        """A photograph is one page and the uploader takes one file at a time,
        so there is nothing to pick. Asking anyway is a control with one
        possible answer."""
        assert _the_pages_she_wants(1, "first", "last") is None

    def test_a_pdf_whose_pages_could_not_be_counted_offers_no_picker(self):
        assert _the_pages_she_wants(None, "first", "last") is None

    def test_the_pages_are_cut_out_of_the_file_somewhere_in_the_panel(self):
        assert list(self._cuts(self._panel())), (
            "nothing in the panel narrows a PDF, so the whole file is still sent"
        )

    def test_the_cut_is_not_made_once_per_file_like_the_box_is(self):
        tree = self._panel()
        for cut in self._cuts(tree):
            holder = self._function_holding(tree, cut)
            guards = " ".join(
                ast.unparse(node.test)
                for node in ast.walk(holder)
                if isinstance(node, ast.If) and any(child is cut for child in ast.walk(node))
            )
            assert "stamp" not in guards, (
                "the page cut is behind the once-per-file stamp, so changing "
                f"the range does nothing: {guards!r}"
            )

    def test_nothing_returns_before_the_pages_are_cut(self):
        """⚠️ Passes today, so its RED step is the mutation
        `the page cut is made once at upload instead of on every rerun`.

        A guard on the enclosing `if` is not the only way to make the cut run
        once: an early `return` when the stamp matches does it just as well,
        and reads as tidy code. Both shapes have to be closed or the one left
        open is the one that gets written.
        """
        tree = self._panel()
        for cut in self._cuts(tree):
            holder = self._function_holding(tree, cut)
            early = [
                node
                for node in ast.walk(holder)
                if isinstance(node, ast.Return) and node.lineno < cut.lineno
            ]
            assert not early, (
                f"{holder.name} returns before it cuts the PDF, so the range "
                "she picks after the first rerun changes nothing"
            )

    def test_the_panel_itself_reaches_the_cut(self):
        """A cut in a function nobody calls is dead code, and every test above
        it still passes while the whole file goes to Claude."""
        tree = self._panel()
        holders = {
            self._function_holding(tree, cut).name for cut in self._cuts(tree)
        }
        panel = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "source_panel"
        )
        called = {
            node.func.id
            for node in ast.walk(panel)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert holders & called, (
            f"nothing in source_panel() calls {sorted(holders)}, so an uploaded "
            "PDF is never narrowed"
        )

    def test_the_cut_does_not_live_in_the_once_per_file_function(self):
        tree = self._panel()
        for cut in self._cuts(tree):
            holder = self._function_holding(tree, cut)
            assert holder is None or holder.name != "_take_the_upload", (
                "the cut runs inside the function that runs once per upload"
            )


class TestTheScreenIsWiredToTheGuard:
    """The four facts about the generation path that no other test can see.

    ⚠️ **Read as text, deliberately**, in the style of the two `GENERATOR_MAP`
    parsers (`test_smoke.py`, `test_worksheet_document.py`). Importing `app.py`
    runs the whole Streamlit script, and the only way to exercise this path for
    real is to press Generate — which calls the live API and costs money on
    every run.

    Each of these was found by the positive control: mutating the line away
    left the entire suite green. A string check that fails on a reformat is a
    poor test; a path nothing checks at all is worse, and this is the path the
    teacher's own text travels down.
    """

    def _the_generation_block(self):
        source = APP.read_text(encoding="utf-8")
        start = source.index("if generate_btn or _regenerating:")
        end = source.index("# Phase 2", start)
        return source[start:end]

    def test_a_pairing_that_cannot_work_is_refused_before_a_token_is_spent(self):
        block = self._the_generation_block()
        guard = block.index("check_the_pairing(")
        request = block.index("generate_worksheet_content(")
        assert guard < request, "the refusal happens after the money is spent"
        assert "if params.get('source_material') is not None:" in block, (
            "the pairing check no longer depends on there being a source"
        )

    def test_her_source_travels_with_the_request(self):
        block = self._the_generation_block()
        assert "request_with(prompt, params.get('source_material'))" in block, (
            "a photograph or PDF never reaches Claude — only the prompt does"
        )

    def test_a_reply_carrying_her_text_back_is_streamed(self):
        """The 2026-09-02 defect: a long reply asked for in one piece had its
        connection closed by the server."""
        block = self._the_generation_block()
        assert "stream=params.get('source_material') is not None" in block

    def test_the_names_are_checked_between_the_reply_and_the_sheet(self):
        block = self._the_generation_block()
        assert "with_the_names_checked(" in block, (
            "her one hard constraint reaches a live user defended by nothing "
            "but a sentence at the end of a prompt"
        )
        assert block.index("with_the_source_in_place(") < block.index(
            "with_the_names_checked("
        ), "the names are checked before the passage is corrected into place"

    def test_the_names_are_checked_against_what_she_typed_as_well(self):
        """Her topic, her objective, her subject and her theme. Without them
        she is told the unit she named is an intruder on her own worksheet."""
        block = self._the_generation_block()
        call = block[block.index("with_the_names_checked("):]
        call = call[: call.index("st.session_state.source_outcomes")]
        for hers in ("effective_topic", "effective_objective", "subject", "theme_name"):
            assert hers in call, f"{hers} is not counted as something she supplied"

    def test_the_guard_runs_between_the_reply_and_the_sheet(self):
        block = self._the_generation_block()
        assert "with_the_source_in_place(" in block
        # ⚠️ `in block`, not a bare string. `assert "x", "msg"` asserts on a
        # non-empty literal and passes whatever the file says — a tautology,
        # and the exact shape of the check that went silent here on 2026-09-03.
        assert "content = outcome.content" in block, (
            "the corrected sheet is generated and then thrown away"
        )


class TestTheWiringItselfHoldsTogether:
    """Two faults that every string check in this file reads as working code.

    Found 2026-09-20 by reading the call site against the signature rather than
    against a sentence. `app.py` is read as *text* everywhere here, deliberately
    — pressing Generate calls the live API and costs money — and text cannot see
    a name nobody imported or arguments handed over in the wrong order. Both
    crash on the first press of the button, and both were in the tree with 1,267
    tests passing.

    ⚠️ These read the *signature*, not a copy of it. A parameter renamed or
    reordered in `planning/source_material.py` fails here rather than in front
    of a teacher.
    """

    #: The parameter names distinctive enough that the expression passed for
    #: them must say so, and the spellings `app.py` uses for each. Anything not
    #: listed — `base_tokens`, `prompt` — is not checked, because the call site
    #: has no obligation to echo a name that carries no meaning of its own.
    SPELLINGS = {
        "content": {"content"},
        "source_action": {"source_action"},
        "source_material": {"source_material"},
        "worksheet_type": {"worksheet_type", "ws_type_key"},
    }

    def _tree(self):
        return ast.parse(APP.read_text(encoding="utf-8"))

    def _names_bound_in(self, tree):
        """Every name `app.py` gives a meaning to, by any route."""
        import builtins

        bound = set(dir(builtins))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                bound |= {alias.asname or alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                bound.add(node.name)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = node.args
                    bound |= {
                        a.arg
                        for a in [*args.posonlyargs, *args.args, *args.kwonlyargs]
                    }
                    bound |= {a.arg for a in (args.vararg, args.kwarg) if a}
            elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                bound.add(node.id)
            elif isinstance(node, ast.ExceptHandler) and node.name:
                bound.add(node.name)
            elif isinstance(node, (ast.Global, ast.Nonlocal)):
                bound |= set(node.names)
        return bound

    def _source_module_calls(self, tree):
        """Every call `app.py` makes to something `planning.source_material` owns."""
        import planning.source_material as module

        theirs = {name for name in dir(module) if not name.startswith("_")}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in theirs:
                    yield node

    def test_every_source_function_it_calls_is_one_it_imported(self):
        """A call to a name nobody imported is a `NameError` on the button press.

        Not hypothetical: `room_for_the_source` and `request_with` were both
        called here and neither was imported, so *every* generation — with a
        source or without one — died on an unhandled name.
        """
        tree = self._tree()
        bound = self._names_bound_in(tree)
        missing = sorted(
            {call.func.id for call in self._source_module_calls(tree)} - bound
        )
        assert not missing, (
            "app.py calls these and never imports them, so pressing Generate "
            f"raises NameError: {missing}"
        )

    def test_every_call_hands_its_arguments_in_the_order_the_function_declares(self):
        """A swap here is silent in the source and fatal on the screen.

        `room_for_the_source(base_tokens, worksheet_type, source_material)` was
        being called with the source in the worksheet-type slot and the action
        in the source slot, which reaches `source_action.is_held` and raises
        `AttributeError` — caught by the bare `except Exception` and shown to
        her as "an unexpected error occurred".
        """
        import inspect

        import planning.source_material as module

        wrong = []
        for call in self._source_module_calls(self._tree()):
            signature = inspect.signature(getattr(module, call.func.id))
            parameters = list(signature.parameters)
            for position, argument in enumerate(call.args):
                if position >= len(parameters):
                    wrong.append(f"{call.func.id}: more arguments than parameters")
                    continue
                parameter = parameters[position]
                allowed = self.SPELLINGS.get(parameter)
                if allowed is None:
                    continue
                said = {
                    node.id for node in ast.walk(argument) if isinstance(node, ast.Name)
                } | {
                    node.value
                    for node in ast.walk(argument)
                    if isinstance(node, ast.Constant) and isinstance(node.value, str)
                }
                if not (said & allowed):
                    wrong.append(
                        f"{call.func.id}(...) line {call.lineno}: the {parameter!r} "
                        f"slot is given {ast.unparse(argument)!r}"
                    )
        assert not wrong, "arguments handed over in the wrong order:\n  " + "\n  ".join(wrong)


class TestTheCaptionAboveTheSheet:
    """What `_say_what_was_done_with_her_text` may say, and when.

    ⚠️ **Read as a shape rather than as a sentence**, because the sentence is
    the thing most likely to be reworded and the shape is the thing that is
    load-bearing. Two properties, and both were wrong before Phase 4 wired the
    name check in: the honest label must never appear beside a sheet where
    nothing was checked, and the findings must render on every path — the early
    return in the unchecked branch swallowed them on the five types that build
    from her text rather than printing it.
    """

    def _the_caption_function(self):
        for node in ast.walk(ast.parse(APP.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_say_what_was_done_with_her_text"
            ):
                return node
        raise AssertionError("the caption above each sheet has gone from app.py")

    def _guards_above(self, function, node):
        """Every `if` test this node sits inside, as source text."""
        guards, stack = [], [(function, [])]
        while stack:
            current, above = stack.pop()
            for child in ast.iter_child_nodes(current):
                if child is node:
                    guards.extend(above)
                if isinstance(child, ast.If):
                    stack.append((child, above + [ast.unparse(child.test)]))
                    for orelse in child.orelse:
                        if orelse is node:
                            guards.extend(above + [f"not ({ast.unparse(child.test)})"])
                        stack.append((orelse, above + [f"not ({ast.unparse(child.test)})"]))
                else:
                    stack.append((child, above))
        return guards

    def test_the_honest_label_never_renders_beside_an_unchecked_sheet(self):
        """⚠️ On a PDF or a photograph the check cannot run at all, because we
        never hold the words. Saying "every name is checked against your text"
        there is the exact failure this design exists to prevent."""
        function = self._the_caption_function()
        labels = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Name) and node.id == "THE_HONEST_LABEL"
        ]
        assert labels, "the honest label is not rendered at all"
        for label in labels:
            guards = " ".join(self._guards_above(function, label))
            assert "names_checked" in guards, (
                "the label is printed without first asking whether the names "
                f"were checked; it is guarded only by: {guards!r}"
            )

    def test_a_finding_is_shown_whether_or_not_the_passage_was_checked(self):
        """A cloze sheet is `source_checked=False` with a reason and its names
        are perfectly checkable. A finding that renders only on the checked
        path is a finding she never sees on five of the seven types."""
        function = self._the_caption_function()
        loops = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.For) and ast.unparse(node.iter).endswith("flags")
        ]
        assert loops, "the findings are no longer rendered"
        for loop in loops:
            guards = " ".join(self._guards_above(function, loop))
            assert "source_checked" not in guards, (
                f"the findings only render when the passage was checked: {guards!r}"
            )

    def test_nothing_returns_early_before_the_findings(self):
        """The shape of the bug, pinned directly: a `return` reachable before
        the flag loop puts every finding behind a branch."""
        function = self._the_caption_function()
        loop = next(
            node
            for node in ast.walk(function)
            if isinstance(node, ast.For) and ast.unparse(node.iter).endswith("flags")
        )
        early = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Return)
            and node.lineno > function.body[0].lineno
            and node.lineno < loop.lineno
            and "origin" not in " ".join(self._guards_above(function, node))
        ]
        assert not early, (
            "something returns before the findings are rendered, on a path that "
            "is not the no-source one"
        )


class TestRegenerateReplaysEveryInput:
    """`generation_params` is the replay tape. Anything read from it that is
    never written into it comes back empty on Regenerate, silently.

    ⚠️ This passes today, so its RED step is the mutation
    `a new input is missing from what Regenerate replays`, not a failing
    feature test. One guard, every future input.
    """

    def _app_source(self):
        return APP.read_text(encoding="utf-8")

    def _keys_written(self, source):
        """Parsed, not split on the first brace.

        ⚠️ `generation_params` is assigned twice: once as `{}` at start-up and
        once as the real literal. Splitting on the first occurrence returns the
        empty one, and the test then reports *every* key as unstored — which
        looks like a catastrophic finding and is really a broken test. It did
        exactly that the first time it ran.
        """
        written = set()
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
                continue
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr == "generation_params":
                    written |= {
                        key.value
                        for key in node.value.keys
                        if isinstance(key, ast.Constant)
                    }
        assert written, "the generation_params literal was not found in app.py"
        return written

    def _keys_read(self, source):
        return set(
            re.findall(r"""params\[['"]([a-z_]+)['"]\]""", source)
            + re.findall(r"""params\.get\(['"]([a-z_]+)['"]""", source)
        )

    def test_everything_regenerate_replays_is_something_it_was_given(self):
        source = self._app_source()
        read_but_never_written = self._keys_read(source) - self._keys_written(source)
        assert not read_but_never_written, (
            "these are read back on Regenerate but never stored, so they come "
            f"back empty: {sorted(read_but_never_written)}"
        )


class TestWhenWhatSheAskedForIsNoLongerOnOffer:
    """Her choice can change itself, and until now it did so in silence.

    Measured 2026-09-21 by driving a real radio: pick *use the source exactly*
    while her text is pasted in, then upload a photograph of the page, and
    Streamlit finds the stored choice is not among the three a photograph
    allows, drops it, and falls back to the first on the list. Nothing crashes.
    She simply asked for one kind of sheet and is now getting another.

    ⚠️ The same thing happens with no upload at all — switching from a reading
    comprehension sheet to a fill-in-the-gaps one takes *use exactly* away too
    — so the sentence names what moved rather than blaming the photograph.
    """

    WHAT_A_PHOTOGRAPH_ALLOWS = actions_for(
        "reading_comprehension",
        SourceMaterial(text="", origin="page.jpg", blocks=({"type": "image"},)),
    )

    def test_nothing_is_said_while_what_she_picked_is_still_offered(self):
        assert _her_choice_moved("adapt", self.WHAT_A_PHOTOGRAPH_ALLOWS) == ""

    def test_nothing_is_said_before_she_has_picked_anything(self):
        assert _her_choice_moved(None, self.WHAT_A_PHOTOGRAPH_ALLOWS) == ""

    def test_it_says_which_choice_of_hers_went_away(self):
        said = _her_choice_moved("use_exactly", self.WHAT_A_PHOTOGRAPH_ALLOWS)
        assert "Use the source exactly" in said, said

    def test_it_says_what_she_is_getting_instead(self):
        """⚠️ Named from what is actually offered, not written out by hand:
        Streamlit falls back to the first option, so the sentence has to follow
        the list rather than a copy of it."""
        said = _her_choice_moved("use_exactly", self.WHAT_A_PHOTOGRAPH_ALLOWS)
        first = next(iter(self.WHAT_A_PHOTOGRAPH_ALLOWS.values()))
        assert first in said, said

    def test_the_sentence_is_shown_on_the_screen_and_not_just_computed(self):
        """A message nothing renders is the silence it was written to fix."""
        source = PANEL.read_text(encoding="utf-8")
        tree = ast.parse(source)
        rendered = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and any(
                isinstance(inner, ast.Name) and inner.id == "moved"
                for inner in ast.walk(node)
            )
        ]
        assert rendered, "the panel works out that her choice moved and says nothing"
