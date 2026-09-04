# Handover — Class Act Plan mode

Paste the block below into a new session.

---

We are continuing **Plan mode** for Class Act — a lesson planner for a Year 3 teacher
(ages 7–8) at St Anthony's Catholic Primary, Bromley. One-form entry, many EAL and
SEND pupils, mixed ability, low-motivation intake. Reading, writing and maths are the
school's focus.

**Work in `/Users/graemeheerden/Documents/Claude Code /Class Act`, on branch `plan-mode`.**
Run Python with `.venv/bin/python`. **1,080 tests pass** — 41 of those are one replay per
saved worksheet reply, so the total grows every time the flow is run and is not a number
to match exactly. **Everything is uncommitted and intentionally so** — do not stash,
revert, commit or push without asking.

Read these two first, and do not re-litigate anything recorded in either:

- `HANDOVER.md` in that repo — full state, what is built, what is next
- `/Users/graemeheerden/.claude/plans/yup-is-it-listening-smooth-frost.md` — the approved
  plan, including a section on what an adversarial review already killed

**The goal now is getting it in front of the teacher, not making it better.** Graeme said
on 2026-09-04 that it felt like it was going nowhere after three days, and he was right to:
most of that time went on stopping it inventing things, which is invisible from outside.
That work is done. What is left is small — read "What's next" and resist widening it.

Pick up at step 1 of "What's next".

## Done so far (on `plan-mode`, 1,080 tests passing here, up from 221)

