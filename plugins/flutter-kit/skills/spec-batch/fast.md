# Fast mode — `Mode: fast` plans only

Read this file only when the user starts a plan with `/spec-batch fast …`, or when the plan file's header says `Mode: fast`. A plan with no `Mode:` line, or `Mode: normal`, never uses anything here.

Fast mode trades quality for time, on purpose: bigger batches, no architect agents, unit tests only, and **one review at the end of the plan** instead of after every batch. Everything in `SKILL.md` still applies — claims, snapshots, commits by path, plan worktrees, rules — except the steps this file replaces.

## Planning (replaces parts of Plan mode)
- Write `Mode: fast` in the plan file header, under `Status:`.
- **Step 5 — batch size:** still sliced by feature, still independently committable, but aim for **~800–1200 lines of production code** per batch — there is no per-batch review to keep small.
- **Sensitive batches:** for every batch that touches money (payments, payouts, prices, commission), auth (sign-in, sessions, tokens, permissions), or a write the server can't undo (bookings, contracts, cancellations), tell the user and ask: keep it fast, or run it as normal? Record the answer as a decision; a batch that runs normal gets `Mode: normal` under its heading. The user decides — never switch on your own.
- **Last entry:** add a final batch `### N. Final review — pending` with `Type: review` under it. `/spec-batch` reaches it like any other batch, after the last implementation batch.

## Batch sessions (replaces Continue steps 3, 5 and 6)
A batch with its own `Mode: normal` line runs the normal steps from `SKILL.md`, not these.
- **3. Architecture — no architect agents.** When the batch needs a real structural decision (the same test as normal step 3), present 2–3 options yourself from what the explorers found — recommendation first, files touched by each — and ask. Record the choice as a decision.
- **5. Tests — unit only.** Launch `flutter-kit:test-writer` on the batch with "**unit tests only — no widget tests**": each action notifier's outcome branches, models with a defensive `fromJson`, params' `toJson` / `toQueryParameters`, and the cancellation tests (a screen read cancels when nothing watches it; writes send no cancel token). Then `flutter test` for the touched features. A bug the tests expose is fixed before the commit.
- **6. No review in the batch** — no reviewers, no tests check, no regression step. Note `Review: at the end (fast mode)` in the batch notes.
- Steps 7–10 (UI check, plan file, commit, hand-off) as normal. The commit question comes after the tests are green — ask it then, unless the user already said to commit.

## The final review batch (`Type: review`)
Claim it like any batch. Scope = every fast batch's commit (their hashes are on the batch headings).
1. **In one message**, launch:
   - per fast batch: `flutter-kit:correctness-reviewer` and `flutter-kit:code-smells-reviewer` on that batch's commit only (`git show <hash>`), so each review stays as focused as a normal one;
   - one `flutter-kit:architecture-reviewer` as a **cross-batch review** over the whole plan;
   - one `flutter-kit:correctness-reviewer` in **tests-check mode** on all the plan's test files.
   With more than 4 batches, pair neighbouring batches into one reviewer each, to stay near 8 agents.
2. Merge everything into one report (`/review-batch` Step 3) and ask **one** question: which items to apply, and whether to commit once tests are green.
3. Apply as in normal step 6: every chosen bug gets its regression test first (one `flutter-kit:test-writer` call in regression mode, with the tests-check findings), red on the current code, then the fix, then green. Bugs not applied go to `## Follow-ups`.
4. Commit the review fixes (`fix(<plan>): final review`, by path).
5. `/simplify` on the whole plan's `lib/` (`/review-batch` Step 4), then the plan's tests again; undo any cleanup that breaks a test. Commit it separately (`refactor(<plan>): simplify`), so it can be reverted alone.
6. Mark the review batch `done`, set the plan's `Status: done`, hand off with the final summary.
