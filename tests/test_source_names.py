"""The name check: content that introduces a named entity absent from her text.

**The promise this can keep, and the one it cannot.** Her one hard constraint is
*"if I upload only part of a story/text, the lesson planner should only use what
I've supplied and not assume or reveal later parts."* No deterministic check can
prove that: *"Later, Alice discovers the key belongs to her father"* uses only
names the extract already contains, and nothing here can see the spoiler in it.

What is testable is narrower — **a named entity on the sheet that is not in her
text** — and that is what these pin, pass and fail. Every test below is about
that narrower claim, and the label on screen says only that much.

⚠️ **Report-only.** Nothing in this phase refuses a sheet. A false refusal here
would be the teacher told her correct worksheet is wrong; a finding is a
sentence she reads before printing.

⚠️ **The two traps the plan named, both false passes, both tested here.**
`_says_the_same` walks word stretches at arbitrary distance, so `Ben
Weatherstaff` would "match" *"…bent down… the weather stayed fair…"* and the
spoiler would be vouched for. `_segments_of` deletes bracketed choices as gaps,
and those are printed on a developing-level cloze sheet. Neither is used.
"""

import dataclasses

import pytest

from generators.styles import THEMES
from planning.source_material import SourceOutcome, source_from_text
from planning.source_names import (
    NAMES_CANNOT_BE_CHECKED,
    THE_HONEST_LABEL,
    names_on,
    supported_words,
    unsupported_names,
    with_the_names_checked,
)

# The opening of *The Secret Garden* — public domain, real prose, real names,
# the same shape as the half-term's RAP text. The same extract the drift tests
# use, so a fixture cannot drift between the two.
HER_TEXT = """When Mary Lennox was sent to Misselthwaite Manor to live with her uncle everybody said she was the most disagreeable-looking child ever seen. It was true, too. She had a little thin face and a little thin body, thin light hair and a sour expression.

Her hair was yellow, and her face was yellow because she had been born in India and had always been ill in one way or another."""

APPROVED = ("Rocks and Soils", "I can name three kinds of rock", "Science")


def flagged(reply, source_text=HER_TEXT, approved=APPROVED):
    """The reasons, as the screen would carry them."""
    return " | ".join(
        reason for _, reason in unsupported_names(reply, source_text, approved)
    )


class TestItFindsANameHerTextDoesNotHave:
    """The whole point. Everything else here exists to stop this misfiring."""

    def test_a_name_inside_a_question_is_found(self):
        """Spoilers live inside questions — that is where a later part leaks."""
        reply = {"questions": ["What do you think Alice does next?"]}
        assert "Alice" in flagged(reply)

    def test_a_name_her_text_already_has_is_left_alone(self):
        reply = {"questions": ["What do you think Mary does next?"]}
        assert not flagged(reply)

    def test_two_names_together_are_found_even_at_the_start_of_a_sentence(self):
        """`Ben Weatherstaff dug the bed.` — a run of two capitals opening a
        sentence is a name, not an instruction. Instructions are one word."""
        reply = {"passage": {"text": "Ben Weatherstaff dug the bed."}}
        assert "Ben Weatherstaff" in flagged(reply)

    def test_an_honorific_and_the_name_after_it_are_one_finding(self):
        """Found by running a realistic sheet rather than by a test: the full
        stop in `Mrs.` breaks the run, so `Mrs. Medlock` arrived as two
        findings — and `Mrs` on its own would fire on any sheet whose extract
        happens not to use it. An honorific is a closed class and names nobody.
        """
        reply = {"questions": ["Why does Mrs. Medlock take her to the Manor?"]}
        findings = unsupported_names(reply, HER_TEXT, APPROVED)
        assert len(findings) == 1, [reason for _, reason in findings]
        assert "Mrs Medlock" in findings[0][1]

    def test_an_honorific_does_not_flag_a_name_her_text_already_has(self):
        """The control: her extract introduces Medlock without the honorific,
        and the sheet adds it. That is not a new name."""
        reply = {"questions": ["Why does Mrs. Medlock take her upstairs?"]}
        assert not flagged(reply, source_text="Medlock took her upstairs.", approved=())

    def test_a_name_is_found_wherever_on_the_sheet_it_is_written(self):
        """The answer key is something she reads out. A name that reaches only
        the answers is still a name the sheet introduced."""
        reply = {"answers": [{"answer": "The key belonged to Archibald."}]}
        assert "Archibald" in flagged(reply)

    def test_an_accented_name_is_found(self):
        """⚠️ Matching `[a-z]` dropped every accented letter and every non-Latin
        script once already, and it failed in both directions at once."""
        reply = {"questions": ["Why did Chloé close the door?"]}
        assert "Chloé" in flagged(reply)

    def test_a_name_is_reported_once_however_often_it_appears(self):
        reply = {"questions": ["Where is Alice?", "What does Alice say?", "Alice ran."]}
        findings = unsupported_names(reply, HER_TEXT, APPROVED)
        assert len([f for f in findings if "Alice" in f[1]]) == 1

    def test_a_finding_says_where_on_the_sheet_it_was_found(self):
        """A name with no sentence around it is not something she can act on."""
        reply = {"questions": ["What do you think Alice does next?"]}
        where, _ = unsupported_names(reply, HER_TEXT, APPROVED)[0]
        assert "What do you think Alice does next" in where


