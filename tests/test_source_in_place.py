"""Her text on the page, and the reply that never used it.

`with_the_source_in_place` is the last thing between the model's reply and the
sheet she prints. It does two jobs that look the same and are not:

**Drift is corrected.** The model reproduced her extract and tidied it — a
smart quote, a dropped last line. Her words go back in and the sheet is right.

**A source the sheet never used is refused.** Measured live 2026-09-15: given a
story extract, a maths word-problem sheet invented a space-shopping scenario
and ignored the source completely, with no error of any kind. Substituting her
story into *that* reply prints it above eight questions about oxygen tanks —
the exact incoherence an adversarial pass killed the first design over. So the
backstop is a guard, not a substitution.

**Where the line sits is measured, not chosen.** `scripts/measure_source_drift.py`,
run 2026-09-16 over the four probe replies and 133 saved replies: every reply
written without her text scored **0.032 or below**, and every genuine
reproduction scored **0.972 or above**. The two thresholds sit inside that gap
with room on both sides.

⚠️ The middle of that gap is not knowledge. A reply between the two thresholds
is neither reproduced nor ignored as far as anything here has measured, so it
is flagged and left alone — not substituted, and not refused.
"""

import re

import pytest

from planning.source_material import (
    CLOSE_ENOUGH_TO_SUBSTITUTE,
    TOO_FAR_FROM_HER_TEXT,
    SourceMaterialError,
    request_with,
    room_for_the_source,
    source_from_text,
    with_the_source_in_place,
)

# ⚠️ **Both of these are the real artefacts, not shortened versions of them**,
# copied from `live-runs/2026-09-15-232726-probe-source-types/`: the extract the
# probe supplied, and the scenario the model wrote instead of using it.
#
# The first draft of this file abridged them, and the positive control caught
# what that cost. Measured: the abridged pair scored 0.000 by word pairs and
# 0.087 by single words — under the refusal line either way, so every test here
# passed whichever measure the guard used, and the mutation that swaps one for
# the other was invisible. The real pair scores 0.015 and 0.130: the second is
# *above* the refusal line, so counting single words really does hand this sheet
# over, and a test can now see it. A shortened fixture is an easier case than
# the one that was measured, and easy cases are what a control is for.
HER_TEXT = """When Mary Lennox was sent to Misselthwaite Manor to live with her uncle everybody said she was the most disagreeable-looking child ever seen. It was true, too. She had a little thin face and a little thin body, thin light hair and a sour expression.

Her hair was yellow, and her face was yellow because she had been born in India and had always been ill in one way or another. Her father had held a position under the English Government and had always been busy and ill himself, and her mother had been a great beauty who cared only to go to parties and amuse herself with gay people.

So when she was a sickly, fretful, ugly little baby she was kept out of the way, and when she became a sickly, fretful, toddling thing she was kept out of the way also. She never remembered seeing familiarly anything but the dark faces of her Ayah and the other native servants."""

IGNORED_IT = """You are a Space Explorer preparing for a mission to visit distant planets. You need to buy supplies from the Space Station Shop. Each item costs a different amount, and you have £50 to spend. Look at the prices of the items you need below.

You must decide which items to buy and work out the total cost of your supplies. Remember, you cannot spend more than £50."""

# The same reproduction, tidied the way a reply drifts: the last paragraph
# dropped and a clause tightened. Measured at 1.000 — every word pair on the
# page still came out of her text, which is what "a short reproduction is drift,
# not a different text" means.
DRIFTED = "\n\n".join(HER_TEXT.split("\n\n")[:2])

# A rewrite close enough to substitute, and not identical to her text — the case
# that tells "never overwrite an adaptation" apart from "it happened to already
# be her words". Measured at 0.972.
LIGHTLY_REWRITTEN = (
    HER_TEXT.replace("disagreeable-looking", "disagreeable looking")
    .replace("familiarly", "clearly")
    .replace("gay people", "cheerful people")
)


def held():
    return source_from_text(HER_TEXT, origin="the text you pasted")


def a_scan():
    """A photograph: it reaches Claude, but we never hold the words."""
    from planning.source_material import SourceMaterial

    return SourceMaterial(text="", origin="page.jpg", blocks=({"type": "image"},))


