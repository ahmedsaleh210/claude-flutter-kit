---
name: dtd-verify
description: Verify a Flutter UI/behavior change at runtime in a feature-based Riverpod Flutter app via the Dart Tooling Daemon (DTD) — hot reload/restart, check for runtime errors, and confirm the rendered screen (RTL layout, real translations) matches intent. Use after implementing a screen/widget/i18n change when you want to confirm it actually renders correctly, not just compiles — but always ask the user first and run it only on a clear yes: it drives their running app.
---

# Runtime verification (DTD)

Use the connected Dart MCP tools (`mcp__dart__*`) to drive a running app instance.

## Step 0 — Ask first, every time
This drives the user's running app: it hot-reloads (and may hot-restart, which resets navigation and app state), navigates, and reads the screen. **Never start without asking.** Say in one line what you'd check and what it will do to the app (e.g. "hot reload, then hot restart to load the new translations — your current screen and state will reset"), then wait:
- **Yes** → continue with Step 1.
- **No / no answer** → don't touch the app. Say plainly that the change wasn't checked at runtime, and what the user should look at themselves.
If the user's own message asked for this check ("check it with /dtd-verify", "verify it on the device"), that is the yes — don't ask twice. Another skill or step deciding it would help is **not** a yes: ask. A yes covers this one check only — ask again next time.

## Step 1 — Apply the change with hot reload
`mcp__dart__hot_reload` after edits. Then `mcp__dart__get_runtime_errors` — a clean reload with no exceptions is the first gate.

## Step 2 — Beware false signals after hot reload (only when you ADDED keys this session)
easy_localization reads `ar.json`/`en.json` **once at startup**, so only locale keys you **added this session** render raw on hot reload (e.g. the key `myNewKey` instead of its translated text) — and those raw keys produce **false overflow errors** because they're odd-width. Pre-existing keys render fine on a plain hot reload. Do NOT report raw-key overflows as bugs.
- Added keys this session? First confirm the generated `ar.json`/`en.json` (and `locale_keys.g.dart`) actually contain the key, then **hot restart** (`mcp__dart__hot_restart`) to load translations.
- Layout-only change with no new keys → a hot reload is enough; skip the restart + re-navigate dance below.

## Step 3 — Re-navigate after restart
Hot restart **resets navigation to the app root**. After restarting, navigate back to the screen under test before judging it — otherwise you're verifying the wrong screen.

## Step 4 — Inspect the rendered result
- Inspect with `mcp__dart__widget_inspector` (`command: get_widget_tree`, `summaryOnly: true`) and read rendered strings via each node's `textPreview`. For an actual image, use `mcp__dart__flutter_driver_command` (`command: screenshot`) — `widget_inspector` **cannot** screenshot.
- For an RTL screen, confirm content reads correctly **right → left** and matches the Figma screenshot (if implementing a design). Right-aligned content, start-anchored rows, chevrons on the left.
- Re-run `mcp__dart__get_runtime_errors` after navigating — confirm no real exceptions (overflow, null, assertion).

## Step 5 — Report honestly
State plainly what you observed: which screen, reloaded vs restarted, any real errors with their output. If you only hot-reloaded (so translations weren't verified), say so. Don't claim "verified" if you only confirmed it compiles.

## Quick checklist
- [ ] Hot reload clean (no runtime errors)
- [ ] If keys were added this session: hot restart done so real translations render (else hot reload is enough)
- [ ] Navigated back to the target screen after any restart
- [ ] RTL layout matches intent / Figma
- [ ] No real overflow/null/assertion errors (raw-key false overflows discounted)
