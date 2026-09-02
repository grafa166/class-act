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

## Done so far (on `plan-mode`, 345 tests passing, up from 221)

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

1. **Unit spine generation** — the chain of objectives with `builds_on_lesson`, for the
   teacher to approve before anything else is written. The coverage record is waiting for
   it in `st.session_state["plan_scheme_plan"]`, and the spine has to account for every
   line in it: that is the coverage map she shows the subject leader.
2. **Full lesson generation at the agreed depth.** This is the thing the teacher
   rejected v1 for. Not an outline of what a lesson should contain — what actually
   happens: what's on the board, the words to say, the questions and expected answers,
   what to watch for, where the other adult stands. Plus **vocabulary in three bands**
   (everyone / expected / stretch), misconceptions to expect, and assessment that names
   an example of work that has *not* met the criterion.
3. **Worksheet coupling** — the headline feature. A worksheet inherits the lesson's
   objective and success criteria verbatim and must produce the evidence each criterion
   names. Assert `worksheet.objective == lesson.objective` and that every criterion has
   a section producing its evidence.
4. **Word output** in the editable paragraph style.

The **"Plan it"** button is still deliberately disabled — it turns on with step 1, not
before. A shell must not look finished.

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