class TestItDoesNotFlagTheWordsEveryWorksheetPrints:
    """⚠️ **A guard that refuses correct work is worse than no guard**, and this
    one would misfire on every sheet ever made if it took a capital letter as
    evidence on its own. These are the shapes that were measured to do it."""

    def test_an_instruction_at_the_start_of_a_line_is_not_a_name(self):
        """*Later, Challenge, Extension, Task, Write, Draw, Think, Why,
        Remember* — dropped structurally rather than by a word list, because a
        word list cannot know the next word somebody writes."""
        reply = {
            "tasks": [
                "Later, write what happens.",
                "Challenge: draw the rock you chose.",
                "Extension work goes here.",
                "Task one is finished.",
                "Write your answer on the line.",
                "Draw a picture of it.",
                "Think about what you have read.",
                "Why does it float?",
                "Remember to check your spelling.",
            ]
        }
        assert not flagged(reply)

    def test_the_corpus_line_that_would_have_flagged_every_sheet_on_day_one(self):
        """⚠️ Measured from the saved replies: without the title-case veto this
        line yields the candidate "Right Rock"."""
        reply = {"title": "Activity 2: Choose the Right Rock for the Job"}
        assert not flagged(reply)

    def test_a_shouted_heading_is_not_a_name(self):
        """Case carries no information in a line that is all of it."""
        reply = {"title": "ROCKS AND SOILS", "sections": ["WORD BANK"]}
        assert not flagged(reply)

    def test_a_capital_that_only_opens_quoted_speech_is_not_a_name(self):
        """A word after an opening quote is capitalised by convention, exactly
        as a word after a full stop is. Without the split it reads as
        mid-sentence, which is the position that makes a capital mean
        something."""
        reply = {"passage": {"text": 'The gardener said, "Later the robin came back."'}}
        assert not flagged(reply)

    def test_a_theme_word_is_supported_without_being_written_down_here(self):
        """*Mission*, *Captain's Log*, *Dive Log* — the theme decorates every
        sheet, and it is derived from `THEMES` rather than copied out of it.

        ⚠️ Written mid-sentence on purpose. As a heading it would be dropped by
        the title-case veto whether or not the themes were in the haystack, and
        the test would pass for a reason that has nothing to do with themes."""
        reply = {"tasks": ["Write your answer in the Captain's Log below."]}
        assert not flagged(reply)

    def test_every_theme_word_there_will_ever_be_is_supported(self):
        """Derived, so a theme added later cannot start flagging sheets."""
        haystack = supported_words("", ())
        for theme in THEMES.values():
            for value in theme.values():
                for word in str(value).replace("'", " ").split():
                    stripped = "".join(c for c in word if c.isalnum())
                    if len(stripped) > 1 and stripped[0].isupper():
                        assert stripped.lower() in haystack, (
                            f"{stripped!r} is in THEMES and would be flagged"
                        )

    def test_what_she_typed_or_approved_supports_a_name(self):
        """The unit title, the objective, the topic, the subject — her words,
        and she cannot be told her own topic is an intruder."""
        reply = {"questions": ["Which of these Soils holds the most water?"]}
        assert not flagged(reply)
        # The control: with her own words taken away, the same sheet flags.
        # ⚠️ A word out of her unit title, not the subject — the subject is
        # supported anyway, so the control would pass with `approved` ignored.
        assert "Soils" in flagged(reply, approved=())

    def test_a_possessive_is_the_same_name(self):
        reply = {"questions": ["Whose room was it? It was Mary's room."]}
        assert not flagged(reply)


