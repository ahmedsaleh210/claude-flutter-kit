---
name: review-batch
description: Review the current batch of work with the project's reviewer agents. Default mode (every batch) runs code-smells-reviewer and architecture-reviewer in parallel on the batch and merges their findings into one report. `full` mode (end of a feature) does the same over the whole feature, then runs /simplify. Use when the user says "review the batch", "راجع الدفعة", "/review-batch", or "/review-batch full" at the end of a feature.
argument-hint: "[full] [scope — files, commit range or feature]"
---

# Review a batch

Arguments: `$ARGUMENTS`. If they contain the word `full` → **full mode**; anything else is the scope. No `full` → **batch mode**.

| Mode | When | Runs |
|---|---|---|
| batch (default) | after every batch | code-smells-reviewer + architecture-reviewer, in parallel |
| full | once, at the end of a feature | the same two over the whole feature, then `/simplify` |

Never run full mode after every batch — `/simplify` is ~80% of review cost; it runs once per feature.

## Step 1 — Fix the scope
- **Batch mode:** the user's scope if given; otherwise the uncommitted changes (`git diff HEAD --name-only` + untracked files under `lib/` and `test/`). If the tree is clean, the commits of this batch — find where the batch started in the conversation or `git log`; if that's unclear, ask instead of guessing.
- **Full mode:** the whole feature(s) the user names, or every feature directory touched on this branch / since the feature started.
- State the scope in one line (mode, N files, features) before launching anything.

## Step 2 — Launch both reviewers in parallel
In **one message**, two Agent calls:
- `subagent_type: "flutter-kit:code-smells-reviewer"`
- `subagent_type: "flutter-kit:architecture-reviewer"`

Each prompt contains: the exact file list (or commit range and how to diff it), the feature name, one line on what the batch was meant to do (from the spec or conversation), and "report only — don't edit". Don't paste file contents; they read the files themselves.

## Step 3 — Merge into one report
- Drop duplicates (the same issue found by both → keep one, note both sources).
- One list ordered high → medium → low: `severity | file:line | finding | source (smells / arch) | proposed fix`.
- Mark every item that's an architecture decision under CLAUDE.md "Architecture decisions — ask before applying" as **needs your decision**.
- Then ask which to apply. Don't apply fixes on your own; when the user says "apply" / "طبق التوصيات", apply the agreed ones, then run `flutter analyze` and the touched features' tests.

## Step 4 — Full mode only: `/simplify`
After the Step 3 fixes are settled (applied or skipped), invoke the built-in `simplify` skill on the same scope. It applies its own cleanups. Finish with `flutter analyze` and `flutter test` for the touched features, and report what changed.

## With /feature-dev
When `/feature-dev` drives the work, tell it to skip its own quality-review phase and run `/review-batch` (or `/review-batch full` at the end) instead — otherwise the same code is reviewed twice.
