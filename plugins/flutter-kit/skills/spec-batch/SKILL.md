---
name: spec-batch
description: Drive spec-based work through planned batches, one batch per session, in a feature-based Riverpod Flutter app. First run (with spec paths and/or Figma links) only plans — gap check, spec-vs-design check, open questions, batches — into specs/_progress.md; with Figma links and no spec it drafts the spec from the design first. Each later run (no arguments) implements the next batch end to end — explore, architecture options, implement (from its Figma frames, or matching an existing screen when there's no design), review, tests, verify, commit on approval — then hands off to a fresh session.
argument-hint: "[spec files/folder] [Figma links] — omit to continue from specs/_progress.md"
disable-model-invocation: true
---

# Spec batches

`specs/_progress.md` is the memory between sessions: the plan, the design for each screen, every decision, and each batch's status. A new session knows only what's in that file — anything the user said while planning that a later batch needs (Figma links, decisions, which screen to copy) must be written there. Read it first; keep it current; when it and the conversation disagree, record the user's latest decision in the file.

Pick the mode from `$ARGUMENTS`:
- **Spec paths and/or Figma links given → Plan mode.** If `specs/_progress.md` already holds an unfinished plan, ask whether to replace it or add to it.
- **No arguments → Continue mode.** If `specs/_progress.md` doesn't exist, ask what to plan from.

Figma is **optional**. Work can come as spec + design, spec only, or design only — and within one plan some screens may have a design and others not.

Talk to the user in their language. Write `_progress.md` (and any drafted spec) in English; decisions may quote the user.

---

## Plan mode — this session plans only, no code

### 1. Inputs
- **Specs** — the given `specs/*.md`, plus the matching `api-specs/` files.
- **Figma links** — optional. For each one, pull the screenshot and metadata with the Figma tools (see `figma-screen` Step 1) and name the screen it shows. If the Figma tools aren't reachable, record the links as-is and say the design couldn't be read yet.
- **Design only, no spec →** first draft `specs/<feature>-flutter.md` from the frames and the API spec: screens and their purpose, the data each shows, user actions, states (loading / empty / error / each status), validation, endpoints, and an **Open questions** list for what a design can't say (error handling, permissions, edge cases, backend behaviour). **Stop and ask the user to review and correct it** before going on; the reviewed file is the spec from here.

### 2. Gap check
Launch `flutter-kit:spec-gap-checker` on the specs (and matching `api-specs/`). Wait for its report.

### 3. Spec ↔ design check (only when there are Figma links)
Map every frame to the screen it implements, then compare:
- fields, actions or states the spec requires that the design doesn't show;
- elements in the design the spec doesn't mention (or contradicts);
- screens the spec needs that have **no design**.
Each mismatch becomes an open question for step 4.

### 4. Open questions
Show the one-line summary, then ask every open question at once — grouped by topic, recommendation first, each with its options (AskUserQuestion, up to 4 per call; repeat until done). Include:
- the gap check's and the spec ↔ design check's questions;
- **for every screen without a design:** (a) build it to match an existing screen of the same kind — name the closest one (recommended), or (b) wait for the design and defer that batch.
Record each answer as a decision.

### 5. Batches
Turn the ⚠️/❌ items into batches:
- each one finishable in one session, independently committable, with tests;
- ordered data/API → state → UI, so later batches never wait on unfinished earlier ones;
- roughly 3–8 batches for a typical spec set; split a batch that touches more than ~2 features;
- every UI batch carries a **Design** line: its Figma links, or `none — match <existing screen path>`, or `deferred — waiting for design`.
Present the list (title, goal, requirements covered, design) and let the user reorder, merge or split.

### 6. Write `specs/_progress.md`
Use the format below. Record the spec snapshot: `git log -1 --format=%h -- specs api-specs`.

### 7. Commit?
Ask before committing `_progress.md` (and a drafted spec). Never push.

### 8. Hand off
Stop. Tell the user the first batch's title and: open a new session and run `/spec-batch`.

---

## Continue mode — exactly one batch this session

### 0. Load and check for changes
- Read `specs/_progress.md`. Take the batch marked `in-progress`, else the first `pending` one whose design isn't `deferred`. Mark it `in-progress`.
- **Spec drift:** `git diff --stat <snapshot>..HEAD -- specs api-specs` (plus uncommitted spec changes). If anything changed, run `flutter-kit:spec-gap-checker` on the changed files only, show what it means for the remaining batches, and update the plan and snapshot once the user agrees.
- **Deferred designs:** if a deferred batch is next in line, ask whether its design is ready (take the links) or keep it deferred and move on.
- Say in one line which batch you're starting, what it covers, and its design source.

### 1. Explore
Launch 2–3 exploration agents in parallel (`feature-dev:code-explorer` if available, else `Explore`), each with a distinct target: the code this batch changes, the closest existing feature that does something similar, and the UI/core building blocks to reuse. Then read the key files they point to yourself.

### 2. Clarify
If the batch needs answers the recorded decisions don't cover, ask them now — grouped, recommendation first. Record the answers in `_progress.md`.

### 3. Architecture
If the batch involves anything under CLAUDE.md "Architecture decisions — ask before applying" (provider count/type/lifetime, file layout, new shared abstraction, state shape): present the options — recommendation first, one-line trade-off each — and **wait**. Otherwise proceed without asking.

### 4. Implement
Follow CLAUDE.md and the plugin's skills (`riverpod`, `wire-endpoint`, `pagination`, `i18n`, `photo-upload-field`, `auth-flow-gotchas`). For UI, take the batch's **Design** line:
- **Figma links →** build each screen with `figma-screen` from those frames.
- **`none — match <screen>` →** read that screen first and build to it: same core widgets, spacing, radii, shadows and text sizes (type ladder in CLAUDE.md). Don't invent a new visual style; anything the reference doesn't cover, take from the nearest sibling screen.
- The spec decides behaviour; the design decides looks. Where they conflict and no decision is recorded, ask.

Run `build_runner` after provider/asset changes. Finish with `flutter analyze` clean.

### 5. Review — show first, apply on approval
- Run `/review-batch` on this batch. **Last batch of the plan → `/review-batch full`** (also runs `/simplify` after the fixes are settled).
- Present the merged findings and **wait** for the user to choose what to apply. Apply only those, then `flutter analyze` again.

### 6. Tests
Launch `flutter-kit:test-writer` on this batch's scope. Then run `flutter test` for the touched features (the full suite if `core/`, `config/`, assets or pubspec changed). Any bug the tests expose goes back to step 4.

### 7. UI check (UI batches)
If the app is running, check the changed screens with `/dtd-verify` against their design — the Figma frame, or the reference screen for `none — match …` — and say what you actually saw. If it isn't running, say the UI wasn't checked at runtime.

### 8. Update `_progress.md`
Mark the batch `done`, add notes (deviations from the spec or design, things deferred), add new follow-ups, and record any decisions taken this session.

### 9. Commit — ask first
Show a short summary: what changed, test results, review items skipped. Ask before committing. On yes, commit the code + `_progress.md` with a conventional message. Never push unless asked.

### 10. Hand off
Stop. Tell the user what the next batch is and: open a new session and run `/spec-batch`. If that was the last batch, give the final summary, the open follow-ups, and any batches still deferred for design.

---

## Rules
- **One batch per session.** Don't start the next batch here even if there's context left — unless the user explicitly asks.
- Don't skip review or tests to save time. Don't run `/feature-dev` inside this flow.
- Never loosen or delete a failing test to get green.
- A screen with no design is built to match an existing screen — never styled from scratch.

## `specs/_progress.md` format
```markdown
# Spec progress — <title>

Specs: specs/a.md, specs/b.md, api-specs/x.json
Spec snapshot: <short hash>   ·   Planned: YYYY-MM-DD

## Designs
| Screen | Design |
|---|---|
| Wallet overview | <Figma link> |
| Withdrawal history | none — match lib/src/features/earnings/presentation/screens/earnings_screen.dart |
| Bank account form | deferred — waiting for design |

## Decisions
- D1 (YYYY-MM-DD) — <question> → <answer>

## Batches
### 1. <title> — done (abc1234)
Goal: <one line>
Covers: R3, R4, R7
Design: — (no UI)
Notes: <after done — deviations, deferred items>

### 2. <title> — in-progress
Goal: …
Covers: …
Design: <Figma links> | none — match <screen path> | deferred — waiting for design

### 3. <title> — pending
…

## Follow-ups
- <deferred item> (from batch N)

## Gap report
<spec-gap-checker table from planning, updated on spec drift>
```