class TestTheCorpusSaidTheseWouldFireOnEverySheet:
    """⚠️ **Measured, not imagined.** `scripts/sweep_unseen_names.py` over all
    133 saved replies, 2026-09-20. Each of these appeared in between six and
    fifty-six separate replies, which is what a hole in the detector looks like:
    a name in one reply is that sheet's subject matter, a word in forty is a
    rule that was missing.

    Every fix is the plan's own principle — *case carries no information here* —
    applied to a position it had not been applied to. None of them widens the
    search for an actual name.
    """

    def test_an_acronym_shouted_inside_ordinary_prose_is_not_a_name(self):
        """`SEND` in 56 replies and `EAL` in 53, plus `HARD`, `SOFT`, `NOT`,
        `ONE`. A word in capitals is emphasis or an abbreviation, and the
        capital says nothing either way — the same reason a shouted line is
        vetoed whole."""
        reply = {
            "steps": [
                "The other adult sits with the SEND group on the carpet.",
                "Put the rocks that are HARD together.",
                "Ask why an alternative rock does NOT work.",
            ]
        }
        assert not flagged(reply)

    def test_the_word_i_is_not_a_name(self):
        """`If I`, `Now I`, `When I`, `Now I'm`, `I've`, `I'll` — 90 replies
        between them. English capitalises the first person always, so it is the
        one word whose capital is guaranteed to mean nothing."""
        reply = {
            "steps": [
                "If I wanted a rock for a doorstep, would I pick the hard one?",
                "Now I need to explain my choice.",
                "When you have done it, I'll come and check.",
                "Right, I've brought in some real soil from outside.",
            ]
        }
        assert not flagged(reply)

    def test_a_name_beside_the_word_i_is_still_found(self):
        """The control. Dropping `I` must not drop what stands next to it."""
        reply = {"steps": ["Now I'm going to tell you Petra's story."]}
        assert "Petra" in flagged(reply)

    def test_a_dash_between_two_halves_of_a_heading_ends_the_first(self):
        """`Hook - What is a rock?`, `Plenary - Can you explain it?` — a spaced
        dash is doing a full stop's job, and the word after it is capitalised
        for a full stop's reason."""
        reply = {
            "sections": [
                "Hook - What is a rock?",
                "Plenary - Can you explain it?",
                "Practice — Paired rock observation",
            ]
        }
        assert not flagged(reply)

    def test_a_table_column_ends_where_the_next_one_begins(self):
        """`Rock name | Scratches?` is two cells, not one sentence."""
        reply = {"table": ["Rock name | Scratches? | Feels like"]}
        assert not flagged(reply)

    def test_a_numbered_part_of_a_sheet_is_furniture_and_not_a_name(self):
        """`Step 4`, `Activity 1`, `Lesson 1`, `Year 3`, `In Steps 3 and 4` —
        names are not numbered, and worksheets number everything."""
        reply = {
            "steps": [
                "This consolidates the observations from Step 3.",
                "Children in Year 3 have limited experience of weathering.",
                "It builds on what they knew from Lesson 1.",
                "In Steps 3 and 4, allow a shorter focus time.",
            ]
        }
        assert not flagged(reply)

    def test_a_numbered_thing_next_to_a_name_does_not_hide_it(self):
        """The control for the rule above."""
        reply = {"steps": ["In Step 3, Dickon plants the seeds."]}
        assert "Dickon" in flagged(reply)

    def test_a_heading_cannot_vouch_for_the_word_it_capitalised(self):
        """The second pass of the census, after the four fixes above: `Hook`,
        `Plenary`, `Practice`, `Modelling`, `Is`, `Hard`, `Smooth`, `Soft` were
        all still firing, and all for one reason.

        A word at the front of a segment counts only when the same word is used
        **mid-sentence** somewhere else, because mid-sentence is the position
        where a capital has to be explained. A heading capitalises every word
        it has, so the second and third words of one are mid-sentence by
        position and say nothing by convention — and that was corroborating the
        very headings the title-case veto had just thrown out.
        """
        reply = {
            "sections": ["Guided Practice", "Practice - sort the rocks."],
            "steps": ["Is it hard or soft?", "Hard or soft?"],
        }
        assert not flagged(reply)

    def test_a_name_used_mid_sentence_in_real_prose_still_vouches_for_itself(self):
        """The control. Narrowing what may corroborate must not stop `Alice`
        at the front of a sentence being found."""
        reply = {"passage": {"text": "The robin knew Alice well. Alice came back."}}
        assert "Alice" in flagged(reply)

    def test_a_word_that_is_not_a_name_in_english_is_never_a_name_here(self):
        """`Is`, `The`, `So`, `What`, `We`, `It`, `Did`, `More`, `Because` —
        the whole tail of the census after everything above.

        ⚠️ **This is a closed class and that is the entire justification.** The
        plan is right that the words which open an instruction cannot be
        listed — somebody writes a new one tomorrow. English function words are
        the opposite: articles, pronouns, auxiliaries, interrogatives,
        conjunctions, prepositions and quantifiers are a fixed set that has not
        grown in centuries, and not one of them names anything.

        ⚠️ Each pair below is copied from the corpus, and the second line of
        each pair is why the first one fires: a function word used mid-sentence
        somewhere on the sheet vouches for the same word opening a sentence
        elsewhere. Written without its corroborating line, this test passes
        whether or not the rule exists.
        """
        reply = {
            "steps": [
                "Is it hard or soft?",
                "What I observe by touching (Is it hard or soft?",
                "The rock has kept the shape of the creature.",
                "(3) The reason uses the property word in a sentence.",
                "So we choose by hard, not by shiny.",
                "Affirm the observations.] So we have found that rocks differ.",
                "What does it feel like?",
                "[Listen.] What does it feel like?",
            ]
        }
        assert not flagged(reply)

    def test_a_name_beginning_with_a_function_word_is_still_a_name(self):
        """The control. *The Secret Garden* is not `The`."""
        reply = {"questions": ["Who lives in The Rookery at the end?"]}
        assert "The Rookery" in flagged(reply)

    def test_the_subject_she_chose_is_hers(self):
        """`English` in 47 replies — she picked it from the sidebar. Derived
        from the curriculum rather than written down here, so a subject added
        later cannot start flagging sheets."""
        from curriculum import SUBJECT_REGISTRY

        haystack = supported_words("", ())
        for subject in SUBJECT_REGISTRY:
            assert subject.lower() in haystack, f"{subject!r} would be flagged"


