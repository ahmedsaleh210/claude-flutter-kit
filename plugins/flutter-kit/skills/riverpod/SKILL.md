---
name: riverpod
description: Scaffold a Riverpod provider (Notifier, AsyncNotifier, action notifier, simple toggle, or hand-written FutureProvider) in a feature-based Riverpod Flutter app — correct provider type, file layout, outcome pattern, cancelToken, barrel export — then run build_runner. Use when adding any new provider/notifier or unsure which provider type fits.
---

# Riverpod provider scaffolder

## Step 0 — Confirm the shape before writing files
**How many providers, of what type, with what lifetime is the user's call — present options and wait.** Default to the *fewest* providers that work: a screen whose fields are related is ONE notifier holding a state class, not one provider per field, per section, or per step. Splitting needs a real reason (different lifetimes, different rebuild scopes, one `keepAlive` and one not, one a `FutureProvider` fetch and one form state).

Skip the question only when the user already specified the structure, or when you're adding a field/setter/method to a provider that already exists. See "Architecture decisions — ask before applying" in CLAUDE.md.

## Step 1 — Pick the provider type (decision tree)
- **Sync state** (toggle, counter, form step, multi-field form) → `Notifier<T>` (`@riverpod`).
- **One-shot async action** (submit / save / delete / send) → action notifier: method returns an **outcome** (enum + wrapper class). Never `AsyncNotifier` just because a method is `async`.
- **Async data fetch with loading/error UI** → `AsyncNotifier<T>`, consumed via `StatusBuilder`. Only when `build()` itself loads data.
- **Stable read-only fetch, no custom methods** → hand-written `FutureProvider` (no codegen); refresh via `ref.invalidate`.
- **Simple boolean/value toggle** → `Notifier` with a `toggle()`.

Auto-dispose (`@riverpod`) is the default — right for screen-scoped state. Use `@Riverpod(keepAlive: true)` only for AsyncNotifiers caching app-lifetime data (lookups, settings, policies).

## Step 2 — File layout
- **Single** notifier in a feature → `presentation/notifiers/{name}_provider.dart` directly.
- **Multiple** notifiers → each in its own folder: `presentation/notifiers/{name}/{name}_provider.dart` (`.g.dart` co-located).
- A feature split into **sub-features** nests first: `presentation/{sub_feature}/notifiers/{name}/{name}_provider.dart`. A multi-step flow groups its steps the same way: `presentation/notifiers/steps/{step}/{step}_provider.dart`. Look at how the existing features in this repo nest before choosing.
- The **state class lives in its own file** beside the provider (`{name}_state.dart`), with its OWN imports — not `part of` the provider and not declared inline. Re-export it from the barrel.
- `@riverpod` files CANNOT be `part of` a barrel — each is a standalone library with its own `part '{name}_provider.g.dart';`. **Export** it from the feature's `presentation/imports/{feature}_presentation_imports.dart` barrel instead.
- Hand-written FutureProviders are standalone files with their own imports (e.g. `core/shared/providers/localized_provider.dart`); export them from the barrel like any other provider.

## Step 3 — Apply the right template

**Simple toggle**
```dart
@riverpod
class IsPasswordVisible extends _$IsPasswordVisible {
  @override
  bool build() => false;
  void toggle() => state = !state;
}
```

**Multi-field form state** — one setter per field (never a generic `update(...)`); each setter cascade-clears its dependents with the nullable `T? Function()?` pattern; validation lives in the view (formKey + CustomWidgetValidator). State holds inputs only — **no** `status`, `errorMessage`, or `lastResult` fields. Build collections immutably (spreads/`.map`/`.where`), never mutate-then-reassign.

