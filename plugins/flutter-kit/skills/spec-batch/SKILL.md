---
name: spec-batch
description: Drive spec-based work through planned batches, one batch per session, in a feature-based Riverpod Flutter app. First run (with spec paths and/or Figma links) only plans — gap check, spec-vs-design check, open questions, batches — into its own plan file under specs/_progress/; with Figma links and no spec it drafts the spec from the design first. Each later run (no arguments) implements the next batch end to end — explore, architecture options (two architect agents, only when there's a real structural decision), implement (from its Figma frames, or matching an existing screen when there's no design), review, tests, verify, commit on approval — then hands off to a fresh session.
argument-hint: "[spec files/folder] [Figma links] to plan · [plan name] or nothing to continue"
disable-model-invocation: true
---

# Spec batches

Every plan has its own **plan file**, `specs/_progress/<plan>.md` — one per `/spec-batch` planning run, however many specs it covers. It is the memory between sessions: the plan, the design for each screen, every decision, and each batch's status. A new session knows only what's in that file — anything the user said while planning that a later batch needs (Figma links, decisions, which screen to copy) must be written there. Read it first; keep it current; when it and the conversation disagree, record the user's latest decision in the file. Finished plans stay in the folder as the record of what was built and why.

Pick the mode from `$ARGUMENTS`:
- **Spec paths and/or Figma links → Plan mode** — a new plan.
- **First word names an existing plan** (no `/`, no `.md`, not a URL) **→ Continue mode** for that plan. Words after it are just a label for the session name and are ignored — except `merge` (`/spec-batch <plan> merge`), which goes straight to "Plan worktrees → Final merge".
- **No arguments → Continue mode.** Look at the plan files whose `Status:` is `active`:
  - none → say so (list finished plans, if any) and ask what to plan from;
  - one → continue it;
  - several → ask which, showing each plan's name and its next batch.
- **Legacy:** if an old single-file `specs/_progress.md` exists, offer to move it to `specs/_progress/<name>.md` (ask the name) before anything else.

Figma is **optional**. Work can come as spec + design, spec only, or design only — and within one plan some screens may have a design and others not.

Talk to the user in their language. Write plan files (and any drafted spec) in English; decisions may quote the user.

---

## Plan mode — this session plans only, no code

### 1. Inputs and plan name
- Planning writes no code, so it may run while a batch is in progress in this folder — just mention that batch. It commits only its own plan file.
- **Plan name** — propose a short kebab-case name for this set of specs (e.g. `notifications-marketing`) and confirm it. If `specs/_progress/<name>.md` already exists and is still `active`, ask: add these specs to it, replace it, or pick another name.
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
- **Slice by feature, not by layer.** A batch delivers one thing the user can see or use, end to end: its models/repository, its state, and its UI together. Don't plan a "data" batch followed by "UI" batches over the same screens — that triples the fixed cost per feature (explorers, three reviewers, tests, a session, approvals) and every one of those batches touches the same files.
  - A data-only batch is right only when **several later batches** consume that data (a shared model, a new endpoint used by three screens), or when there is no UI at all.
- **Size:** aim for roughly **300–500 lines of production code** (tests extra) — a whole feature that still finishes in one session. That's a guideline, not a rule: a self-contained small feature can be smaller; don't go much past ~2× that, or reviews lose focus and the session risks compaction. Merge neighbouring small items that touch the same screens.
- Independently committable, with tests; a batch never waits on an unfinished later one — put shared foundations first.
- Every UI batch carries a **Design** line: its Figma links, or `none — match <existing screen path>`, or `deferred — waiting for design`.
Present the list (title, goal, requirements covered, design, rough size) and let the user reorder, merge or split.

### 6. Write the plan file
Create `specs/_progress/<plan>.md` with `Status: active`, using the format below. Record the spec snapshot: `git log -1 --format=%h -- specs api-specs`.

### 7. Commit?
Ask before committing. Stage only the plan file (and a drafted spec) **by path** — never `git add -A`, `git add .` or `commit -a`. Never push.

### 8. Hand off
Stop. Tell the user the first batch's title and: open a new session and run `/spec-batch` (or `/spec-batch <plan>` when more than one plan is active).

---

## Continue mode — exactly one batch this session

