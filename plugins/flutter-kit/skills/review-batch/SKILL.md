---
name: review-batch
description: Review the current batch of work with the project's reviewer agents. Default mode (every batch) runs correctness-reviewer, code-smells-reviewer and architecture-reviewer in parallel on the batch and merges their findings into one report. `full` mode (end of a feature) reviews the last batch the same way, adds a cross-batch architecture pass over the whole feature, then runs /simplify on the whole feature. Use when the user says "review the batch", "راجع الدفعة", "/review-batch", or "/review-batch full" at the end of a feature.
argument-hint: "[full] [scope — files, commit range or feature]"
---

# Review a batch

Arguments: `$ARGUMENTS`. If they contain the word `full` → **full mode**; anything else is the scope. No `full` → **batch mode**.

| Mode | When | Runs |
|---|---|---|
| batch (default) | after every batch | correctness-reviewer + code-smells-reviewer + architecture-reviewer, in parallel |
| full | once, at the end of a feature | correctness + smells on the **last batch**; architecture on the **whole feature** (cross-batch only); then `/simplify` on the whole feature |

Never run full mode after every batch — `/simplify` is ~80% of review cost; it runs once per feature.

## Step 1 — Fix the scope
- **Tests are part of the scope**: the batch's new and changed files under `test/` go to correctness and smells with the code. Write them first (`flutter-kit:test-writer`) when they don't exist yet — a review that never sees the tests can't tell a test that can't fail from one that guards the behaviour.
- **Batch mode:** the user's scope if given; otherwise the uncommitted changes (`git diff HEAD --name-only` + untracked files under `lib/` and `test/`). If the tree is clean, the commits of this batch — find where the batch started in the conversation or `git log`; if that's unclear, ask instead of guessing.
- **Full mode** has two scopes:
  - **Batch scope** — the last batch, found as in batch mode. Correctness and smells review only this: every earlier batch was already reviewed by all three before its commit, so going over it again repeats work and pulls fixes into old commits.
  - **Feature scope** — the whole feature(s) the user names, or everything the plan touched (from the plan's first batch commit, or since the feature started on this branch). The architecture pass and `/simplify` use this.
  - If the earlier batches were **not** reviewed with `/review-batch` (no plan file records it, or the user says so), use the feature scope for all three.
- State the scope in one line (mode, N files, features) before launching anything.

## Step 2 — Launch the three reviewers in parallel
In **one message**, three Agent calls — every batch, whatever it touches:
- `subagent_type: "flutter-kit:correctness-reviewer"` — functional bugs: logic vs intent, edge cases, async/lifecycle, state, error handling, data mapping; and whether the batch's tests actually guard them
- `subagent_type: "flutter-kit:code-smells-reviewer"` — code smells and project conventions, in code and tests
- `subagent_type: "flutter-kit:architecture-reviewer"` — layering, coupling, responsibilities, Riverpod design (production code only)

In **full mode**, correctness and smells get the batch scope; architecture gets the feature scope plus the batch scope, with "**cross-batch review**: the batches were each reviewed already — report only what shows up across them (duplicated helpers or widgets, the same thing done two ways, boundaries or provider design that drifted between batches)".

Each prompt contains: the exact file list (or commit range and how to diff it), the feature name, one line on what the batch was meant to do (from the spec or conversation), and "report only — don't edit". Don't paste file contents; they read the files themselves.

## Step 3 — Merge into one report
- Drop duplicates (the same issue found by more than one → keep one, note all sources).
- One list ordered high → medium → low: `severity | file:line | finding | source (bug / smells / arch) | proposed fix`. Bugs come first within the same severity.
- Mark every item that's an architecture decision under CLAUDE.md "Architecture decisions — ask before applying" as **needs your decision**.
- Then ask which to apply — when `/spec-batch` is driving, ask its combined question instead (which items to apply + commit once tests are green). Don't apply fixes on your own; when the user says "apply" / "طبق التوصيات", apply the agreed ones, then run `flutter analyze` and the touched features' tests.
- **Every bug that gets fixed gets a regression test, written first:** one `flutter-kit:test-writer` call in regression mode with all the chosen bugs (Scenario + Test line each). Each test must fail on the current code for the scenario's reason; then fix, then rerun green. If a test can't be made to fail, the bug isn't real as described — report it and ask before changing the code.
- Bugs not applied: list them at the end of the report (title, file:line, scenario, Test line) — `/spec-batch` records them under the plan's Follow-ups.

## Step 4 — Full mode only: `/simplify`
After the Step 3 fixes are settled (applied or skipped) and the tests are green, invoke the built-in `simplify` skill on the **feature scope's `lib/` files only** — it hasn't seen any of this code yet. Tests stay out of its scope: they are the check that its cleanups didn't change behaviour, and a simplifier that edits them can merge or weaken their assertions.
Then run `flutter analyze` and `flutter test` for every touched feature. If a test fails, undo the `/simplify` change that broke it — don't edit the test — unless the test only pinned an internal detail (a removed helper or widget name) rather than behaviour. Report what changed.

## With /feature-dev
When `/feature-dev` drives the work, tell it to skip its own quality-review phase and run `/review-batch` (or `/review-batch full` at the end) instead — otherwise the same code is reviewed twice.
