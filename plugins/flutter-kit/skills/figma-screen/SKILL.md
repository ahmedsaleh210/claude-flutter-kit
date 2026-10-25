---
name: figma-screen
description: Translate a Figma design (screen, view, modal, card, or component node) into Flutter in an RTL-first, feature-based Riverpod Flutter app. Use whenever a Figma URL or node is provided and the user wants it built in Flutter, or asks to implement/match a design. Handles RTL child ordering, color verification against AppColors, screenutil sizing, part-of widget extraction, and i18n key emission.
---

# Figma → Flutter (RTL-first)

Designs on these projects are authored in **Arabic (RTL)**. The #1 failure mode is copying LTR source order from the React/HTML export. Always reason from the rendered screenshot, right → left.

## Step 1 — Pull the design (token-safe)
Call these together, NOT `get_design_context` (it blows the token limit on real nodes):
- `mcp__figma-dev-mode-mcp-server__get_screenshot` — the source of truth for **layout order**
- `mcp__figma-dev-mode-mcp-server__get_metadata` — structure, sizes, spacing
- `mcp__figma-dev-mode-mcp-server__get_variable_defs` — colors, radii, font tokens

Only fall back to `get_design_context` on a small leaf node when you need exact CSS.

## Step 2 — Verify every color against AppColors
For each hex in the design, check it against `lib/src/config/res/app_colors.dart`.
- Match found → use the existing `AppColors.*` constant.
- No match → **add a new constant** to `app_colors.dart` first. Never inline `Color(0xFFXXXXXX)`.
- Do NOT assume a similarly-named existing color is the same hex — compare the actual value.

## Step 3 — Transcribe layout right → left (at EVERY nesting level)
- In an RTL `Row`, the **first** child renders at the **start (right)**, the **last** at the **end (left)**.
- Read the screenshot right → left and write `children: [...]` in that order.
- Apply this at every nested Row, not just the outer one. If you catch yourself copying children straight from the export, stop and look at the screenshot canvas instead — use the export only for styling (colors, padding, fonts).
- `MainAxisAlignment.start` packs content on the **right**; `.end` packs on the **left**. Right-aligned content in a wide container → use `start` (or default), never `end`.
- Never hard-code `left`/`right`/`CrossAxisAlignment.end`/`EdgeInsets.only(left:)`. Use `start`/`end`/`EdgeInsetsDirectional`.

Worked example — mock (right→left) `[emoji] [title+subtitle] [...] [chevron]`:
```dart
Row(
  mainAxisAlignment: MainAxisAlignment.spaceBetween,
  children: [
    Row(children: [emojiBox, 8.szW, textColumn]), // emoji first → right
    chevron,                                       // last → left
  ],
)
```

## Step 4 — Sizing, spacing, overflow
- All sizing `.r`/`.w`/`.h`/`.sp`; spacing `12.szH`/`12.szW` (multiples of 4); radius `12.r` cards / `8.r` buttons.
- Space siblings with `.joinWith(8.szW)` / `.joinWith(12.szH)` — not per-child margins. `szW`/`szH` are `int` extensions, so the size goes on the number.
- Any text next to a fixed-size sibling (icon tile, badge, %) → wrap text in `Expanded`. In a `spaceBetween` Row, wrap the flexible group in `Expanded` too.
- Network images → `CachedImage`. SVG tint → `someSvg.svg(colorFilter: color.filterMode)` — only when the design actually recolors the icon from its source asset; otherwise render the SVG as-is with no `colorFilter`.

## Step 4b — Icons & gradients: use the DESIGN's actual asset, never a substitute
**Do NOT** swap in a Material `Icon(Icons.*)` or a similarly-named existing `AppAssets.svg.*` for an icon shown in the design. They look different and it's wrong every time. For each icon/illustration node:
1. Download the real SVG: `download_assets(fileKey, nodeId, defaultFormat: 'svg')`, then `curl -s <url> -o assets/svg/{name}.svg`.
2. The Figma export wraps the icon in the whole artboard — it includes a `<rect ... fill="#F2F2F2"/>` placeholder bg plus giant page-frame `<path>`s. **Strip all of that**: keep only the real icon paths (the innermost `<g id="Icon"|"Vector"|"elements">` group, or just the `fill="white"`/colored icon paths), and wrap them in a clean `<svg viewBox="0 0 W H">` matching the node's own width/height. Extract programmatically (regex the `<path>`s) to avoid transcription errors.
3. Pick a name that does NOT collide with an existing asset (e.g. `camera_filled.svg`, not `camera.svg`) unless you truly mean to reuse it.
4. Regenerate: `rm lib/src/config/res/assets.gen.dart && dart run build_runner build`, then use `AppAssets.svg.{name}`. Verify the getter exists.
- **Layered/multi-fill icons that don't survive as a single SVG** → rasterize to PNG with **resvg**, never `qlmanage` (it ignores viewBox scaling on small square viewBoxes and outputs a tiny icon in a white square):
  1. `get_design_context` on the icon's parent frame → per-layer SVG URLs + inset percentages.
  2. Resolve CSS vars in each layer (`fill="var(--fill-0, white)"` → `white`; regex `var\(--[^,]+,\s*([^)]+)\)` → `\1`).
  3. Flatten into ONE `<svg width="S" height="S" viewBox="0 0 S S">`, each layer as `<g transform="translate(x,y) scale(W/vbW, H/vbH)">` (x/y/W/H = inset% × S). Flat `<g>`s only, never nested `<svg>`.
  4. Render with `@resvg/resvg-js` (npm, in a temp dir): `new Resvg(svg, {fitTo:{mode:'width', value: 6*S}}).render().asPng()`.
  5. Verify by rendering a preview **over the real card color** and viewing it — a transparent background hides white glyphs/trays. Retint single-color glyphs by string-replacing the fill when the screenshot shows an instance override the export missed.
  6. Save to `assets/images/`, regenerate `assets.gen.dart` (new filenames only), use `AppAssets.images.xxx.image(width:, height:)`.
