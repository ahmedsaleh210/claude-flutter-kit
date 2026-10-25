# claude-flutter-kit

A [Claude Code](https://code.claude.com) plugin marketplace with one plugin, **flutter-kit**: skills, subagents and a hook for **feature-based Riverpod Flutter apps** (RTL-first, Arabic/English).

## What's inside

**Skills** (`plugins/flutter-kit/skills/`)

| Skill | What it does |
|---|---|
| `riverpod` | Scaffolds a provider the project's way — picks Notifier / AsyncNotifier / action notifier / FutureProvider, file layout, outcome pattern, cancelToken, build_runner |
| `wire-endpoint` | Wires an API endpoint end to end — contract check, endpoint constant, repository + params, provider |
| `pagination` | Infinite-scroll lists with a paginated-provider factory + `PaginatedListView` |
| `i18n` | Adds translation keys the right way (single source file, interpolation, RTL gotchas) |
| `notifier-testing` | Unit tests for notifiers with `ProviderContainer` + mocktail |
| `widget-testing` | Widget tests through a shared `pumpApp` harness |
| `figma-screen` | Figma → Flutter for RTL designs |
| `dtd-verify` | Runtime verification through the Dart Tooling Daemon — always asks before touching your running app |
| `photo-upload-field` | Mixed local/remote photo pickers with edit mode |
| `auth-flow-gotchas` | The silent-failure contracts of auth/onboarding flows |
| `review-batch` | Runs the three reviewer agents (correctness, smells, architecture) on a batch in parallel; `full` mode (end of a feature) keeps bugs and smells on the last batch, adds a cross-batch architecture pass and `/simplify` over the whole feature |
| `spec-batch` | Drives spec work in batches across sessions — batches sliced by feature (data + state + UI together, ~300–500 lines), one approval for review fixes + commit; each plan keeps its own file in `specs/_progress/`. Takes specs, Figma links, or both; drafts a spec from the design when there's none; screens without a design are built to match an existing screen; real architectural decisions get two `code-architect` subagents (minimal vs clean) before you choose (user-invoked only) |

**Agents** (`plugins/flutter-kit/agents/`) — subagents the skills launch; each runs in its own context and returns a report:

| Agent | Used by | Does | Edits files? |
|---|---|---|---|
| `spec-gap-checker` | `/spec-batch` planning, spec changes | Compares specs + OpenAPI with the code: implemented / differs / missing | no |
| `code-explorer` | start of every batch (2–3 in parallel) | Maps one slice: the code to change, the closest similar feature, or reusable building blocks | no |
| `code-architect` | batches with a real architectural decision (2 in parallel) | Full blueprint from one stance — minimal change or clean | no |
| `correctness-reviewer` | `/review-batch` | Functional bugs — logic vs intent, edge cases, async/lifecycle, state, error handling, data mapping — each with the scenario that triggers it | no |
| `code-smells-reviewer` | `/review-batch` | Code smells, why they matter, cleaner version | no |
| `architecture-reviewer` | `/review-batch` | Layering, coupling, responsibilities, Riverpod design | no |
| `test-writer` | after review | Writes and runs unit + widget tests until green | yes (tests) |

Self-contained: no other plugin is required. `/review-batch full` also runs Claude Code's built-in `/simplify`.

**Hooks** (`plugins/flutter-kit/hooks/`)
- **dart format** — formats every `.dart` file Claude edits (generated files skipped).
- **Session names for `/spec-batch`** — names the session from the plan, so every batch session is easy to find (see below).

## Assumptions — read before using it elsewhere
The skills are written for apps that share a specific structure: `lib/src/features/{feature}/{data,presentation}` with barrel files, Riverpod with `@riverpod` codegen, a `Go` navigation helper, `StatusBuilder`, a `TextBuilder` text extension, `LocaleKeys` generated from a single `lang.json`, a paginated-provider factory, and a `pumpApp` test harness. Business rules are deliberately **not** in the skills: they point to a `## Project specifics` section in each app's `CLAUDE.md`. If your app differs, fork and adapt the skills.

## Install

Per project (recommended) — commit this in the app's `.claude/settings.json`:
```json
{
  "extraKnownMarketplaces": {
    "flutter-kit": { "source": { "source": "github", "repo": "ahmedsaleh210/claude-flutter-kit" } }
  },
  "enabledPlugins": { "flutter-kit@flutter-kit": true }
}
```
Claude Code offers to install it the first time the project is opened.

Or for yourself, in any session:
```
/plugin marketplace add ahmedsaleh210/claude-flutter-kit
/plugin install flutter-kit@flutter-kit
```

Don't keep copies of these skills in a repo's `.claude/skills/` — same-named project skills load alongside the plugin's.

## Daily use
- Skills trigger on their own when the task matches (or call them: `/riverpod`, `/flutter-kit:riverpod`).
- Spec work: `/spec-batch specs/… [Figma links]` plans the batches (no code); then `/spec-batch` (or `/spec-batch <plan>` when several plans are active) in a fresh session per batch. Design only? `/spec-batch <Figma links>` drafts the spec first for you to review.
- After each batch: `/review-batch`. At the end of a feature: `/review-batch full`.
- Ask for an agent by name: "have test-writer cover the bookings feature", "run spec-gap-checker on specs/x.md".

## Plans, batches and session names
- A **plan** is one `/spec-batch` planning run — any number of specs (and Figma links) planned together. It has one file, `specs/_progress/<plan>.md`, holding the specs, designs, decisions and the list of batches. `Status: active` until the last batch is done, then `done`.
- A **batch** is one slice of a plan, finished in one session: its own goal, requirements, design and commit.

```
plan: wallet   (specs/_progress/wallet.md)
├── Batch 1: models + repository      ← session 2
├── Batch 2: wallet state             ← session 3
└── Batch 3: withdrawal screen        ← session 4
```

Each session is named automatically when its first prompt is `/spec-batch` — no need to type a description:

| You type | Session name |
|---|---|
| `/spec-batch wallet specs/wallet-flutter.md specs/_enums.md` | `wallet · planning` |
| `/spec-batch specs/wallet-flutter.md specs/_enums.md` | `wallet, enums · planning`, then `wallet · planning` once you confirm the name |
| `/spec-batch` (one active plan) | `wallet · Batch 3: Withdrawal screen` |
| `/spec-batch notifications` | `notifications · Batch 1: Notification enums` |
| `/spec-batch wallet merge` | `wallet · merge` |

- The batch is the one in progress, else the first pending one whose design isn't deferred — the same one `/spec-batch` will work on.
- With several active plans, `/spec-batch` alone leaves the name untouched (it can't know which plan you'll pick); use `/spec-batch <plan>`.
- A planning session without a name in the command is renamed to `<plan> · planning` on your next message after the name is confirmed (the plan file records `Planning session: <id>`).
- A session you already named is never renamed.
- Labels follow the plan's language: Arabic (`الدفعة`, `تخطيط`) when the plan file contains Arabic, English otherwise. Force one with the `FLUTTER_KIT_LANG` environment variable (`ar` or `en`), e.g. in `~/.claude/settings.json` → `"env": { "FLUTTER_KIT_LANG": "ar" }`.
- The plugin must be installed (not just loaded for one session) for its hooks to name sessions.

### Safety rails in batch sessions
- **Commits carry only the batch's files**, staged by path — files that were already modified when the batch started (another session's work) are left out. Never `git add -A`.
- **A batch is claimed when it starts** (`Session:` and `Stage:` lines in the plan file). Before starting, `/spec-batch` reads **every** plan in the folder: if any batch is running there — same plan or another — it stops and asks whether that session is still running.
- **An interrupted batch resumes** from its recorded stage after checking what's already committed or on disk — nothing is rewritten.
- **No Figma, no designed screen:** if a batch has Figma frames but the Figma tools don't answer, the UI work stops until they do (or you explicitly accept matching an existing screen for now).