class TestTheTwoFalsePassesThePlanNamedByName:
    """⚠️ **Worse than a false refusal, and invisible.** A refusal is seen and
    gets a second attempt; a false pass tells her the names were checked and
    hands a child the spoiler anyway."""

    def test_two_words_far_apart_in_her_text_do_not_support_a_name(self):
        """`_says_the_same` walks word stretches at arbitrary distance, so
        `Ben Weatherstaff` "matches" *"…bent down… the weather stayed fair…"*.
        This is the reason it is not used."""
        her_text = (
            "The old man bent down over the bed. It had been dry all week and "
            "the weather stayed fair until the evening."
        )
        reply = {"passage": {"text": "Ben Weatherstaff dug the bed."}}
        assert "Ben Weatherstaff" in flagged(reply, source_text=her_text, approved=())

    def test_a_name_drawn_inside_a_bracketed_choice_is_still_checked(self):
        """`_segments_of` deletes bracketed choices as gaps — and a developing
        level cloze sheet **prints** them, so the name is on the page."""
        reply = {"paragraphs": ["The gardener was [Ben/Dickon]."]}
        assert "Dickon" in flagged(reply)

    def test_a_name_is_not_supported_by_a_longer_word_it_sits_inside(self):
        """Whole words. `Mary` is not in her text because `Maryland` is.

        ⚠️ **The first fixture here was `Alice` against `Alicia`, and the
        positive control caught it**: `alice` is not a substring of `alicia`
        either, so the test passed whether the matching was whole-word or a
        bare substring, and the mutation that opens it reported `NOTHING
        FAILED`. A fixture that does not contain the thing being varied
        measures nothing — the same lesson the drift census earned.
        """
        reply = {"questions": ["Where did Mary go?"]}
        assert "Mary" in flagged(
            reply, source_text="They travelled to Maryland.", approved=()
        )

    def test_a_name_is_not_supported_by_a_shorter_word_inside_it(self):
        """The other direction, and the one `_says_the_same` fails at."""
        reply = {"questions": ["What did Weatherstaff plant?"]}
        assert "Weatherstaff" in flagged(
            reply, source_text="The weather stayed fair.", approved=()
        )


class TestNothingRefusesInThisPhase:
    def test_an_unsupported_name_is_a_flag_and_never_an_exception(self):
        outcome = SourceOutcome(
            content={"questions": ["What do you think Alice does next?"]},
            source_checked=True,
            origin="the text you pasted",
        )
        checked = with_the_names_checked(
            outcome, source_from_text(HER_TEXT, "the text you pasted"), APPROVED
        )
        assert checked.names_checked
        assert any("Alice" in flag for flag in checked.flags)

    def test_the_sheet_itself_is_handed_back_untouched(self):
        content = {"questions": ["What do you think Alice does next?"]}
        outcome = SourceOutcome(content=content, origin="the text you pasted")
        checked = with_the_names_checked(
            outcome, source_from_text(HER_TEXT, "the text you pasted"), APPROVED
        )
        assert checked.content == content