def reading(passage_text):
    """A reading sheet whose vocabulary box is drawn from its own passage.

    ⚠️ The box used to be a fixed word regardless of the passage, which made
    every sheet built by this helper incoherent the moment the vocabulary check
    existed — a test failure that said nothing about the code. A fixture has to
    be a sheet that could really have come back.

    ⚠️ And it picks the words with the guard's own tokeniser, not a second
    regex. A hand-rolled one pulled `shouldn` out of `shouldn't`, which is not
    a word on the page by any reading — so the fixture invented the very fault
    the check is for, and the failure looked like a defect in the guard.
    """
    from planning.source_material import _words

    words = [w for w in _words(passage_text) if len(w) >= 4][:2]
    return {
        "title": "Reading Comprehension",
        "passage": {"title": "Mary Arrives", "text": passage_text},
        "vocabulary": [{"word": w, "definition": "..."} for w in words],
        "questions": [{"number": 1, "question": "What was Mary like?", "answer": "thin"}],
    }


def word_problems(scenario_text):
    return {
        "title": "Problem Solving",
        "scenario": {"title": "At the shop", "text": scenario_text},
        "questions": [{"number": 1, "question": "How much?", "answer": "£4"}],
    }


class TestWithoutASourceNothingHappens:
    """The call is unconditional in `app.py`, so there is no branch to forget."""

    def test_a_sheet_with_no_source_comes_back_untouched(self):
        content = reading("A passage the model wrote about space.")
        outcome = with_the_source_in_place(content, "reading_comprehension", None, None)
        assert outcome.content == content

    def test_a_sheet_with_no_source_never_claims_anything_was_checked(self):
        outcome = with_the_source_in_place(reading("anything"), "reading_comprehension", None, None)
        assert outcome.source_checked is False


class TestAnEmptyHaystackNeverReportsGreen:
    """The failure this whole design is built against.

    A guard running on nothing and reporting success is invisible: every test
    passes and the screen says "checked against your text" when it never was.
    """

    def test_a_photograph_is_never_reported_as_checked_against_her_text(self):
        outcome = with_the_source_in_place(
            reading(IGNORED_IT), "reading_comprehension", a_scan(), "questions_from"
        )
        assert outcome.source_checked is False, "we never held the words on a photograph"

    def test_a_photograph_is_never_refused_for_not_matching_words_we_do_not_have(self):
        outcome = with_the_source_in_place(
            reading(IGNORED_IT), "reading_comprehension", a_scan(), "questions_from"
        )
        assert outcome.content["passage"]["text"] == IGNORED_IT

    def test_a_reply_with_no_passage_at_all_is_not_reported_as_checked(self):
        outcome = with_the_source_in_place(reading(""), "reading_comprehension", held(), "use_exactly")
        assert outcome.source_checked is False

    def test_forgetting_the_source_argument_is_an_error_not_a_silent_skip(self):
        with pytest.raises(TypeError):
            with_the_source_in_place(reading(HER_TEXT), "reading_comprehension")


class TestDriftIsCorrected:
    def test_her_text_replaces_a_passage_that_drifted_from_it(self):
        outcome = with_the_source_in_place(
            reading(DRIFTED), "reading_comprehension", held(), "use_exactly"
        )
        assert outcome.content["passage"]["text"] == HER_TEXT
        assert outcome.substituted is True

    def test_the_passage_printed_is_her_text_character_for_character(self):
        outcome = with_the_source_in_place(
            reading(DRIFTED), "reading_comprehension", held(), "use_exactly"
        )
        assert outcome.content["passage"]["text"] == held().text

    def test_a_word_problem_sheet_has_its_scenario_corrected_not_its_passage(self):
        outcome = with_the_source_in_place(
            word_problems(DRIFTED), "problem_solving", held(), "use_exactly"
        )
        assert outcome.content["scenario"]["text"] == HER_TEXT

    def test_the_reply_she_actually_got_needed_no_correcting(self):
        outcome = with_the_source_in_place(
            reading(HER_TEXT), "reading_comprehension", held(), "use_exactly"
        )
        assert outcome.substituted is False, "already her text, word for word"
        assert outcome.source_checked is True

    def test_the_original_reply_is_left_alone_and_a_corrected_copy_returned(self):
        content = reading(DRIFTED)
        with_the_source_in_place(content, "reading_comprehension", held(), "use_exactly")
        assert content["passage"]["text"] == DRIFTED, "the artefact on disk is evidence"


