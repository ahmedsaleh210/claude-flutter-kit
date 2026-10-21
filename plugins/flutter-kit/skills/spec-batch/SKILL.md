---
name: spec-batch
description: Drive spec-based work through planned batches, one batch per session, in a feature-based Riverpod Flutter app. First run (with spec paths) only plans — gap check, open questions, batches — into specs/_progress.md. Each later run (no arguments) implements the next batch end to end — explore, architecture options, implement, review, tests, verify, commit on approval — then hands off to a fresh session.
argument-hint: "[spec files or folder] — omit to continue from specs/_progress.md"
disable-model-invocation: true
---

# Spec batches

`specs/_progress.md` is the memory between sessions: the plan, every decision, and each batch's status. Read it first; keep it current; when it and the conversation disagree, record the user's latest decision in the file.

Pick the mode from `$ARGUMENTS`:
- **Spec paths given → Plan mode.** If `specs/_progress.md` already holds an unfinished plan, ask whether to replace it or add these specs to it.
- **No arguments → Continue mode.** If `specs/_progress.md` doesn't exist, ask which specs to plan.

Talk to the user in their language. Write `_progress.md` in English (decisions may quote the user).

---

## Plan mode — this session plans only, no code

1. **Gap check.** Launch `flutter-kit:spec-gap-checker` on the given specs (and the matching `api-specs/` files). Wait for its report.
2. **Open questions.** Show the one-line summary, then ask every open question at once — grouped by topic, recommendation first, each with its options (AskUserQuestion, up to 4 per call; repeat until done). Record each answer as a decision.
3. **Batches.** Turn the ⚠️/❌ items into batches:
   - each one finishable in one session, independently committable, with tests;
   - ordered data/API → state → UI, and so later batches never wait on unfinished earlier ones;
   - roughly 3–8 batches for a typical spec set; split a batch that touches more than ~2 features.
   Present the list (title, goal, requirements covered) and let the user reorder, merge or split.
4. **Write `specs/_progress.md`** (format below). Record the spec snapshot: `git log -1 --format=%h -- specs api-specs`.
5. **Commit?** Ask before committing `_progress.md`. Never push.
6. **Hand off.** Stop here. Tell the user the first batch's title and: open a new session and run `/spec-batch`.

---

## Continue mode — exactly one batch this session

### 0. Load and check for spec changes
- Read `specs/_progress.md`. Take the batch marked `in-progress`, else the first `pending` one. Mark it `in-progress`.
- **Spec drift:** `git diff --stat <snapshot>..HEAD -- specs api-specs` (plus uncommitted spec changes). If anything changed, run `flutter-kit:spec-gap-checker` on the changed files only, show what it means for the remaining batches (new work, changed work, now-obsolete work), and update the plan and the snapshot once the user agrees.
- Say in one line which batch you're starting and what it covers.

### 1. Explore
Launch 2–3 exploration agents in parallel (`feature-dev:code-explorer` if available, else `Explore`), each with a distinct target: the code this batch changes, the closest existing feature that does something similar, and the UI/core building blocks to reuse. Then read the key files they point to yourself.

### 2. Clarify
If the batch needs answers the recorded decisions don't cover, ask them now — grouped, recommendation first. Record the answers in `_progress.md`.

### 3. Architecture
If the batch involves anything under CLAUDE.md "Architecture decisions — ask before applying" (provider count/type/lifetime, file layout, new shared abstraction, state shape): present the options — recommendation first, one-line trade-off each — and **wait**. Otherwise proceed without asking.

### 4. Implement
Follow CLAUDE.md and the plugin's skills (`riverpod`, `wire-endpoint`, `pagination`, `i18n`, `figma-screen`, `photo-upload-field`, `auth-flow-gotchas`). Run `build_runner` after provider/asset changes. Finish with `flutter analyze` clean.

### 5. Review — show first, apply on approval
- Run `/review-batch` on this batch. **Last batch of the plan → `/review-batch full`** (also runs `/simplify` after the fixes are settled).
- Present the merged findings and **wait** for the user to choose what to apply. Apply only those, then `flutter analyze` again.

### 6. Tests
Launch `flutter-kit:test-writer` on this batch's scope. Then run `flutter test` for the touched features (the full suite if `core/`, `config/`, assets or pubspec changed). Any bug the tests expose goes back to step 4.

### 7. UI check (UI batches)
If the app is running, verify the changed screens with `/dtd-verify` and say what you actually saw. If it isn't running, say the UI wasn't checked at runtime.

### 8. Update `_progress.md`
Mark the batch `done`, add notes (deviations from the spec, things deferred), add new follow-ups, and record any decisions taken this session.

### 9. Commit — ask first
Show a short summary: what changed, test results, review items skipped. Ask before committing. On yes, commit the code + `_progress.md` with a conventional message. Never push unless asked.

### 10. Hand off
Stop. Tell the user what the next batch is and: open a new session and run `/spec-batch`. If that was the last batch, give the final summary and the open follow-ups instead.

---

## Rules
- **One batch per session.** Don't start the next batch here even if there's context left — unless the user explicitly asks.
- Don't skip review or tests to save time. Don't run `/feature-dev` inside this flow.
- Never loosen or delete a failing test to get green.

## `specs/_progress.md` format
```markdown
# Spec progress — <title>

Specs: specs/a.md, specs/b.md, api-specs/x.json
Spec snapshot: <short hash>   ·   Planned: YYYY-MM-DD

## Decisions
- D1 (YYYY-MM-DD) — <question> → <answer>

## Batches
### 1. <title> — done (abc1234)
Goal: <one line>
Covers: R3, R4, R7
Notes: <after done — deviations, deferred items>

### 2. <title> — in-progress
Goal: …
Covers: …

### 3. <title> — pending
…

## Follow-ups
- <deferred item> (from batch N)

## Gap report
<spec-gap-checker table from planning, updated on spec drift>
```
