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
| `dtd-verify` | Runtime verification through the Dart Tooling Daemon |
| `photo-upload-field` | Mixed local/remote photo pickers with edit mode |
| `auth-flow-gotchas` | The silent-failure contracts of auth/onboarding flows |
| `review-batch` | Runs the reviewer agents on a batch; `full` mode adds `/simplify` at the end of a feature |
| `spec-batch` | Drives spec work in batches across sessions, with a `specs/_progress.md` plan (user-invoked only) |

**Agents** (`plugins/flutter-kit/agents/`) — `code-smells-reviewer`, `architecture-reviewer`, `test-writer`, `spec-gap-checker`.

**Hook** — runs `dart format` on every `.dart` file Claude edits (generated files skipped).

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
- Spec work: `/spec-batch specs/…` plans the batches (no code); then `/spec-batch` in a fresh session per batch.
- After each batch: `/review-batch`. At the end of a feature: `/review-batch full`.
- Ask for an agent by name: "have test-writer cover the bookings feature", "run spec-gap-checker on specs/x.md".

## Developing the plugin
- Try local changes before pushing: `claude --plugin-dir ./plugins/flutter-kit` (that session uses the local copy).
- Validate: `claude plugin validate .` and `claude plugin validate ./plugins/flutter-kit`.
- Installs from GitHub are cached by version: **bump `version`** in `plugins/flutter-kit/.claude-plugin/plugin.json` on every change you push — patch for wording fixes, minor for a new skill/agent. Users pick it up with `/plugin` → update.