class TestASourceTheSheetNeverUsedIsRefused:
    def test_a_reply_about_something_else_entirely_is_refused(self):
        with pytest.raises(SourceMaterialError):
            with_the_source_in_place(
                word_problems(IGNORED_IT), "problem_solving", held(), "use_exactly"
            )

    def test_the_refusal_names_the_mismatch_she_made_not_the_symptom(self):
        """She paired a story with a maths sheet. That is the thing to tell her.

        "the passage did not match" is true and useless — she cannot act on it.
        """
        with pytest.raises(SourceMaterialError) as refused:
            with_the_source_in_place(
                word_problems(IGNORED_IT), "problem_solving", held(), "use_exactly"
            )
        message = str(refused.value).lower()
        assert "problem solving" in message, "name the kind of sheet that could not use it"
        assert "text you gave it" in message or "text you supplied" in message

    def test_the_refusal_says_what_would_fix_it(self):
        with pytest.raises(SourceMaterialError) as refused:
            with_the_source_in_place(
                word_problems(IGNORED_IT), "problem_solving", held(), "use_exactly"
            )
        message = str(refused.value).lower()
        assert "reading comprehension" in message, "the sheet a story extract does suit"

    def test_an_ignored_source_is_flagged_not_refused_when_she_asked_to_adapt(self):
        """🚨 This test used to assert the opposite, and the assertion was wrong.

        It was written from the reasonable-sounding idea that adapting is a
        rewrite of *her* text, so a reply about something else should be
        refused however she asked for it. Then the rewrite case was measured:
        a correct Year 3 simplification of one sentence scores **0.000** by the
        same comparison, indistinguishable from an ignored source. There is no
        threshold that separates them, so refusing here would have refused
        correct work — which this project holds to be worse than not guarding
        at all. It is flagged instead, and the flag says what is not known.
        """
        outcome = with_the_source_in_place(
            word_problems(IGNORED_IT), "problem_solving", held(), "adapt"
        )
        assert outcome.flags, "an ignored source must at least be said out loud"
        assert outcome.substituted is False


class TestAnAdaptationIsNeverOverwritten:
    """She asked for it to be rewritten, so putting the original back destroys it."""

    def test_an_adaptation_is_left_as_the_model_wrote_it(self):
        rewritten = (
            "Mary Lennox was sent to Misselthwaite Manor to live with her uncle. Everybody "
            "said she was the most disagreeable-looking child they had ever seen. It was "
            "true. She had a thin little face and a sour expression.\n\nHer hair was yellow "
            "and her face was yellow too. She had been born in India and she was often ill."
        )
        outcome = with_the_source_in_place(
            reading(rewritten), "reading_comprehension", held(), "adapt"
        )
        assert outcome.content["passage"]["text"] == rewritten
        assert outcome.substituted is False

    def test_a_perfect_reproduction_is_still_not_substituted_when_adapting(self):
        outcome = with_the_source_in_place(
            reading(HER_TEXT), "reading_comprehension", held(), "adapt"
        )
        assert outcome.substituted is False

    def test_a_close_rewrite_keeps_its_own_wording(self):
        """The one that tells the rule apart from a coincidence.

        Both tests above pass even with the action ignored: an adaptation far
        from her text is never close enough to substitute, and one identical to
        it is returned untouched by the branch that skips a pointless copy. Only
        a rewrite that is *close and different* can tell whether `adapt` is
        being honoured — the positive control found both of them blind.
        """
        outcome = with_the_source_in_place(
            reading(LIGHTLY_REWRITTEN), "reading_comprehension", held(), "adapt"
        )
        assert outcome.content["passage"]["text"] == LIGHTLY_REWRITTEN
        assert outcome.substituted is False


class TestTheMiddleOfTheGapIsFlaggedNotJudged:
    def _a_half_invented_passage(self):
        return HER_TEXT.split("\n\n")[0] + "\n\nThe rocket climbed above the clouds and the " \
            "crew waved at the crowd below, counting down the seconds until launch."

    def test_a_reply_neither_close_nor_ignored_is_left_alone(self):
        outcome = with_the_source_in_place(
            reading(self._a_half_invented_passage()),
            "reading_comprehension",
            held(),
            "use_exactly",
        )
        assert outcome.substituted is False
        assert outcome.flags, "she is told, even though nothing is refused"

    def test_the_flag_says_the_passage_drifted_not_that_it_was_rewritten(self):
        """⚠️ Asserting only that *a* flag exists let the wrong one through.

        With the reproduction branch disabled the adaptation wording fired
        instead — so a teacher who asked for her text word for word would have
        been told her sheet "has been rewritten", which is both wrong and the
        opposite of what she needs to check. The positive control found it; no
        test did.
        """
        outcome = with_the_source_in_place(
            reading(self._a_half_invented_passage()),
            "reading_comprehension",
            held(),
            "use_exactly",
        )
        said = " ".join(outcome.flags).lower()
        assert "not from the text you supplied" in said
        assert "rewritten" not in said, "this sheet was never meant to be a rewrite"

    def test_a_reply_that_matched_her_text_carries_no_flag(self):
        outcome = with_the_source_in_place(
            reading(HER_TEXT), "reading_comprehension", held(), "use_exactly"
        )
        assert not outcome.flags


