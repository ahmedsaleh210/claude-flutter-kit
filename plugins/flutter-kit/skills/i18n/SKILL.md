---
name: i18n
description: Add or update localization keys in a feature-based Riverpod Flutter app (English/Arabic pairs) the correct way — edit lang.json only, use explicitKey and interpolate patterns, avoid the RTL number-glue and camelCase-after-digit gotchas, and verify the generated LocaleKeys name. Use whenever a feature needs new translated strings or you see a hardcoded user-facing string.
---

# Localization (easy_localization + custom generator)

## Golden rule
Edit **`assets/translations/lang.json` ONLY**. Never hand-edit `en.json`, `ar.json`, or `locale_keys.g.dart` — they're generated. The watcher regenerates `locale_keys.g.dart` within ~5s. Do not run the generator yourself unless the watcher isn't running (see the stale-watcher note below).

## Step 1 — Add the pair
Format is `"English": "Arabic"`:
```json
"Save changes" : "حفظ التغييرات"
```
Arabic must be **Modern Standard Arabic (الفصحى)**, not colloquial.

## Step 2 — Force a stable key when needed
Use `explicitKey #$ Human readable English`:
```json
"saveChanges #$ Save changes" : "حفظ التغييرات"
```
Keep the English part free of `,` `:` `=` — the generator skips keys containing those. (`?` and `{}` are allowed; the generator strips them when building the key — e.g. `"Forgot Password?"` works fine.)

## Step 3 — Interpolate values with `.interpolate`, never Dart `$`
Define `{token}` placeholders in the value and substitute at the call site:
```json
"itemsCountLabel #$ You have {count} items in {place}" : "لديك {count} عنصر في {place}"
```
```dart
LocaleKeys.itemsCountLabel.interpolate({'count': count, 'place': place})
```
Why not `'$prefix ${LocaleKeys.x} $value'`: the translator can't reorder tokens (Arabic order differs), digit-adjacent interpolation causes RTL number-glue bugs, and untranslated fragments leak into the UI.

## Step 4 — Avoid the gotchas
- **camelCase after a digit gets lowercased**: `before1Hour` → `before1hour`. Always verify the real name in `locale_keys.g.dart`.
- **Never interpolate a number directly before a key that starts with a digit**: `'$hours ${LocaleKeys.hour1}'` where `hour1 = "1 ساعة"` renders `"11 ساعة"` in RTL. Use a unit-only key (e.g. `hourUnit = "ساعة"`).
- `LocaleKeys.x` is already a `.tr()`-calling getter — **never** call `.tr()` on it again. Interpolate directly into text builders: `'📷 ${LocaleKeys.photos}'.text…build()`.

## Step 5 — Use at the call site
```dart
LocaleKeys.saveChanges.text.semiBold.fs(16).c(AppColors.black).build()
```
Form fields use `hintText:` (not `hint`/`label`).

## Step 6 — Verify
- Wait for the watcher (~5s), then confirm the exact generated getter name in `lib/src/config/language/locale_keys.g.dart`.
- If `locale_keys.g.dart` isn't updating: kill stale `generate/strings` watcher processes and re-run `dart run generate/strings/main.dart` — then **stop** that run once it prints success, or you leave a second long-lived watcher behind (the exact problem you're fixing).
- When verifying in-app: hot reload shows **raw keys** (and false overflows) until a **hot restart** loads translations — and restart resets navigation, so navigate back to the screen.