### 0. Load, claim, check
1. **Where does this plan live?** Run `git worktree list --porcelain`. If a worktree on branch `plan/<plan>` exists and this session isn't in it, this plan runs there: move the session into it (EnterWorktree with that absolute `path`, if the tool is available) and continue there; otherwise open it with `code <path>` (if the `code` command exists) and tell the user to run `/spec-batch <plan>` in that window, then stop.
2. **Snapshot the working tree.** Run `git status --porcelain` and keep that list as the *pre-existing changes*. If it isn't empty, tell the user which files are already modified — another session's work or something unfinished. They are not this batch's, and this batch will not commit them (step 9).
3. **Is a batch already running in this folder?** Read **every** plan file in this folder's `specs/_progress/` — not just this plan's. A batch marked `in-progress` there (any plan) means another session is, or was, working in this folder. Show it (plan, batch, started when, stage) and offer:
   - (a) that session is still working → **stop here**; one batch per folder at a time.
   - (b) that session ended or was interrupted → take that batch over and **resume** it (item 5). If it belongs to another plan, that means running `/spec-batch <that plan>` — do it here if the user says so.
   - (c) run **this plan in its own worktree**, in parallel — only when the running batch belongs to a *different* plan → follow "Plan worktrees → Create", then come back to item 4 inside the worktree.
4. **Pick the batch** from this plan:
   - **Already `in-progress`** (and not handled by item 3 because it's this plan's own): show its `Session:` line and ask whether that session is still working (stop) or ended/interrupted (take it over and resume — item 5).
   - **Otherwise** the first `pending` batch whose design isn't `deferred`.
   - **Claim it right away**, before exploring: set its heading to `— in-progress` and add `Session: <YYYYMMDD-HHMMSS> · started <YYYY-MM-DD HH:MM> · <folder> · <branch>` and `Stage: exploring`. Save the plan file now, not at the end, so any other session in this folder sees the claim.
5. **Resuming a taken-over batch.** Before any new work, find out what is already done: the batch's `Stage:` and `Notes:`, commits since the plan snapshot that belong to it (`git log`), and the uncommitted files that belong to it (`git diff`, untracked files — told apart from the pre-existing changes). Tell the user what's done and what's left, confirm, and continue from the recorded stage. Never rewrite code that already exists — review it and finish it.
6. **Spec drift:** `git diff --stat <snapshot>..HEAD -- specs api-specs` (plus uncommitted spec changes). If anything changed, run `flutter-kit:spec-gap-checker` on the changed files only, show what it means for the remaining batches, and update the plan and snapshot once the user agrees.
7. **Deferred designs:** if a deferred batch is next in line, ask whether its design is ready (take the links) or keep it deferred and move on.
8. Say in one line which batch you're starting (or resuming), what it covers, and its design source.

**Keep `Stage:` current** as you go — `exploring` → `implementing` → `reviewing` → `testing` → `ready to commit` — and add a short `Notes:` line at each milestone (e.g. "notifier + repo done, screen pending"). That is what lets an interrupted batch resume without redoing work.

### 1. Explore
Launch 2–3 `flutter-kit:code-explorer` subagents in parallel (one message), each with a distinct target: the code this batch changes, the closest existing feature that does something similar, and the UI/core building blocks to reuse. Then read the key files they point to yourself.

### 2. Clarify
If the batch needs answers the recorded decisions don't cover, ask them now — grouped, recommendation first. Record the answers in the plan file.

### 3. Architecture
**Only when the batch involves a real architectural decision** — anything under CLAUDE.md "Architecture decisions — ask before applying": provider count/type/lifetime, file/folder layout, a new shared abstraction in `core/`, state shape. Typical cases: the first state batch of a feature, a new `core/` abstraction, more than one sensible way to structure the files. A batch that follows an existing pattern skips this step entirely — no agents, no question.

When it applies:
1. **Launch two `flutter-kit:code-architect` subagents in parallel** (one message), one per stance. Give each the batch goal and requirements, the recorded decisions, the key files from step 1, and the instruction to follow CLAUDE.md. Ask for a complete blueprint: files to create/change, providers (type, lifetime), state shape, data flow, how it fits the existing patterns, and its trade-offs.
   - **A — stance "minimal change":** extend what already exists; fewest new files and abstractions.
   - **B — stance "clean":** the design that fits the architecture best long-term, even if it touches more code.
2. **Compare** the two blueprints: where they agree, where they differ, and what each costs. If a middle ground beats both, add it as option **C**.
3. **Present** the options — recommendation first, one-line trade-off each, and roughly how many files each touches — and **wait** for the user's choice.
4. **Record** the choice as a decision in the plan file, then build exactly that design in step 4.