class TestWhatTheResultCarries:
    """`results.json` gets these, so a source dropped somewhere upstream shows
    up as a column of zeroes rather than as nothing at all."""

    def test_the_result_carries_how_close_the_reply_was(self):
        outcome = with_the_source_in_place(
            reading(HER_TEXT), "reading_comprehension", held(), "use_exactly"
        )
        assert outcome.similarity == pytest.approx(1.0)

    def test_the_result_carries_where_her_text_came_from(self):
        outcome = with_the_source_in_place(
            reading(HER_TEXT), "reading_comprehension", held(), "use_exactly"
        )
        assert outcome.origin == "the text you pasted"


class TestASheetThatBuildsFromTheTextIsNotCompared:
    """A cloze sheet is mostly its own instructions, so comparing it to her
    extract would refuse correct work — and nothing here has measured what a
    correct one scores. It is left alone and said to be unchecked."""

    def _a_cloze_sheet(self):
        """⚠️ With a `passage` on it, which is not an accident.

        Models put keys on a sheet that nobody asked for: measured on
        2026-09-03, two investigation replies answered every criterion out of
        `sorting_section`, `job_section` and `explanation_section`, three keys
        the prompt has never mentioned. A fixture with only the keys the schema
        requires cannot tell "this type is never compared" from "this fixture
        happened to have nothing to compare", and the positive control found
        exactly that hole here.
        """
        return {
            "title": "Cloze",
            "sections": [{"text": "Fill in the missing words."}],
            "passage": {"text": "The rocket left the launch pad in a cloud of steam."},
        }

    def test_a_fill_in_the_gaps_sheet_is_neither_substituted_nor_refused(self):
        content = self._a_cloze_sheet()
        outcome = with_the_source_in_place(content, "cloze", held(), "questions_from")
        assert outcome.content == content
        assert outcome.source_checked is False


class TestUncheckedAlwaysSaysWhy:
    """"Not checked" and "checked and fine" must never look the same on screen.

    ⚠️ And the three reasons are not the same sentence. A photograph cannot be
    read; a fill-in-the-gaps sheet can be read perfectly well and is simply not
    the kind of sheet that prints a text whole. Telling her the second in the
    words of the first says the app failed when it did exactly the right thing.
    """

    def test_a_photograph_says_we_cannot_read_it(self):
        outcome = with_the_source_in_place(
            reading(IGNORED_IT), "reading_comprehension", a_scan(), "questions_from"
        )
        assert "read" in outcome.why_not_checked.lower()

    def test_a_build_from_sheet_says_it_does_not_print_a_text_whole(self):
        content = {"title": "Cloze", "sections": [{"text": "Fill in the missing words."}]}
        outcome = with_the_source_in_place(content, "cloze", held(), "questions_from")
        assert "whole" in outcome.why_not_checked.lower()

    def test_all_three_reasons_are_different_sentences(self):
        """⚠️ Comparing only two of the three left the third free to be

        aliased to one of the others without a single test noticing — the
        positive control found exactly that. Three states, three sentences.
        """
        reasons = [
            with_the_source_in_place(
                reading(IGNORED_IT), "reading_comprehension", a_scan(), "questions_from"
            ).why_not_checked,
            with_the_source_in_place(
                {"title": "Cloze"}, "cloze", held(), "questions_from"
            ).why_not_checked,
            with_the_source_in_place(
                reading(""), "reading_comprehension", held(), "use_exactly"
            ).why_not_checked,
        ]
        assert all(reasons), "every unchecked outcome says why"
        assert len(set(reasons)) == 3, f"two of these are the same sentence: {reasons}"

    def test_a_checked_sheet_gives_no_reason_because_there_is_none(self):
        outcome = with_the_source_in_place(
            reading(HER_TEXT), "reading_comprehension", held(), "use_exactly"
        )
        assert outcome.why_not_checked == ""