- **Gradients:** read the real stops from the exported SVG's `<linearGradient>` (`get_variable_defs` often returns the gradient token as an empty string — the SVG is the source of truth). Add the stop colors to `AppColors` and, if the gradient is reused, a `LinearGradient` constant next to the existing gradient constants. Never guess a shade. **Gradient borders / any new package:** check `pubspec.yaml` first; if it isn't there, ask before adding it rather than faking the effect with stacked containers.

## Step 5 — Extract widgets (part-of pattern)
For a complex screen, each widget goes in `presentation/widgets/`, one file per widget:
- Screen file declares `part 'widgets/xxx.dart';`
- Widget file starts `part of '../screens/{screen_name}.dart';` — no imports of its own.
- Widget classes stay **private** (`_HeaderSection`). Usages live only in the parent.
- Reusable across screens / >30 lines / configurable → make it a real class with `const` ctor instead.

## Step 5b — Reuse core components, don't hand-roll chrome
A Figma sheet/dialog/picker/top-bar is a *visual* spec, not a reason to rebuild
the mechanism. Before hand-rolling a `showModalBottomSheet` + `Container`, a
`Dialog`, a picker, or a custom header `Row`, reach for the existing core
helper — they already carry the drag handle, rounded top, keyboard/safe-area
padding, adaptive iOS/Android behaviour, and RTL back button:
- **Bottom sheets** (`lib/src/core/widgets/`): `showDefaultBottomSheet(child:)`
  for a content sheet (adds the handle + rounded top + keyboard/`bottomBarHeight`
  padding via `DefaultSheetBody` — just pass the inner `Column`);
  `showSuccessBottomSheet(title:, subtitle:)` (`sheets/success_bottom_sheet.dart`)
  for a success confirmation; `ConfirmationSheet.show(message:, confirmLabel:, cancelLabel:, destructive:)`
  → `Future<bool>` (`confirmation_sheet.dart`) for any destructive confirm
  (delete / logout / delete-account). Don't re-create the white rounded container
  + `ScreenUtil().bottomBarHeight` padding by hand — that chrome lives in `DefaultSheetBody`.
- **Dialogs:** `showCustomDialog(context, child:)` (`custom_dialog.dart`) — not a raw `showGeneralDialog`/`Dialog`.
- **Date / time:** `showAdaptiveDatePicker()` → `Future<DateTime?>`; `showCustomTimePicker(initialTime:)` → `Future<DateTime?>` (both adaptive Material/Cupertino). Never build a `CupertinoDatePicker` inline. Capture `DateTime.now()` **once** for `initial/first/last` (see CLAUDE.md gotcha).
- **Top bar:** a standard title + back + actions is a plain `AppBar(title: Text(...), actions: [...])` (centre it with `centerTitle: true` if the design does) — don't assemble a custom header `Row` with circular back/settings buttons for what `AppBar` already gives you. Match the sibling screens.
- Selection fields, add-rows, buttons: see CLAUDE.md "Reusable selection components" and "Buttons" before building a new one.

## Step 6 — Text & localization
- Text via TextBuilder: `LocaleKeys.x.text.semiBold.fs(12).c(AppColors.black).build()`. Sizes follow the type ladder in CLAUDE.md "Text Styling" — take the size from the design, don't default upward.
- Every visible string is a `LocaleKeys.*` key — never hardcode. If keys are missing, run the `/i18n` skill to add them.
- Per-span multi-color text → `Text.rich` + `TextSpan`.

## Step 7 — Feedback messages: toast vs snackbar
- **Inside a dialog or bottom sheet, use `MessageUtils.showSimpleToast(msg)`** — NOT `showSnackBar`. `showSnackBar` resolves a `ScaffoldMessenger`, which the dialog/sheet route may not provide (or it renders *behind* the overlay). `showSimpleToast` (fluttertoast) is an OS-level overlay that always paints above modal routes.
- For error feedback pass `color: AppColors.error`; success/info uses the default (primary). Both from `lib/src/core/widgets/custom_messages.dart`.
- On a normal full screen (`Scaffold` present), `MessageUtils.showSnackBar` is still fine.

## Step 8 — Verify
Offer `/dtd-verify` — ask the user first and run it only on a clear yes — to confirm the rendered RTL layout matches the screenshot (hot reload shows false overflows from raw keys; hot restart to see real translations, then navigate back to the screen).

## Checklist before done
- [ ] Layout reads correctly right→left at every nesting level
- [ ] Every color resolves to an `AppColors` constant (added new ones if needed)
- [ ] Every icon is the design's own downloaded asset (no Material `Icons.*` / look-alike substitute); gradients read from the exported SVG stops
- [ ] No hard-coded sizes/strings/colors; screenutil + LocaleKeys throughout
- [ ] Reused core chrome (`showDefaultBottomSheet` / `ConfirmationSheet.show` / `showCustomDialog` / `showAdaptiveDatePicker` / `showCustomTimePicker` / `AppBar`) instead of hand-rolling sheets, dialogs, pickers, or headers
- [ ] Complex widgets extracted as private part files
- [ ] `flutter analyze` clean on the touched files