1. **Fixed a live bug**: the app took `objectives[0]` for whatever topic was chosen.
   Topics and objectives are two independent lists per strand that drifted apart, so
   picking "How Fossils Are Formed" produced the objective about comparing rocks — on
   every worksheet built from a non-first topic. Index-pairing does **not** fix it
   (94% of strands have matching lengths but the entries don't line up). The app now
   offers the strand's objectives and the teacher chooses. See `curriculum/selection.py`.
2. **Truncated replies are refused** — `stop_reason` was logged and ignored, so a reply
   cut off at a tidy point parsed cleanly and rendered a short worksheet. See
   `TruncatedResponseError` in `llm/client.py`.
3. **First tests that actually execute `app.py`** — nothing did before; `test_smoke.py`
   deliberately avoids importing it. `tests/test_app_runs.py` uses `streamlit.testing.v1.AppTest`.
4. **Plan mode screen** at `pages/2_Lesson_Plans.py`, added *alongside* the worksheet
   flow — `app.py` is untouched apart from two sidebar links and the objective picker.
5. **Per-subject anchors** (`planning/anchors.py`) and **scheme intake**
   (`planning/scheme_intake.py`) — reading a pasted, uploaded or photographed Boost plan.
6. **Scheme intake wired into the page.** `read_scheme_plan()` is the whole journey in one
   call and the screen shows what came back: the unit title, the coverage she is
   accountable for, the subject leader's assessment, and the lines that are not teachable
   as written. Three things went in alongside it:
   - **Word documents are now readable.** The uploader offered `.docx` and the intake
     refused it — the single likeliest upload of all. `.docx` is extracted rather than
     handed over whole (it has a real text layer and the API has no block type for it),
     walking the body in document order so table rows stay intact and a term heading stays
     attached to the units under it.
   - **A dropped coverage line is caught.** Found by running the real API, not by a test:
     told to "flag a vague entry in the `vague` list", Claude *moved* the line there and
     left it out of `coverage`, so a whole lesson vanished off the record while the
     extraction looked clean. The prompt now says a flagged line appears in both lists
     (verified live, twice), and anything flagged but missing from the coverage is shown to
     her by name — never silently restored, which is how an invented line would get in.
   - **A stale reading says so.** Edit the plan after reading it and the screen says the
     coverage below is the older version. It is what she would hand a subject leader.
7. **The unit spine** (`planning/spine.py`) — the chain of objectives, each saying which
   earlier lesson it needs *and why*, with the objectives editable on screen before
   anything longer is written. Plus the coverage map: every line the scheme named, and
   which lesson now teaches it, with gaps shown rather than omitted.
   - **Maths never reaches the model.** `build_locked_spine` assembles the spine from the
     small steps she typed, in her order, word for word — no API call in the path at all.
     `generate_spine` also refuses a locked subject outright, so there are two independent
     defences; deleting the screen's route was measured to produce zero model calls.
   - **Deterministic checks only**, all of them structural: count matches the request, the
     numbering runs 1..n, a lesson cannot build on itself or on one that comes later, the
     reason cannot be blank, no objective appears twice, only the last lesson assesses the
     outcome, and no lesson may claim coverage the scheme never named.
   - **Coverage assessed but never taught.** Second live-only defect: told every scheme
     line had to be taught, the draft attached *"recognise that soils are made from
     rocks"* to a final lesson about grouping rocks. Dropped in substance while the map
     vouched for it. The prompt now says an honest gap beats a false entry, and
     `coverage_never_taught()` catches a line whose only lesson is the assessment.
     Verified live twice: soil now gets its own lesson.
8. **The lessons themselves** (`planning/lesson.py`) — at the depth she rejected v1 for.
   Every step carries what is on the board, the words to say, the questions with the answers
   to expect, what the children do, the common wrong answer and how to respond, and where
   the other adult is. Plus vocabulary in three bands, misconceptions, resources with
   quantities, adaptations, and an assessment naming work that has **not** met the criterion.
   - **The objective is hers, word for word.** Sent in and checked on the way back, exactly.
     `approved_spine()` applies her on-screen edits *before* the lessons are written — without
     it the approval step is decoration. Written one lesson per call, in sequence, each
     knowing what came before and what is still to come.
   - **Structural checks only**: timings sum to the lesson she actually has, 2–5 criteria each
     naming evidence, effort-not-evidence criteria rejected, all three vocabulary bands present
     and no word in two of them, an adaptation may not announce a different objective.
     A failure part-way keeps the lessons already written and says which are missing.
   - **Streaming, not a longer timeout.** Third live-only defect: at this depth a lesson runs
     past the 60-second client default, and raising the timeout only moved the failure to the
     server closing the connection. Anthropic's guidance is to stream a long output; the
     shared client now takes a `stream` flag and the worksheet path is untouched. Verified
     live: a three-lesson unit wrote end to end in 3m44s (61s, 92s, 66s).

9. **Worksheet coupling** (`planning/worksheet.py`) — the headline feature. A worksheet is
   built from a lesson, inherits its objective and success criteria **word for word**, and
   has to produce the evidence each criterion names. Wired into the plan page: a kind-of-task
   and pitched-for picker on every written lesson, then the sheet with each criterion set
   against the task that evidences it.
   - **The claim is checked against the sheet, not taken on trust.** Each criterion must name
     where it is evidenced, what the child records there, and **quote the instruction** — and
     the quote is searched for in the worksheet *with the claims stripped out*, because
     searching the whole reply would let every quote match itself. This caught a real
     fabrication live: a cloze sheet claimed *"Dead plants and insects decay in the soil"* was
     the task, and that sentence appears nowhere except inside the claim.
   - **Reading is not evidence** — a criterion whose part of the sheet has the child record
     nothing is rejected, as is an invented criterion, a dropped one and a reworded one.
   - **Her criteria are printed in her order**, whatever order came back, and the sheet is
     rejected if the generator could not render it.
   - Four live-only defects, none reachable from a test. Three were **my guard refusing
     correct work**: a word-bank sentence stored as fragments with the gaps between them; a
     cloze passage stored as `paragraphs`, a list of lists of pieces with no `pieces` key to
     spot; and a gap drawn as `[hard/soft]` or `_____` rather than filled in. The fourth was
     the model dropping `success_criteria` from word-bank sheets three runs running — now it
     is filled in from the lesson rather than demanded, because the sheet prints hers anyway
     and the evidence array is what actually proves the sheet was built to them.
   - Verified live end to end seven times across word-bank, cloze and investigation sheets;
     the last two runs made 4 of 4 with none refused.

10. **The lost lesson** (2026-09-03) — a unit lost about one lesson in three, from two
   separate causes. Both addressed, and the whole flow re-run live four times.
   - **The reply is now constrained to a schema, not asked for in prose.**
     `output_config.format` with a JSON schema goes with every lesson request, so the
     reply is shaped as it is generated. This is Anthropic's documented answer and it
     replaced the failure entirely: **40 live calls across four runs, zero unparseable
     replies**, against several in the seven runs before. It is visible in the artefacts —
     the spine, which sends no schema, still comes back wrapped in markdown fences, and
     the lessons come back as bare JSON. The schema lives beside the lesson prompt and
     mirrors it field for field, because every object closes with
     `additionalProperties: false` and a field the prompt asks for but the schema omits
     could not be written at all. It is deliberately constant between lessons: the
     compiled grammar is cached for 24 hours and keyed on the schema, so pinning the
     objective per lesson with `const` would pay a compile on every call to re-buy a
     guarantee the validator already gives. **The worksheet path is deliberately left
     unconstrained** and a test holds it that way — see "what's next".
   - **A lesson that fails its own checks is asked for once more, not thrown away.**
     Not a retry: the attempt goes back with the one reason it was refused, which is
     information the first ask did not have. Verified live — a lesson refused at 55
     minutes came back at 60 with the teaching in all four steps word for word and the
     criteria and vocabulary untouched. The checks did not move: the repaired lesson goes
     through the same `validate_lesson`, a second failure is refused, and only a failed
     *check* is repairable — a reply that ran out of room or came back unusable is a
     problem with the request, and sending it again only doubles the cost of finding out.
   - **Three defects in that repair, all found live, none reachable from a test.**
     A refusal saying *"Step 6 has no time on it"* only described what the model had
     deliberately done, so it returned a byte-identical lesson: refusals now name the
     step and say what would fix it. Telling it to *"fix that and change nothing else"*
     was a contradiction, because a step with no time can only be fixed by taking minutes
     from a step that has them: it now asks for the teaching to be kept and expects the
     timings to move. And the timing check reported the first fault it met, so a lesson
     that was both 70 minutes long *and* hiding the overrun in a zero-minute plenary was
     told about the plenary, fixed it, and was lost to the overrun nobody had mentioned:
     timing faults are now reported together, with what the steps currently add up to.
   - **`scripts/live_run.py`** is the harness that found all of this. It runs the whole
     flow — spine, every lesson, a worksheet for each — and writes every request, schema
     and raw reply to `live-runs/<timestamp>/` **before** anything is parsed. Three of the
     four worksheet defects had produced an identical error message from three different
     causes; reading the artefact settled each of today's in a minute.
   - **Where it stands, measured.** Four runs of the whole flow: 14 lessons of 16, 13
     worksheets of 14. The first two runs were measuring earlier states of the fix, so the
     honest number for the code as it stands is the last two runs — **8 lessons of 8, with
     three repairs fired and all three successful**, and one worksheet lost to something
     else (below). Two runs is not seven; treat it as promising rather than settled, and
     run `scripts/live_run.py` again before believing it.

11. **The fourth "guard refuses correct work" (2026-09-03)** — closed, and the answer
   turned out to apply to the lesson lane too. Three live runs of the whole flow today;
   the last one, carrying everything below, was **4 lessons of 4 and 4 worksheets of 4
   with nothing lost** — the first clean run there has been.
   - **The guard was right and did not move.** The quote genuinely was not on the sheet,
     and the same check has caught a real fabrication, so widening the search would let
     that back in. Two positive controls confirm it: loosening the search to accept a long
     enough run of the quote breaks six tests, and searching the sheet as one blob instead
     of as separate tasks breaks two.
   - **What was actually wrong is that a correct sheet was thrown away over a mis-copied
     pointer.** So the sheet is now asked for **once** more, carrying the attempt and every
     reason it was refused, and the second reply goes through exactly the same checks. A
     second failure is refused. This is the pattern the lesson lane already had.
   - **The contract had no conforming move for the case that failed.** Asked to quote "one
     sentence, question or instruction", a model evidencing a results-table column has none
     of those to quote — a heading is not an instruction — so it wrote a sentence about the
     column. The prompt now says a heading is quotable, that a table column is quoted by
     its heading, and shows a description beside the quote it should have been.
   - **The inferred hole was real, and is now measured.** The printed objective, success
     criteria and title were searchable pieces of the sheet, so a quote matching nothing but
     one of them passed. They are the header, not tasks. Left out by key and never by text,
     so a sheet that asks the child to tick a criterion off can still quote that instruction.
   - **Every fault is now reported together, and every refusal says what would fix it.**
     Both were laws the lesson lane earned the day before, and both became load-bearing here
     the moment a refused sheet started being asked for again — a refusal naming the first
     fault it meets gets that one fixed and loses the sheet to the second.
   - **Measured live, four times over.** The exact failure recurred on the last run: a cloze
     sentence quoted as *"In your mission report, you write: '...'"* — the sheet's own words
     wrapped in a description of where they appear. Refused, told what to do, and fixed in
     one attempt with the other two claims byte-identical. Across the three runs the
     worksheet lane made **10 of 10 with four repairs fired and all four successful**; two of
     them moved a claim off a reading passage and onto the place the child actually writes,
     so the sheet came back better rather than merely passing.

12. **The same law, twice more in the lesson lane (2026-09-03)** — both found by the live
   runs above, neither reachable from a test, and each cost a lesson on the run that found it.
   - **A refusal that names one fault loses the lesson to the next.** A fossils lesson came
     back as a single 8-minute step in a 60-minute lesson — complete JSON, nothing the schema
     can prevent, since structured output has no `minItems`. Told only *"a lesson needs at
     least two steps"*, the repair produced six and gave the last one 0 minutes. That refusal
     now carries the whole timing contract, and the per-step content checks are collected and
     reported together instead of refusing on the first missing field they meet.
   - **A total is a verdict; a repair needs the arithmetic.** A lesson came back at 70 minutes
     in a 60-minute lesson, was told exactly that, and the repair came back at 45 — it redid
     the timings from scratch and overshot. The refusal now says how many minutes have to move
     and what each step currently costs, and asks for as few steps to change as possible.
   - `scripts/live_run.py` now records every second attempt and whether it worked, in
     `results.json`. Until today that number existed only as logging interleaved with the
     printed output, so a saved run said how many lessons were lost and nothing about how
     many were saved.

13. **The lesson plan as a Word document (2026-09-03)** — `generators/lesson_plan.py`,
   downloadable from every written lesson on the plan page.
   - **Zero tables.** Every box is a paragraph with a border; Word merges consecutive
     paragraphs carrying identical borders into one visual box, so the objective and all
     the criteria sit in a single box that is still ordinary, typeable, reflowing text.
     Measured on four real lessons from the last live run: 0 tables, ~135 paragraphs each.
   - **Twelve named styles, all `CA `-prefixed, nothing formatted on the run.** One style,
     one meaning: reading a real generated plan showed the objective style also carrying
     the misconceptions and the worksheet's criteria, which would silently restyle those
     the moment she restyled the objective — the exact feature the styles exist for. Split
     into `Item` and `Tick`, with a test that the objective style carries the objective and
     nothing else.
   - **Arial, black and blue**, with the font a setting on the screen. The joined
     handwriting font and Comic Sans are absent from the picker rather than left to her to
     avoid. Nothing here imports `FONT_NAME`, which is still Comic Sans for the ten
     worksheet generators — **retiring that globally is a separate job and was not done.**
   - **The test that matters is `test_every_word_of_the_lesson_reaches_the_document`.** It
     walks the lesson rather than naming its fields, so a field added later and never
     rendered fails it without anyone remembering to come back. A plan missing its
     misconceptions still looks like a plan. Deliberately a test and not a check in the
     generator: refusing to produce the document over a rendering bug would take the plan
     away from her the night before she teaches it.
   - **It says which task on the sheet proves which criterion**, when she has made one —
     and says nothing about a worksheet when she has not. The one thing it refuses is a
     sheet built from a different lesson.
   - ⚠️ **Not opened in Word.** LibreOffice is not on this machine and `textutil` drops
     paragraph borders, so the HTML it produces shows no boxes and is not evidence.
     Verified instead by reading the document's own XML — nine consecutive paragraphs, one
     identical border signature — and by reading the text in order. **Opening it in Word is
     still Graeme's check**, and it is the same one already open about the prototype.

14. **Comic Sans and the six-colour scheme retired across all ten worksheet generators
   (2026-09-03).** The typography decision now covers what it always said it covered.
   - **Every sheet is Arial, black and blue.** `tests/test_worksheet_typography.py`
     renders all ten types at all three levels, plus the answer keys and four themes, and
     holds every colour and every font it finds to one palette. The dict *shapes* in
     `generators/styles.py` are unchanged — only the values — so no generator had to move.
   - **The themes keep their language and lose their palettes.** *Mission*, *Captain's
     Log*, the rocket: that is what a Year 3 class responds to, and it is not colour.
   - **Colour was the only carrier in exactly one place**, and a palette test cannot see
     it: a sentence-builder word card printed the word and nothing else, with the kind of
     word held entirely in the fill. The cards now carry the symbol. Retiring the colours
     without that would have deleted the thing a child sorts by.
   - 🔑 **Two word types shared a mark.** Languages offers *describing word* and *key
     word* and both were a star; the fill colour was what told them apart, and inline in
     a cloze sentence the symbol is all there is. `vocabulary` is now a key. There is a
     test that no subject offers two types with the same symbol.
   - ⚠️ **The sheets went on telling children to match colours.** Found by reading a
     rendered sheet, invisible to every palette check: *"Match the colour and symbol to
     find the right word"* and *"Write your own sentence using a word from each colour
     group"* — the second of which the model was being **told to write**. All of it now
     says symbol. There is a test over the rendered sheets *and* the prompts.
   - **The font is one setting, not several hundred.** `set_run_font` no longer names the
     typeface on every run; runs inherit `Normal`, which `create_base_document` sets once
     from a `font` argument every generator now takes. A picker sits in the accessibility
     block on the worksheet screen and on each lesson plan. The joined handwriting font
     and Comic Sans are **absent from both lists** rather than left to her to avoid. This
     also makes select-all-and-change-the-font work in Word, which it never did.
   - **A guard that would have refused correct work, caught before it shipped.** The first
     version of the no-colour test matched a bare "colour" and flagged the UK-spelling
     instruction — *"use 'colour' not 'color'"* — which is correct and needed. Narrowed to
     the actual construction. Same failure class as the four on the worksheet coupling.
   - Also fixed on the way: `SUBJECT_WORD_TYPES` was sending the model the literal text
     `\\u23f0` where a symbol was meant, in every subject. It never reached a sheet, because
     the generator overrides the label — but it was a false instruction, and a sweep that
     fixed the obvious lines left the `open` line untouched because its trailing
     "(ONLY for greater_depth)" put it outside the pattern.

15. **A schema per worksheet type, and the hole reading the artefacts found (2026-09-03).**
   `planning/worksheet_schema.py` — ten schemas, one per type, each mirroring its own
   prompt field for field and sent with both the first ask and the repair.
   - **Per type, not one.** The objection recorded against a single schema was right and
     does not apply here: `paragraphs` is what a cloze sheet *is*, and it does not have to
     be legal on a times-tables sheet. Every schema is checked against content the
     generators already render — the ten fixtures, plus all 28 worksheet replies ever
     saved — so a schema that forbids working work fails a test rather than a teacher.
   - ⚠️ **It is not buying what the lesson one bought.** The lesson schema replaced replies
     that came back as invalid JSON at 20–25k characters. **None of the 28 saved worksheet
     replies failed to parse**; they run a third the length (median 5,958 chars against
     18,238). Do not repeat the parse-safety justification for this path — it was not true.
   - 🔑 **What it is buying, measured.** Of 87 evidence claims across every saved reply,
     **six quoted text that no generator prints.** Both investigation sheets on the 11:51
     run answered all three of their criteria out of `sorting_section`, `job_section` and
     `explanation_section` — keys the prompt never asks for and the generator has never
     heard of. The coupling check passed them and the run recorded the worksheets as made.
     The sheet the child would have been handed had none of it on it. The same two replies
     are the only two of eight that dropped `conclusion_prompts`, the one place on that
     sheet a child writes in prose: told to change the sheet rather than the criterion, the
     model added tasks, correctly, and put them where nothing would print them.
   - **So the guard was tightened to match**: `_sheet_pieces` searches only the keys that
     kind of generator renders, and `RENDERED_KEYS` is re-derived from the generator source
     in the tests so it cannot drift. Replaying every saved claim through both versions:
     **78 of 78 that pointed at something a child would see still pass, and only those six
     stop passing.** Tightened, never softened.
   - **A closed schema needs a conforming move.** The prompt tells the sheet to add a task
     rather than touch a criterion; with the reply constrained, "add a task" has exactly one
     legal form, so the prompt now says it — in a field this worksheet already has, because
     an invented one is not printed. Same law as the table column, and it was what the model
     actually got wrong.
   - **A sheet with nothing printable says so.** Three types need only a title to reach the
     evidence check, so a sheet in the wrong kind's shape used to be refused once per
     criterion with "your quote is not on the worksheet" — true, and the most useless
     refusal there is. It now names the fault one step up.
   - **Verified live, twice.** Every call parsed. Across both runs, **nine worksheet replies,
     zero keys beyond what a generator prints, and every one satisfies its own schema** —
     which is the thing this was built to stop. The constraint is visibly enforced rather
     than merely sent: the previous run's worksheet replies came back wrapped in markdown
     fences, tonight's come back as bare JSON. Accepted sheets were rendered to `.docx` and
     read, and every accepted claim is on the page the child gets.
   - ⚠️ **But the worksheet hit rate went down, and two runs cannot say why.** Runs: lessons
     3 of 4 then **4 of 4**; worksheets 2 of 3 then 3 of 4 — **5 of 7 against 10 of 10 on the
     three runs before.** Both losses were read off the artefacts and neither is the schema
     or the narrowing: one quoted `'Rock 1 name:'` (12 own-word characters, refused by
     `MIN_QUOTE_CHARS`, which I did not touch), the other welded a passage across four
     separate paragraphs — **measured as refused by the old search too**. What two runs
     *cannot* settle is whether a closed schema makes such quotes more likely, by leaving
     the model fewer places to point at. Do not record this change as neutral on hit rate;
     run the flow a few more times before believing either way.
     **Update 2026-09-04: the next run was 4 of 4**, so it now reads 5 of 7 then 4 of 4
     against 10 of 10. Still three runs on a lane that loses roughly one sheet in eight —
     nowhere near enough to call it either way, and the question is still open.
   - 🔑 **The positive control was run on all of it.** Eight new mutations in
     `scripts/mutate.py`, each caught, including the two that matter most — searching a key
     no generator prints, and opening a schema's shape.

16. **The model quoting the wrong line of its own worksheet (2026-09-04).** The
   refusal named the right move both times and left the model to find it. The
   search did not move; what changed is what the refusal makes findable.
   - **What was actually wrong, read off the artefacts.** A word-bank sheet
     quoted `'Rock 1 name:'` and was told to quote *"the instruction or question
     the child reads before writing"* — with an instruction doing exactly that
     sitting on the same activity. It quoted the label again and the repair came
     back **shorter**. A cloze sheet quoted its fossil passage as one sentence
     when the sheet prints it as four paragraphs, and was told to copy *"that
     part's own words"* without ever being told which parts there were.
   - **So a refusal now carries the sheet's own lines**, verbatim, where the
     quote appears — printed one per line, with an instruction to copy exactly
     one. Where nothing prints the quote whole, it is split at its sentences and
     the parts that *are* printed come back, which is the welded case.
   - 🔑 **It is scoped to the quote, and it is never a menu.** A quote that
     appears nowhere on the sheet is offered **nothing**, and that is the whole
     design: handing a fabricated claim a list of lines it could quote instead
     would let it pick any passing line and evidence a criterion with a task that
     does not produce it. A false pass is worse than the refusal it replaces.
   - **Measured on every worksheet reply ever saved before writing any of it** —
     37 replies, 114 evidence claims. **100 accepted before the change and 100
     after, so the search provably did not move.** Of the 14 refusals, **7 now
     carry a line the sheet really prints** (never more than three) and 7 carry
     nothing — and all seven of those are the invented-key sheets and the
     column-description, i.e. exactly the ones that should get no help.
   - **The guarantee is a test, not a claim.** The lines offered come from a
     narrower walk than the one the check searches — no half-sentences, no hints,
     no two prompts run together. Two walks can drift, so every line offered is
     quoted back through the real check.
   - 🔑 **The positive control found something the tests could not.** Seven new
     mutations, all caught — but one *existing* mutation went silent:
     `NOTHING FAILED` on the one that opens the printed-keys filter, which is the
     guard closing the whole 2026-09-03 hole. Cause: I had written that filter out
     a second time, so the mutation landed on the copy and left the real guard
     untouched. It is now one function called twice. ⚠️ **Duplicating a guarded
     line silently disarms its mutation**, and only the control can see that.
   - **Live, and the honest version of it.** A full flow ran **4 lessons of 4 and
     4 worksheets of 4** — which *does not verify this change at all*, because
     nothing was refused, so nothing read the new refusal. So the two lost sheets
     were replayed through it against the real API. The word-bank sheet **copied
     the offered line exactly and was accepted** — the sheet that was lost is now
     saved. The cloze sheet also copied its offered line exactly and was **still
     refused**, because its repair had deleted three of the four sections while
     quoting them. ⚠️ **A repair may rewrite the sheet, and a line copied out of
     the attempt is then genuinely no longer on it.** That is the guard being
     right, not the offer being wrong.
   - ⚠️ **A suspicion I had, tested and refuted.** *"Copy ONE of them exactly, and
     nothing else"* looked like it could read as an instruction about the sheet
     rather than the quote. Three samples each of the old refusal, this wording,
     and a reword: the old refusal shrank the sheet **every time** (3, 2, 3
     sections of 4) and was accepted 2 of 3; this wording kept all four sections
     **every time** and was accepted 3 of 3. The truncation is not caused by the
     lines and the reword fixes nothing, so **the wording did not change**. Raw
     replies and the script are in `live-runs/2026-09-04-replay-refusal-wording/`.
   - **Four full runs since (2026-09-04): worksheets 15 of 15, lessons 15 of 16.**
     Against 5 of 7 on the two runs before, and 23 of 24 across the seven before
     that. And the number that says most: **the worksheet second attempt had never
     once succeeded — 0 of 2 — and is now 2 of 2.**
   - 🔑 ⚠️ **But do not attribute those two recoveries to this change, because
     neither used it.** All five faults across those two refused sheets were quotes
     that appear nowhere on the sheet at all — the invented-text family, which by
     design is handed **no lines** — and both were repaired by the instruction that
     was already there. **In four live runs the lines have fired zero times.** The
     only live evidence for them is the replay of the sheet that was lost. What the
     corpus says is that they *would* fire on 7 of the 14 refusals ever recorded;
     what the flow says so far is that the family they answer is the rarer one.
     Keep running it, and check whether a refusal carried lines before crediting it.
   - ⚠️ **The lesson lost on the second run is an old defect, not a new one**: refused
     at 70 minutes, told exactly 10 had to come out, and the repair came back at 65.
     That is the "repair overshoots the arithmetic" family already recorded at
     item 12, recurring with the arithmetic in front of it.

17. **Saving (2026-09-04)** — `planning/library.py`. Until this there was no
   database and no saved anything: she could read a scheme, approve a sequence,
   wait several minutes for every lesson to be written, generate the worksheets,
   and lose all of it by closing the tab. **Measured, not assumed** — there was no
   `data/` folder and no `sqlite` anywhere in the source.
   - **The risk is not losing a unit, it is handing one back different.** So the
     test that matters is `test_every_word_of_the_unit_comes_back`, which walks the
     objects rather than naming their fields — a field added to a lesson later and
     never stored fails there rather than in front of a teacher.
   - **One set of SQL over two databases**, through SQLAlchemy: a file on disk while
     building and testing, Supabase once hosted. Not two hand-written dialects — the
     differences are real (auto-numbering, foreign-key enforcement, parameter style)
     and two definitions of one thing is exactly what produced the day's other bugs.
   - 🔑 **The positive control found two pieces of my own code doing nothing.** A
     lookup that preserved the "taught" mark was dead, because the upsert simply does
     not touch that column; and an explicit delete of a unit's lessons was dead,
     because the cascade had already done it. Both mutations reported `NOTHING
     FAILED`. Replaced by one mechanism each, and both are now caught.
   - ⚠️ **The Postgres half is written and has never been run.** The control that
     swaps the Postgres upsert for the SQLite one still reports `NOTHING FAILED`,
     because the whole suite runs against the file. That is an unguarded guard, not a
     passing one. `tests/test_library.py` now takes `LIBRARY_TEST_URL` and runs every
     one of its tests against a real database: **run it once against the Supabase
     project before trusting a word of the hosted path.**
   - **No pupil data, still.** No names, no SEND detail, no EHCP records, and nowhere
     to put one — with a test over the column names, which runs against the hosted
     database too, so it cannot drift when reflections are added on top.

18. **Where it is going to live (2026-09-04, Graeme).** Two facts from him that
   change the design, and one decision that follows.
   - **It will be hosted**, not run on his Mac, and **she is on Windows**. Hosting is
     why the local file is not enough: on almost all hosting the app's own disk is
     wiped on restart or redeploy, which would take her term's planning with it,
     silently. Windows turns out not to matter for a hosted app — and it **closes the
     Word question**: she has real Word, so opening the document is hers to check.
     Stop listing it as an open item.
   - 🔴 **A separate Supabase organisation, not a second project.** His instruction was
     that it must not clash with Brother Marcus. Measured: there is exactly one
     organisation (`Brother Marcus`) with one project in it, and a second project
     there **costs $10/month and bills to the client's account.** A new organisation is
     free and shares nothing. He has been asked to create it; nothing here can.
   - ⚠️ **Use the session pooler, port 5432** — `aws-<region>.pooler.supabase.com`.
     Checked against Supabase's own docs on 2026-09-04, not assumed: the obvious
     `db.<project>.supabase.co` string is **IPv6-only** without the paid IPv4 add-on,
     and Streamlit's hosting is IPv4-only. It would work on the machine it was written
     on and fail once deployed.
   - Recommended hosting is **Streamlit Community Cloud** (free), which the existing
     password door and daily worksheet ceiling in `access.py` were already built for.

19. **The worksheet she can actually hand out (2026-09-04)** —
   `planning/worksheet_document.py`. **Found by counting, not by guessing:** the
   plan page had **one** download button, for the lesson plan, and imported none
   of the ten generators. So the headline feature made a sheet she could look at
   and could not get out of the app. A worksheet that cannot be printed is not a
   worksheet, and no test noticed because every test stopped at the checked object.
   - **Both documents, from the same object.** The child's copy and the answer key,
     built from `sheet.content` exactly as the checks left it — her objective and
     her criteria already in it, in her order.
   - 🔑 **The guarantee now reaches paper.** `test_every_quote_that_was_checked_is_on_the_page`
     takes the claims the guard accepted and finds each one in the rendered
     document. That is the 2026-09-03 hole closed one step further out: the reply
     and the printed page had quietly stopped being the same object once already.
   - 🚨 **And writing it found that they are still not the same string.** Measured by
     rendering and reading it: the page draws every gap with the word-type symbol
     **and the hint** inside it, so *"The rocket landed on the ___ surface of the
     planet."* reaches the page as *"The rocket landed on the ⭐ __________ (a
     describing word about the surface) surface of the planet."* Both are correct
     and deliberate. **Nothing in the project knew it.** Anyone comparing a reply to
     a printed sheet literally will get a false negative on correct work — take the
     symbol and the bracketed hint off first, then use the guard's own matcher.
   - ⚠️ **The coupling fixtures are not renderable sheets.** `worksheet_payload()` in
     the coupling tests stores its cloze sentences under `sentences`, which is enough
     to search for a quote in and is not something the generator can draw
     (`KeyError: 'paragraphs'`). Fine for testing the search; **useless for testing
     what she prints.** A test about the page has to start from `ALL_CONTENT`.
   - ⚠️ **A sheet can pass the coupling checks and still not render.** Measured:
     `validate_worksheet_content` does not check the shape of `word_bank`; the schema
     sent with every request does, so no real reply can be malformed. Belt and braces
     anyway — the download is wrapped, and she is told to make it again rather than
     shown a traceback.
   - **The generator map is a second copy of `app.py`'s, deliberately**, because
     importing `app.py` would execute the whole worksheet flow and there is a recorded
     decision that it stays untouched. The two are pinned by a test that reads
     `app.py` as **text**, with a control that the parse found all ten.
   - **Positive control: five new mutations, all caught**, including building the
     document from something other than the checked sheet.

## Decisions already made — do not reopen

- **White Rose is the only locked scheme.** Maths must never be re-sequenced; the small
  step *is* the objective. Everything else is hers to build. Boost covers science,
  history, geography **and computing**; RE follows Lighting the Path; English runs off
  the school's medium-term plan plus the half-term's RAP text.
- **Publisher content is never reproduced.** She supplies the page; we build around it.
- **Arial everywhere, black and blue only** — for lesson plans *and* worksheets. The
  six-colour word-type scheme is retired; symbols and labels carry the meaning instead,
  which also survives mono photocopying. Comic Sans and Georgia are both out.
- **Word output must be editable**: no single-cell tables. Boxes are paragraphs with
  borders, using real named Word styles. `prototype/make_editable_demo.py` generates a
  side-by-side comparison file proving it — Version B has zero tables.
- **No AI judging AI.** Deterministic checks only, plus the teacher confirming. Output
  is labelled "AI-drafted — check before teaching", never "verified".
- **Plan the whole sequence at once**, then allow amending a single lesson; re-check the
  lessons after an amended one. **Lesson count varies** — suggested from the topic and
  weeks left, never fixed at six.
- 🔴 **No database, for now — decided 2026-09-04 with Graeme.** Saving is written and
  tested (`planning/library.py`, off by default) and is **deliberately not switched
  on**. The output is the Word files she downloads; a database only buys reopening a
  unit, amending one lesson, and the reflections loop. Against that, **Supabase's free
  plan pauses a project after ~7 days of low activity and only the account owner can
  resume it** (their docs, checked 2026-09-04) — so after a half-term break she would
  open a broken app and have to ask Graeme. Ship without it; turn it on if she asks.
- **Pupil data**: tick-boxes first, free text optional and warned, "show me what gets
  sent" before transmission. No names, no EHCP records.

## What's next, in order

1. **Get it hosted so she can open it.** Everything she makes now leaves the app —
   lesson plans, worksheets and answer keys — which was the last thing standing in
   the way. Streamlit Community Cloud, free; the password door and the daily
   worksheet ceiling in `access.py` were built for exactly this. ⚠️ **Saving is
   deliberately off** (decision below), so nothing needs a database to go live.


2. **A repair may quietly rewrite the sheet, and nothing measures that.** Found on
   2026-09-04 and not chased: asked to repair one evidence quote, a cloze sheet came back
   having deleted three of its four sections while still quoting them. The coupling check
   caught it — correctly, because those tasks really were gone — but it reported a bad
   quote, which is the *symptom*. Measured over three samples the old refusal shrank that
   sheet every time and the current one did not, so it is not new and it is not the lines.
   Worth a look: the repair prompt already says *"keep the tasks word for word"*, and a
   structural check that the repair still contains the tasks the attempt had would name the
   real fault instead. ⚠️ Do not build it as a refusal without measuring first — a sheet
   that legitimately adds a task must not be refused for it.

3. **No live coverage of six of the ten worksheet types.** Every live run so far uses
   Science, so only word bank, cloze, matching and investigation have ever been generated
   against the real API. The other six schemas are derived from their prompts and
   generators and checked against the fixtures — but nothing has proved a real model can
   satisfy one. `scripts/live_run.py` would need an English or Maths unit to find out.

4. **Amending a single lesson** (Phase 3 stage 3). Editing a spine objective currently says
   the reasons after it may no longer hold; it does not re-check them, and a taught lesson
   cannot yet be re-planned against what actually happened.

Smaller things noticed on the way, none blocking:
- **Changing subject empties the objectives picker** — Streamlit drops a selection that is
  not in the new options. The screen now says so rather than looking like it is loading.
- **A whole unit takes a few minutes** — one call per lesson, roughly a minute or two each.
  The screen shows which lesson it is on. Nothing is cached between runs.
- ⚠️ **"Soil now gets its own lesson" was true twice and is not a settled fact.** The
  scheme line *"recognise that soils are made from rocks and organic matter"* landed on the
  assessment lesson again on 2026-09-03, and `coverage_never_taught()` caught it and told
  the teacher — which is the design working. The prompt reduces it; the guard is what makes
  it safe. Do not record it as fixed.
- **The coverage map is a declaration, not a reading.** On one run a lesson declared it
  covered both the soil line and the fossils line while its objective named only soil.
  Nothing structural can catch that — deciding whether an objective teaches a line is a
  judgement, and by an existing decision it is hers. She sees the map; that is the answer.

## Working rules that have already earned their place here

- **TDD, genuinely**: write the failing test, confirm it fails, then implement. And
  **run a positive control** — I confirmed the objective tests fail against the old
  behaviour before trusting them. A test that cannot fail proves nothing. This is not
  ceremony: a control on the intake tests caught one that passed either way, asserting
  that a failed read wipes the plan it replaces when no plan was ever there to wipe.
- **A test cannot see a prompt defect. Run it against the real API once.** The intake had
  full unit coverage, a green suite and a genuine RED→GREEN history, and it still silently
  dropped a lesson from the coverage record — because the fault was in how Claude read the
  instruction, and every test used a fake that returned whatever I told it to. One live
  call found it in a minute. Do this for every generation step that follows.
  **Fifteen for fifteen so far**: the dropped coverage line, the coverage faked onto the
  assessment lesson, the connection dropped on a long request, four on the worksheet
  coupling, three on 2026-09-03 in the repair written that morning, three more the same
  afternoon — a lesson arriving as a single 8-minute step, a repair told its total and
  overshooting it the other way, and a refusal naming one missing field while a second step
  was missing another — and the evidence quoted out of a section nothing prints. None was
  reachable from a test, and one was invisible on a single lesson — it only appeared when a
  whole unit ran back to back. Run the *whole* flow, not one step of it, and read
  `results.json` — it now records every second attempt and whether it worked, which is the
  number that says whether the repairs are earning their place.
  🔑 **And the fourteenth was not found by running it — it was found by re-reading runs
  already on disk.** Every artefact ever saved is a corpus, not just the last one: 87
  evidence claims across seven runs, six of them wrong in a way no single run made obvious.
  Sweeping the whole of `live-runs/` is cheap, costs no API calls, and is the only reason
  that defect was ever seen. Do it before adding a guard, not after.
  🔑 **And the fifteenth needed a run that was deliberately made to fail.** On 2026-09-04
  the whole flow came back 4 of 4 and 4 of 4 — and verified nothing about the change that
  session made, because that change was to a *refusal*, and a clean run never reads one.
  **A green live run is not coverage of the failure path.** Replaying two known-bad sheets
  through it found the fifteenth in two calls: asked to repair one quote, a sheet came back
  having deleted three of its four sections. ⚠️ When the thing you changed only fires on
  failure, you have to cause the failure — a passing run is the *control*, not the test.
- **A refusal the model will read is an instruction, not a description.** Earned three
  times over on 2026-09-03. *"Step 6 has no time on it"* is a true and useless sentence: it
  describes exactly what the model had chosen to do, so it changed nothing and returned a
  byte-identical lesson. *"Fix that and change nothing else"* was worse — a contradiction,
  because the only fix took minutes from another step. And a refusal that named the first
  fault it met got that one fixed and lost the lesson to the second. If there is one repair,
  the refusal has to name **everything** wrong, say what it would take to fix it, and carry
  the numbers the fix needs. This costs nothing and is invisible until you run it live.
- **Keep every raw reply, and read the artefact before changing anything.** Three of the four
  worksheet defects looked identical from the error message — "the quote is not on the
  sheet" — and had three different causes, two of which were the guard refusing correct work.
  Guessing from the message would have fixed none of them. Write the live-run script so it
  saves every raw reply to disk *before* parsing it — that is what made all four diagnosable,
  and a reply that fails to parse is gone otherwise. **`scripts/live_run.py` now does this
  for the whole flow** — run it, then read `live-runs/<timestamp>/` rather than reasoning
  from the error text. It also prints the coverage map and the assessed-but-never-taught
  flag, because those refuse nothing: a run that only watched for exceptions called a unit
  clean while the screen was telling the teacher a scheme line was never taught.
- **A guard that refuses correct work is worse than no guard**, because it is invisible on a
  green suite and only shows up as the teacher being told her worksheet is wrong. Three of
  the four were this. But note the fourth: the same check caught a genuine invented task, so
  the answer is to make the guard *right*, never to soften it. **And "right" was not a wider
  search.** It was three things that left the search exactly where it was: a contract with a
  conforming move in it for the case that kept failing, a refusal saying what would fix it,
  and one more attempt. Loosening the search is still the tempting fix and it is still
  wrong — a positive control on 2026-09-03 showed that accepting a long enough run of a
  quote breaks six tests, because a paraphrase and a fabrication look the same from there.
- ⚠️ **But a guard can be wrong in the loose direction too, and every other rule here leans
  the other way.** Five of the failures above are the guard refusing correct work, which
  makes "it refused something" feel like the only shape a guard bug takes. On 2026-09-03
  the coupling check was found *accepting* work it should have refused: six evidence
  quotes, on two whole sheets, pointing at text no generator prints. That is worse than a
  false refusal, not better — a refusal is visible and gets a second attempt, while this
  told the teacher her worksheet evidenced her criteria and handed the child one that
  evidenced nothing. **A green suite and a happy live run look identical either way.** The
  test is not "did anything get refused" but "is the thing this check reads the same thing
  the teacher gets" — here, the reply and the printed page had quietly stopped being the
  same object.
- **Run the positive control on the guard, not just on the feature.** Mutating each part of
  the worksheet and lesson guards in turn on 2026-09-03 found two tests that passed either
  way, and showed that the tests meant to pin the anti-fabrication search were rejecting a
  stitched quote by accident of the order the pieces come out in rather than because each
  piece is searched on its own. **`scripts/mutate.py` does this** — forty mutations,
  each undoing one thing a guard does, printing what failed and putting it back. A mutation
  nothing catches is the finding. Editing the guards stales a mutation; it says so loudly
  and carries on, and re-copying the lines costs a minute.
  ⚠️ **A mutation can also go silent without saying anything, and that is the dangerous
  one.** It is a literal string replaced **once**, so writing a guarded line out a second
  time anywhere in the file sends the mutation to the copy and leaves the real guard
  running. That happened on 2026-09-04: a new helper repeated the filter that decides what
  reaches the page, and the mutation covering the whole 2026-09-03 hole reported
  `NOTHING FAILED` — a guard nobody was checking any more. **Fix it by having one
  definition, not by editing the mutation.** The control only sees this if you run the
  whole file after touching a guard, so run it.
- **Check the current API guidance before changing how a call is made.** The first fix for
  the dropped connection was a longer timeout, which was wrong: the documented answer for
  a long output is to stream it. Guessing cost a live run.
- **Verify claims against the code before repeating them.** A Codex review asserted
  three things about this repo; all three needed checking, and one was a misreading.
- **`app.py` stays structurally untouched.** No refactor. It has almost no coverage and
  it works.
- The prototype is `prototype/plan-mode.html` — open it to see the agreed workflow and
  the target depth for tabs 3 and 6.

## Open with Graeme

- The free Oak National Academy API key (`open-api.thenational.academy`) — he has asked
  but expects not to get it. **Oak must be a bonus, never a dependency**; everything has
  to work without it.
- Which English medium-term plan and RAP text Year 3 is on this half-term.
- 🔴 **A separate free Supabase organisation for Class Act**, with a project inside it in
  London (`eu-west-2`). Asked for 2026-09-04. **Not** a second project in the Brother
  Marcus organisation: measured at $10/month, and it would bill to the client. The
  connection string goes into the hosting's secrets box as `LIBRARY_URL` — never into
  this repository, and never into a chat.
- ✅ **Closed 2026-09-04 — the Word question is the teacher's.** Graeme has no copy of
  Word; she is on Windows and will open it herself. Do not list it as blocking again.

He is not a coder. Updates go: what's true now, anything blocked on him, then **always**
what's next. No file names, no jargon, no commit SHAs.