class TestThereIsRoomInTheReplyForHerTextToComeBack:
    """The reply has to carry her text back *as well as* its questions, its
    model answers and its vocabulary box. The budget is an output ceiling, and
    streaming does not raise it — a truncated reply is refused either way."""

    def test_a_sheet_that_prints_her_text_is_given_room_for_it(self):
        assert room_for_the_source(6144, "reading_comprehension", held()) > 6144

    def test_a_longer_text_is_given_more_room_than_a_shorter_one(self):
        short = source_from_text("One short line about Mary.", origin="x")
        assert room_for_the_source(6144, "reading_comprehension", held()) > (
            room_for_the_source(6144, "reading_comprehension", short)
        )

    def test_a_sheet_that_only_builds_tasks_is_given_no_extra(self):
        assert room_for_the_source(4096, "cloze", held()) == 4096

    def test_no_source_changes_nothing(self):
        assert room_for_the_source(4096, "reading_comprehension", None) == 4096

    def test_the_longest_source_we_accept_still_fits_in_one_reply(self):
        """The length limit and the reply ceiling must not disagree."""
        from planning.source_material import MAX_REPLY_TOKENS, MAX_SOURCE_CHARS

        longest = source_from_text("word " * (MAX_SOURCE_CHARS // 5), origin="x")
        assert room_for_the_source(6144, "reading_comprehension", longest) <= MAX_REPLY_TOKENS

    def test_the_budget_is_capped_even_for_a_source_that_got_past_the_limit(self):
        """The backstop, and it needs its own test to be worth anything.

        ⚠️ The test above cannot see this cap: the length limit already keeps
        every accepted source comfortably under the ceiling, so removing the
        cap changes nothing it measures. The positive control caught that.
        What the cap defends is a later edit raising `MAX_SOURCE_CHARS` — so it
        is tested the only way that is real, by handing it a source that never
        went through the limit.
        """
        from planning.source_material import MAX_REPLY_TOKENS, SourceMaterial

        enormous = SourceMaterial(text="word " * 40_000, origin="x")
        assert room_for_the_source(6144, "reading_comprehension", enormous) == MAX_REPLY_TOKENS


class TestAScanReachesTheModelAsAPicture:
    """Her text goes as text. A PDF or a photograph has to go as itself —
    there is nothing here to paste into the prompt."""

    def test_a_pasted_text_is_sent_as_the_prompt_it_has_always_been(self):
        assert request_with("the prompt", held()) == "the prompt"

    def test_no_source_is_sent_as_the_prompt_it_has_always_been(self):
        assert request_with("the prompt", None) == "the prompt"

    def test_a_photograph_is_sent_as_blocks_with_the_prompt_after_it(self):
        sent = request_with("the prompt", a_scan())
        assert isinstance(sent, list)
        assert sent[-1] == {"type": "text", "text": "the prompt"}
        assert sent[0]["type"] == "image", "the picture comes first, as documented"

    def test_a_photograph_that_carried_no_blocks_is_not_sent_as_an_empty_list(self):
        """A source with neither words nor blocks has nothing in it at all."""
        from planning.source_material import SourceMaterial

        empty = SourceMaterial(text="", origin="page.jpg", blocks=())
        assert request_with("the prompt", empty) == "the prompt"


class TestTheComparisonSeesTheWholeText:
    """What the comparison cannot read, it scores as if it were not there.

    ⚠️ Every case below was measured on 2026-09-18 against the first version of
    this guard, and every one of them was wrong. The first three are the same
    root cause: a tokeniser that only matched `[a-z0-9']` silently dropped
    curly apostrophes, accented letters and every non-Latin script, so texts
    that differ entirely could look identical and texts reproduced perfectly
    could look unrelated.

    None of this showed up in the drift census, because the extract it was
    measured on contains no apostrophe and no accent — the "typography tidied"
    row replaced a character that was never in the text. **A fixture that does
    not contain the thing being varied measures nothing**, and it reported
    1.000 either way.
    """

    def test_a_reply_that_only_curled_the_apostrophes_is_still_her_text(self):
        """Measured 0.000 before the fix, i.e. refused — and curling quotes is
        the single most ordinary thing a model does to a piece of prose."""
        straight = "I can't go. We won't wait. You shouldn't ask."
        curled = "I can’t go. We won’t wait. You shouldn’t ask."
        outcome = with_the_source_in_place(
            reading(curled),
            "reading_comprehension",
            source_from_text(straight, origin="x"),
            "use_exactly",
        )
        assert outcome.content["passage"]["text"] == straight

    def test_a_french_name_survives_the_comparison(self):
        """Accented letters were dropped, so `Éléa rêve` and `Elea reve`
        compared as fragments rather than as words."""
        from planning.source_material import how_much_of_it_is_hers

        hers = "Éléa rêve d'un jardin secret et d'une clé rouillée."
        assert how_much_of_it_is_hers(hers, hers) == pytest.approx(1.0)

    def test_two_unrelated_texts_in_another_script_are_not_the_same_text(self):
        """Measured 1.000 before the fix: every character was discarded, so
        both sides reduced to their numbering and matched perfectly."""
        from planning.source_material import how_much_of_it_is_hers

        hers = "1. 小猫睡觉。2. 小狗跑步。"
        invented = "1. 火箭升空。2. 宇航员登月。"
        assert how_much_of_it_is_hers(hers, invented) < TOO_FAR_FROM_HER_TEXT

    def test_a_short_passage_reproduced_exactly_is_not_refused(self):
        """A text too short to contain a single word pair scored 0.000 —
        so the shortest possible perfect reproduction was refused."""
        from planning.source_material import how_much_of_it_is_hers

        assert how_much_of_it_is_hers("Go!", "Go!") == pytest.approx(1.0)

    def test_a_short_passage_that_is_not_hers_is_still_caught(self):
        """The control for the row above: the short-text path must not simply
        return 1.0 for everything."""
        from planning.source_material import how_much_of_it_is_hers

        assert how_much_of_it_is_hers("Go!", "Stop!") < TOO_FAR_FROM_HER_TEXT


class TestAnAdaptationIsNeverRefused:
    """She asked for a rewrite. A thorough rewrite shares almost nothing with
    the original, and nothing here has ever measured what a real one scores.

    🚨 Measured on 2026-09-18: *"The exhausted infant slumbered peacefully."*
    rewritten as *"The tired baby slept well."* — a correct, careful Year 3
    simplification — scored **0.000** and was refused. That is the failure this
    project holds to be worse than having no guard at all: the teacher is told
    her correct work is wrong, and there is no measurement behind the refusal.
    """

    def test_a_thorough_rewrite_is_not_refused(self):
        outcome = with_the_source_in_place(
            reading("The tired baby slept well."),
            "reading_comprehension",
            source_from_text("The exhausted infant slumbered peacefully.", origin="x"),
            "adapt",
        )
        assert outcome.content["passage"]["text"] == "The tired baby slept well."

    def test_a_rewrite_far_from_her_text_is_flagged_rather_than_accepted_in_silence(self):
        outcome = with_the_source_in_place(
            reading("The tired baby slept well."),
            "reading_comprehension",
            source_from_text("The exhausted infant slumbered peacefully.", origin="x"),
            "adapt",
        )
        assert outcome.flags, "she is told, even though nothing is refused"

    def test_an_unrelated_reply_is_flagged_on_every_action(self):
        """Middle-band replies used to pass silently unless she had asked for
        reproduction, so the one action that cannot be measured was also the
        one that said nothing."""
        for action in ("use_exactly", "adapt", "questions_from", "scaffolds_around"):
            outcome = with_the_source_in_place(
                reading("It was hot. Rockets flew into space."),
                "reading_comprehension",
                source_from_text("It was cold. Mary wore a coat.", origin="x"),
                action,
            )
            assert outcome.flags, f"{action} passed an unrelated passage in silence"


class TestTheVocabularyBoxIsAboutThePagePrinted:
    """The template's own rules 3 and 12, made checkable.

    `READING_COMPREHENSION_PROMPT` ties the vocabulary box to the passage — so
    a box listing words that are not on the page is a sheet that teaches
    nothing, and it is exactly what an adversarial pass predicted would happen
    if her text were swapped in underneath a passage the model wrote.

    ⚠️ **Refusing is scoped to the case that creates the incoherence.** When
    her text was substituted, the box may describe the passage we deleted, so
    the sheet is refused. When we changed nothing, a word off the page is the
    model's own mistake: she is told, and keeps the sheet. Measured
    2026-09-18 across every reply that carries a vocabulary list beside a
    passage — 12 of 12 words were on the page — but two replies is not a census,
    and a refusal built on it would refuse correct work the first time a model
    writes `slumbering` for `slumbered`.
    """

    def _with_vocabulary(self, passage_text, words):
        return {
            "title": "Reading Comprehension",
            "passage": {"title": "Mary Arrives", "text": passage_text},
            "vocabulary": [{"word": w, "definition": "..."} for w in words],
            "questions": [{"number": 1, "question": "What?", "answer": "thin"}],
        }

    def test_a_box_about_the_deleted_passage_is_refused_when_her_text_went_in(self):
        content = self._with_vocabulary(DRIFTED, ["rocket", "astronaut"])
        with pytest.raises(SourceMaterialError) as refused:
            with_the_source_in_place(content, "reading_comprehension", held(), "use_exactly")
        message = str(refused.value).lower()
        assert "rocket" in message, "name the words, or she cannot act on it"

    def test_the_refusal_says_what_the_box_should_have_contained(self):
        content = self._with_vocabulary(DRIFTED, ["rocket"])
        with pytest.raises(SourceMaterialError) as refused:
            with_the_source_in_place(content, "reading_comprehension", held(), "use_exactly")
        assert "your text" in str(refused.value).lower()

    def test_a_box_drawn_from_her_text_passes(self):
        content = self._with_vocabulary(DRIFTED, ["disagreeable", "sour", "yellow"])
        outcome = with_the_source_in_place(
            content, "reading_comprehension", held(), "use_exactly"
        )
        assert outcome.substituted is True
        assert not outcome.flags

    def test_a_word_off_the_page_is_flagged_when_nothing_was_substituted(self):
        """Her sheet is not thrown away for a mistake we did not cause."""
        content = self._with_vocabulary(HER_TEXT, ["rocket"])
        outcome = with_the_source_in_place(
            content, "reading_comprehension", held(), "use_exactly"
        )
        assert outcome.substituted is False
        assert any("rocket" in flag for flag in outcome.flags)

    def test_case_is_not_a_difference_a_reader_would_see(self):
        content = self._with_vocabulary(DRIFTED, ["Yellow", "SOUR"])
        outcome = with_the_source_in_place(
            content, "reading_comprehension", held(), "use_exactly"
        )
        assert not outcome.flags

    def test_a_word_the_page_has_in_another_form_is_not_refused(self):
        """`servants` on the page, `servant` in the box — the likeliest false
        refusal there is, and the one that would throw away a correct sheet.

        ⚠️ This test used to call the guard and assert nothing, so it passed
        whether or not the rule it names existed. The positive control found
        it: tightening the match to letter-for-letter left the whole suite
        green. A test that only checks "no exception" on a path that never
        raises is not a test.
        """
        content = self._with_vocabulary(HER_TEXT, ["servant", "toddling"])
        outcome = with_the_source_in_place(
            content, "reading_comprehension", held(), "use_exactly"
        )
        assert not outcome.flags, (
            "a word the page carries in another form was called missing"
        )

    def test_a_fragment_from_the_middle_of_a_word_is_not_on_the_page(self):
        """The control for the row above. Without it, accepting `servant` for
        `servants` is indistinguishable from accepting `ant` — and a check that
        accepts `ant` has stopped meaning anything at all.
        """
        content = self._with_vocabulary(HER_TEXT, ["ant"])
        outcome = with_the_source_in_place(
            content, "reading_comprehension", held(), "use_exactly"
        )
        assert any("ant" in flag for flag in outcome.flags)

    def test_a_sheet_with_no_vocabulary_box_is_not_refused_for_an_empty_one(self):
        outcome = with_the_source_in_place(
            reading(DRIFTED), "reading_comprehension", held(), "use_exactly"
        )
        assert outcome.substituted is True


class TestTheThresholdsAreTheMeasuredOnes:
    def test_the_refusal_line_sits_above_every_ignored_reply_ever_measured(self):
        """Worst measured ignore: 0.032, over 136 replies, 2026-09-16."""
        assert TOO_FAR_FROM_HER_TEXT > 0.032

    def test_the_refusal_line_sits_below_the_loosest_plausible_adaptation(self):
        """A Year 3 rewrite of the probe extract scored 0.570 by hand."""
        assert TOO_FAR_FROM_HER_TEXT < 0.570

    def test_the_substitution_line_sits_below_every_genuine_reproduction(self):
        """Lowest drifted reproduction measured: 0.972."""
        assert CLOSE_ENOUGH_TO_SUBSTITUTE < 0.972

    def test_the_substitution_line_sits_above_a_rewrite(self):
        assert CLOSE_ENOUGH_TO_SUBSTITUTE > 0.570


class TestTheCreditLineUnderHerPassage:
    """🚨 An attribution nobody asked for, that nothing can check, printed on
    the sheet the children read.

    Measured off the only reply ever generated from a supplied text
    (`live-runs/2026-09-15-232726-probe-source-types/`): given the Secret Garden
    extract, the model wrote *"From The Secret Garden by Frances Hodgson
    Burnett"* into `passage.source_note`. That one is correct — and it is
    correct because the model **recognised the book**, which is precisely the
    mechanism that names the wrong one on a text it half recognises. The app
    never asks for the line, cannot verify it, and would print it under her own
    extract on thirty copies.

    ⚠️ It is dropped rather than corrected. Writing the origin there instead
    would put a file name on a child's worksheet, and the only person who knows
    what the book actually is is her.
    """

    def _with_a_credit(self, text, credit):
        content = reading(text)
        content["passage"]["source_note"] = credit
        return content

    def test_the_models_attribution_is_not_printed_under_her_passage(self):
        outcome = with_the_source_in_place(
            self._with_a_credit(HER_TEXT, "From The Secret Garden by Frances Hodgson Burnett"),
            "reading_comprehension",
            held(),
            "use_exactly",
        )
        assert not outcome.content["passage"].get("source_note")

    def test_it_goes_on_the_path_where_her_text_is_put_back(self):
        """The substituting path builds its own copy of the sheet, so it has
        to drop the credit there too or the fix reaches only half the cases."""
        outcome = with_the_source_in_place(
            self._with_a_credit(DRIFTED, "Adapted from a novel by Frances Hodgson Burnett"),
            "reading_comprehension",
            held(),
            "use_exactly",
        )
        assert outcome.substituted is True
        assert not outcome.content["passage"].get("source_note")

    def test_it_goes_when_she_asked_for_the_text_to_be_adapted(self):
        """An adaptation is her text rewritten. A book named under it is an
        attribution for something that is no longer in that book."""
        outcome = with_the_source_in_place(
            self._with_a_credit(LIGHTLY_REWRITTEN, "From The Secret Garden"),
            "reading_comprehension",
            held(),
            "adapt",
        )
        assert not outcome.content["passage"].get("source_note")

    def test_it_goes_on_a_photograph_where_we_never_held_the_words(self):
        """⚠️ The route that matters most: her scans. The passage came out of a
        picture nothing here can read, so an attribution under it is the model
        guessing at a book from an image."""
        outcome = with_the_source_in_place(
            self._with_a_credit("Whatever Claude read off the page.", "From a book"),
            "reading_comprehension",
            a_scan(),
            "questions_from",
        )
        assert not outcome.content["passage"].get("source_note")

    def test_it_goes_on_a_word_problem_sheet_too(self):
        content = word_problems(HER_TEXT)
        content["scenario"]["source_note"] = "From a maths textbook"
        outcome = with_the_source_in_place(
            content, "problem_solving", held(), "use_exactly"
        )
        assert not outcome.content["scenario"].get("source_note")

    def test_a_sheet_she_supplied_no_text_for_keeps_what_it_wrote(self):
        """⚠️ Out of scope, deliberately. Without a source the passage is the
        model's own invention and so is the line under it; there is nothing
        here that makes one more honest than the other, and widening this to
        every sheet would change a screen nobody asked about."""
        content = self._with_a_credit("A passage about space.", "Adapted from a space book")
        outcome = with_the_source_in_place(content, "reading_comprehension", None, None)
        assert outcome.content["passage"]["source_note"] == "Adapted from a space book"

    def test_the_sheet_she_passed_in_is_not_changed_underneath_her(self):
        """The caller keeps the reply it was given. Editing it in place would
        leave the raw artefact and the printed sheet disagreeing — which is the
        2026-09-03 defect exactly."""
        content = self._with_a_credit(HER_TEXT, "From The Secret Garden")
        with_the_source_in_place(content, "reading_comprehension", held(), "use_exactly")
        assert content["passage"]["source_note"] == "From The Secret Garden"

    def test_a_sheet_with_no_credit_line_is_not_copied_for_nothing(self):
        """Cheap, and it keeps the common path free of a deep copy of the whole
        reply on every single sheet."""
        content = reading(HER_TEXT)
        outcome = with_the_source_in_place(
            content, "reading_comprehension", a_scan(), "questions_from"
        )
        assert outcome.content is content