### Two plans in parallel
A single plan never uses any of this — its batches run in the repo folder on the current branch. One running batch per folder. To work on a second plan while another plan's batch is running, choose the worktree option when `/spec-batch` offers it:
- It creates a git worktree **next to** the repo (`../<repo>--<plan>`, branch `plan/<plan>`) from your local HEAD, copies the git-ignored local files the app and tools need (`.env`, `.claude/settings.local.json`, signing config, ignored pubspec assets), moves the session into it (you approve the move), runs `flutter pub get` + `build_runner`, and continues there. All of that plan's batches run in that folder, one after another.
- After every batch commit it **syncs** the base branch into the plan branch and resolves conflicts there — generated files are regenerated, never hand-merged; `lang.json` and other additive lists keep both sides; real code conflicts are shown to you — then runs analyze and tests.
- `/spec-batch <plan> merge` (or the offer after the last batch) merges the plan into the base branch — only when the base folder is idle — then removes the worktree after asking. Nothing is pushed.
- Batches of the *same* plan never run in parallel; they depend on each other.

## Developing the plugin
- Try local changes before pushing: `claude --plugin-dir ./plugins/flutter-kit` (that session uses the local copy).
- Validate: `claude plugin validate .` and `claude plugin validate ./plugins/flutter-kit`.
- Installs from GitHub are cached by version: **bump `version`** in `plugins/flutter-kit/.claude-plugin/plugin.json` on every change you push — patch for wording fixes, minor for a new skill/agent. Users pick it up with `/plugin` → update.

## License
MIT — see [LICENSE](LICENSE).