class TestTheScreenNeverSaysItCheckedWhenItDidNot:
    """⚠️ **The failure this whole design is built against.** A guard running on
    an empty haystack and reporting green: every test passes, and she is told
    something was verified that nothing looked at."""

    def test_a_photograph_can_never_be_reported_as_checked(self):
        """We never hold the words, so there is no haystack — and a haystack
        transcribed by the model would vouch for its own hallucination."""
        from planning.source_material import SourceMaterial

        scan = SourceMaterial(text="", origin="chapter-1.pdf", blocks=({"x": 1},))
        checked = with_the_names_checked(
            SourceOutcome(content={"questions": ["Who is Alice?"]}, origin="chapter-1.pdf"),
            scan,
            APPROVED,
        )
        assert not checked.names_checked
        assert checked.why_names_not_checked == NAMES_CANNOT_BE_CHECKED
        assert not checked.flags, "a scan cannot produce a finding about a name"

    def test_a_sheet_she_brought_no_text_to_says_nothing_at_all(self):
        outcome = SourceOutcome(content={"questions": ["Who is Alice?"]})
        assert with_the_names_checked(outcome, None, APPROVED) == outcome

    def test_a_sheet_that_only_builds_from_her_text_is_still_name_checked(self):
        """⚠️ **Two different axes, and collapsing them loses the check on five
        of the seven types that take a source.** A cloze sheet never prints her
        passage whole, so `source_checked` is False with a reason — and we hold
        every word of her text, so the names on it can be checked perfectly
        well."""
        from planning.source_material import DOES_NOT_PRINT_IT_WHOLE

        outcome = SourceOutcome(
            content={"paragraphs": ["The gardener was Dickon."]},
            source_checked=False,
            why_not_checked=DOES_NOT_PRINT_IT_WHOLE,
            origin="the text you pasted",
        )
        checked = with_the_names_checked(
            outcome, source_from_text(HER_TEXT, "the text you pasted"), APPROVED
        )
        assert checked.names_checked, (
            "the name check was skipped on a sheet whose every word we hold"
        )
        assert any("Dickon" in flag for flag in checked.flags)

    def test_a_finding_is_added_to_the_flags_already_there(self):
        outcome = SourceOutcome(
            content={"questions": ["Who is Alice?"]},
            source_checked=True,
            origin="the text you pasted",
            flags=("something the passage check found",),
        )
        checked = with_the_names_checked(
            outcome, source_from_text(HER_TEXT, "the text you pasted"), APPROVED
        )
        assert "something the passage check found" in checked.flags
        assert len(checked.flags) == 2


class TestTheLabelPromisesOnlyWhatIsTestable:
    def test_it_never_claims_the_sheet_is_spoiler_free(self):
        assert "not a promise the sheet is spoiler-free" in THE_HONEST_LABEL

    def test_it_says_the_check_is_against_her_text(self):
        assert "checked against your text" in THE_HONEST_LABEL

    def test_it_still_says_the_sheet_is_ai_drafted(self):
        """The standing decision: output is labelled AI-drafted, never verified."""
        assert "AI-drafted" in THE_HONEST_LABEL

    def test_the_reason_a_scan_cannot_be_checked_is_not_the_label(self):
        """"Checked and fine" and "not checked at all" must never read the same."""
        assert NAMES_CANNOT_BE_CHECKED != THE_HONEST_LABEL


class TestTheHaystackCannotGoQuietlyEmpty:
    def test_neither_argument_has_a_default(self):
        """⚠️ A forgotten argument must be a `TypeError` at the call site, not a
        sheet that checks nothing and says it checked everything."""
        import inspect

        for function in (supported_words, unsupported_names, with_the_names_checked):
            for name, parameter in inspect.signature(function).parameters.items():
                assert parameter.default is inspect.Parameter.empty, (
                    f"{function.__name__}({name}=...) can be forgotten silently"
                )

    def test_an_empty_source_finds_every_name_rather_than_none(self):
        """The shape of the failure: if a dropped source made the check pass,
        nothing would ever show it. It must fire on everything instead."""
        reply = {"questions": ["What do you think Alice does next?"]}
        assert "Alice" in flagged(reply, source_text="", approved=())


class TestTheOutcomeCarriesWhatWasChecked:
    def test_the_new_fields_are_on_the_outcome_and_start_off(self):
        """`names_checked` is read to decide whether the label may render, so
        its default has to be the pessimistic one."""
        fields = {f.name: f for f in dataclasses.fields(SourceOutcome)}
        assert fields["names_checked"].default is False
        assert fields["why_names_not_checked"].default == ""