```dart
class CategoryState extends Equatable {
  final CategoryModel? category;
  final GroupModel? Function()? group;   // depends on category
  final TypeModel? Function()? type;     // depends on group
  final DifficultyLevel difficulty;
  final String note;

  const CategoryState({this.category, this.group, this.type,
    this.difficulty = DifficultyLevel.easy, this.note = ''});

  CategoryState copyWith({ /* same nullable-fn types */ }) => /* ... */;

  @override
  List<Object?> get props => [category, group?.call(), type?.call(), difficulty, note];
}

@riverpod
class Category extends _$Category {
  @override
  CategoryState build() => const CategoryState();

  void selectCategory(CategoryModel value) {
    if (state.category?.id == value.id) return;
    // parent changed → clear every dependent
    state = state.copyWith(category: value, group: () => null, type: () => null);
  }

  void selectGroup(GroupModel value) {
    if (state.group?.call()?.id == value.id) return;
    state = state.copyWith(group: () => value, type: () => null);
  }

  void selectType(TypeModel value) => state = state.copyWith(type: () => value);
  void setNote(String value) => state = state.copyWith(note: value);
}
```
`copyWith(x: () => value)` sets it, `copyWith(x: () => null)` clears it, `copyWith()` keeps the previous — no `bool clearX` flags. Read with `state.x?.call()`.

**Action notifier** — one enum + one outcome class per action. Distinguish `invalid` (params couldn't be built — silent UX) from `failure` (server rejected — show snackbar).
```dart
enum SaveResult { invalid, success, failure }
class SaveOutcome {
  final SaveResult result;
  final String? errorMessage;
  final DataModel? data;
  const SaveOutcome(this.result, {this.errorMessage, this.data});
}

@riverpod
class Feature extends _$Feature {
  @override
  FeatureState build() => const FeatureState();

  Future<SaveOutcome> save() async {
    final params = _buildParams();
    if (params == null) return const SaveOutcome(SaveResult.invalid);
    try {
      final response = await ref.read(featureRepositoryProvider).postData(params);
      return SaveOutcome(SaveResult.success, data: response.data);
    } on ServerException catch (e) {
      return SaveOutcome(SaveResult.failure, errorMessage: e.toString());
    }
  }
}
```
The **view** dispatches UX (snackbar / bottom sheet / navigation) on the outcome. Catch only `ServerException`. Let truly unexpected exceptions propagate.

**AsyncNotifier** — return `AsyncValue<T>` directly. If the fetch depends on another provider, `ref.watch(...)` inside `build()` for an automatic re-run; only set `const AsyncLoading()` manually when a shimmer is actually wanted. Use `state.value` (no `.valueOrNull` in this version). Never `copyWithPrevious` (internal member).

**FutureProvider** (hand-written, cancelable)
```dart
final featureDataProvider = FutureProvider<DataModel>((ref) async {
  final response = await ref.read(featureRepositoryProvider)
      .fetchData(cancelToken: ref.cancelToken());
  return response.data;
});
```

## Step 4 — Hard rules
- **No UI side effects in notifiers**: no `MessageUtils.showSnackBar`, `showSuccessBottomSheet`, or `Go.*`. No `runSafely(onError: …showSnackBar)`. Return outcomes; the view renders UX.
- Any repository fetch passes `cancelToken: ref.cancelToken()` (exception: auto-disposing action-only notifiers — see `/auth-flow-gotchas` #4).
- Naming: `class Xxx extends _$Xxx` → `xxxProvider`. Prefer the bare class name (drop the `Notifier` suffix) unless it clashes with a type in scope.
- State classes only when there are multiple independent fields; `Equatable` with `props`.

## Step 5 — Generate & verify
- `dart run build_runner build --delete-conflicting-outputs`
- If build_runner fails after changing a state type: `rm` the stale `.g.dart` first, then rebuild.
- Confirm the generated provider variable name in `{name}_provider.g.dart`.
- `flutter analyze` clean. If the IDE still shows errors for generated symbols but analyze is clean → restart the Dart Analysis Server.
- Add the export line to the feature's `{feature}_presentation_imports.dart`.