### 4. Implement
Follow CLAUDE.md and the plugin's skills (`riverpod`, `wire-endpoint`, `pagination`, `i18n`, `photo-upload-field`, `auth-flow-gotchas`). For UI, take the batch's **Design** line:
- **Figma links →** first make sure the Figma tools answer (fetch the frame's metadata). **If they don't, stop the UI work** and tell the user to open the Figma desktop app with the Dev Mode MCP server enabled (or connect the Figma plugin), then retry. Never build a designed screen from the spec text or from guesswork. Only if the user explicitly says to go ahead without it, build to match an existing screen and add `Design check: pending — Figma unavailable` to the batch notes, so the screen is checked against the design later. Non-UI parts of the batch can continue meanwhile.
  Once the tools answer, build each screen with `figma-screen` from those frames.
- **`none — match <screen>` →** read that screen first and build to it: same core widgets, spacing, radii, shadows and text sizes (type ladder in CLAUDE.md). Don't invent a new visual style; anything the reference doesn't cover, take from the nearest sibling screen.
- The spec decides behaviour; the design decides looks. Where they conflict and no decision is recorded, ask.

Run `build_runner` after provider/asset changes. Finish with `flutter analyze` clean.

### 5. Review — one question: what to apply, and commit after
- Run `/review-batch` on this batch. **Last batch of the plan → `/review-batch full`** (also runs `/simplify` after the fixes are settled).
- Present the merged findings and ask **one** question that covers both decisions: which items to apply, and whether to commit once tests are green — e.g. "Apply 1, 3, 5, then run the tests and commit this batch's files if everything is green?" Offer: apply the recommended ones + commit (recommended) · choose items · apply but don't commit yet.
- Apply only the chosen items, then `flutter analyze` again. The commit answer is used in step 9.

### 6. Tests
Launch `flutter-kit:test-writer` on this batch's scope. Then run `flutter test` for the touched features (the full suite if `core/`, `config/`, assets or pubspec changed). Any bug the tests expose goes back to step 4.

### 7. UI check (UI batches)
If the app is running, **ask the user** whether to check the changed screens with `/dtd-verify` against their design — the Figma frame, or the reference screen for `none — match …` — saying it will reload (and may restart) their running app. Run it only on a clear yes, and say what you actually saw. If they decline or the app isn't running, say the UI wasn't checked at runtime and list the screens to look at.

### 8. Update the plan file
Mark the batch `done` (set `Stage: done`; drop the `Session:` line), add notes (deviations from the spec or design, things deferred), add new follow-ups, and record any decisions taken this session. After the last batch, set the plan's `Status:` to `done`.

### 9. Commit — this batch's files only
- **Regenerate first:** run `dart run build_runner build --delete-conflicting-outputs` (and the strings generator if `lang.json` changed) so every generated file matches the code being committed — a provider whose doc comment changed still changes its `.g.dart`.
- Build the file list: every file this batch created or changed, the plan file, and the generated files that come with them (`*.g.dart` of its providers, `locale_keys.g.dart` / `en.json` / `ar.json` when it changed `lang.json`, `assets.gen.dart` when it added assets).
- Anything from the **pre-existing changes** (step 0) stays out. If this batch also edited one of those files, ask before including it — the commit would carry someone else's change too. Generated files that changed only because an **earlier** commit forgot to regenerate them stay out too — offer them as a separate `chore(gen): regenerate stale generated files` commit.
- **If the user already said "commit" in step 5** and tests are green, the list holds nothing unexpected (no pre-existing or stale files), and no review item was skipped silently → commit without asking again, then show the summary (hash, files, test results). **Otherwise** show the summary and ask.
- Stage **by path** and commit with a conventional message. Never `git add -A`, `git add .` or `git commit -a`. Never push unless asked.

**In a plan worktree** (branch `plan/<plan>`): after the commit, follow "Plan worktrees → Sync" so the plan keeps up with the base branch.

### 10. Hand off
Stop. Tell the user what the next batch is and: open a new session and run `/spec-batch` (or `/spec-batch <plan>` when more than one plan is active). If that was the last batch, give the final summary, the open follow-ups, and any batches still deferred for design — and, in a plan worktree, offer "Plan worktrees → Final merge".

---

## Plan worktrees — running a second plan in parallel

This section only applies when the user picks the worktree option in Continue step 0. **A single plan never uses it** — its batches run in the repo folder, on the current branch, with no worktree, sync or merge.

One batch per folder at a time. To work on two plans at once, the second plan gets its own git worktree — a separate folder of the same repo, **next to it** (`../<repo>--<plan>`), on branch `plan/<plan>` — for its whole life. Next to the repo, not inside it: a worktree inside would show up as untracked in the base folder's `git status` and be picked up by its analyzer and search. Its batches still run one after another, inside that worktree. Batches of the same plan never run in parallel.

### Create (only after the user picks it)
1. If this plan's file isn't committed yet, commit it first (ask; by path), so the worktree has it.
2. `git worktree add ../<repo>--<plan> -b plan/<plan> HEAD` (`<repo>` = this folder's name) — from the local HEAD, so local commits come along. Note the base branch (the branch checked out here) and the absolute path of both folders.
3. **Copy the local files git doesn't carry.** A worktree starts from the last commit — uncommitted and git-ignored files stay behind. Copy these from the base folder into the same paths in the worktree (only if they exist and aren't tracked), and list what you copied:
   - `.env` files at the root (`.env`, `.env.*`) — usually listed as a pubspec asset, so the app won't build without them;
   - `.claude/settings.local.json` — the user's approved permissions;
   - `android/key.properties` and the keystore its `storeFile` points to (path relative to `android/app/`);
   - any other git-ignored file listed under `flutter: assets:` in `pubspec.yaml`.
   Find candidates with `git ls-files --others --ignored --exclude-standard`. Skip build output and what Flutter regenerates (`build/`, `.dart_tool/`, `GeneratedPluginRegistrant.*`, `Generated.xcconfig`, `local.properties`, Pods). These files stay on this machine and are never committed.
4. Move the session in: EnterWorktree with `path:` the new folder's absolute path. If that tool isn't available, run `code <new folder>` (if the `code` command exists), tell the user to run `/spec-batch <plan>` in the new window, and stop.
5. Inside the worktree: `flutter pub get`, then `dart run build_runner build --delete-conflicting-outputs`.
6. Add to the plan file header: `Worktree: ../<repo>--<plan> · branch plan/<plan> · base <base>`, and continue the batch right here.

### Sync — after every batch commit in the worktree
Bring the base branch in, so conflicts are solved here and never in the base folder:
1. `git merge <base>` (inside the worktree).
2. Resolve conflicts by kind:
   - **Generated files** (`en.json`, `ar.json`, `locale_keys.g.dart`, `*.g.dart`, `assets.gen.dart`, `pubspec.lock`): never hand-merge — take either side, then regenerate.
   - **`lang.json`**: keep both sides' keys; make sure the JSON is valid and no key is duplicated.
   - **Additive lists** (`ApiConstants`, barrels, `pubspec.yaml` dependencies, plan files' Decisions/Follow-ups): keep both sides.
   - **Real code conflicts** (same widget, notifier or model changed on both sides): show both versions and ask.
3. Regenerate: `flutter pub get`, `dart run generate/strings/main.dart` (stop it after it prints success if it starts a watcher), `dart run build_runner build --delete-conflicting-outputs`.
4. `flutter analyze` and `flutter test` — a merge can compile-break without any textual conflict (a renamed method used elsewhere). Fix before committing.
5. Ask, then commit the merge.

### Final merge — after the last batch, or `/spec-batch <plan> merge`
1. Check the base folder is idle: no batch `in-progress` in its plan files, and `git -C <base folder> status --porcelain` is empty. If not, say what's blocking and stop — never merge into a folder where a session is working.
2. Sync once more (above), and set the plan's `Status: done` in the worktree.
3. Ask, then `git -C <base folder> merge --no-ff plan/<plan>`. It should be clean after the sync; if it isn't, `git -C <base folder> merge --abort` and report.
4. Run `flutter analyze` and `flutter test` in the base folder.
5. Cleanup, after asking: return the session to the base folder (ExitWorktree with `action: keep`), then `git worktree remove ../<repo>--<plan>` and `git branch -d plan/<plan>`.
Never push.

---

## Rules
- **One batch per session, one running batch per folder.** Don't start the next batch here even if there's context left — unless the user explicitly asks.
- Don't skip review or tests to save time. Don't run `/feature-dev` inside this flow.
- Never loosen or delete a failing test to get green.
- Never stage with `git add -A`, `git add .` or `git commit -a` — only this batch's files, by path.
- **Don't end your turn in the middle of a batch.** End it only when you're asking the user something, or when the batch is handed off. While subagents run, wait for their results and keep going; if something blocks you, say what and ask.
- **Session names come from a hook**, not from you: the plugin's UserPromptSubmit hook names the session from the plan file (`<plan> · Batch N: <title>`) when the first prompt is `/spec-batch`. If the user says the name is wrong, check the plan file's batch headings (`### N. <title> — <status>`), and tell them they can rename it (`/rename`, or Rename in the session list).
- A screen with no design is built to match an existing screen — never styled from scratch.

## Plan file format — `specs/_progress/<plan>.md`
```markdown
# Spec plan — <plan>

Status: active | done
Worktree: ../<repo>--<plan> · branch plan/<plan> · base main   (only for a plan running in a worktree)
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
Stage: done
Notes: <after done — deviations, deferred items>

### 2. <title> — in-progress
Goal: …
Covers: …
Design: <Figma links> | none — match <screen path> | deferred — waiting for design
Session: 20261022-171500 · started 2026-10-22 17:15 · romway-provider · main
Stage: implementing
Notes: repository + notifier done; screen next

### 3. <title> — pending
…

## Follow-ups
- <deferred item> (from batch N)

## Gap report
<spec-gap-checker table from planning, updated on spec drift>
```
