# Handover — Class Act Plan mode

Paste the block below into a new session.

---

We are building **Plan mode** for Class Act — a lesson planner for a Year 3 teacher
(ages 7–8) at St Anthony's Catholic Primary, Bromley. One-form entry, many EAL and
SEND pupils, mixed ability, low-motivation intake. Reading, writing and maths are the
school's focus.

**Work in `/Users/graemeheerden/Documents/Claude Code /Class Act`, on branch `plan-mode`.**
Run things with `.venv/bin/python`. Read `/Users/graemeheerden/.claude/plans/yup-is-it-listening-smooth-frost.md`
first — that is the approved plan, including a section on what an adversarial pass already
killed. Do not re-litigate decisions recorded there.

## Done so far (on `plan-mode`, 486 tests passing, up from 221)

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
- **Pupil data**: tick-boxes first, free text optional and warned, "show me what gets
  sent" before transmission. No names, no EHCP records.

## What's next, in order

1. **Worksheet coupling** — the headline feature, and the thing nothing else on the market
   does. A worksheet inherits the lesson's objective and success criteria **verbatim** and
   must produce the evidence each criterion names. Assert `worksheet.objective ==
   lesson.objective` and that every criterion has a section producing its evidence. The
   lesson's objective is already checked verbatim against the spine, so this is the last
   handover in the chain — get it right and the plan, the sheet and the child's book agree.
2. **Word output** in the editable paragraph style: Arial, black and blue only, boxes as
   bordered paragraphs rather than tables. Reuse the low-level helpers in
   `generators/components.py`, not the worksheet-semantic ones.
3. **Amending a single lesson** (Phase 3 stage 3). Editing a spine objective currently says
   the reasons after it may no longer hold; it does not re-check them, and a taught lesson
   cannot yet be re-planned against what actually happened.

Smaller things noticed on the way, none blocking:
- **Changing subject empties the objectives picker** — Streamlit drops a selection that is
  not in the new options. The screen now says so rather than looking like it is loading.
- **A whole unit takes a few minutes** — one call per lesson, roughly a minute or two each.
  The screen shows which lesson it is on. Nothing is cached between runs.

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
  **Three for three so far**: the dropped coverage line, the coverage faked onto the
  assessment lesson, and the connection dropped on a long request. None of the three was
  reachable from a test, and the third was invisible on a single lesson — it only appeared
  when a whole unit ran back to back. Run the *whole* flow, not one step of it.
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
- Whether Version B of `prototype/Worksheet - editing comparison.docx` actually solves
  the copy-into-Word problem in practice.

He is not a coder. Updates go: what's true now, anything blocked on him, then **always**
what's next. No file names, no jargon, no commit SHAs.
