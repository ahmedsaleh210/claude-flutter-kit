---
name: widget-testing
description: Write a widget (UI) test for a screen, sheet, dialog or wizard in an RTL-first, feature-based Riverpod Flutter app using the shared pumpApp harness — Arabic EasyLocalization, ScreenUtil, Riverpod overrides, Go.navigatorKey. Covers which UI needs a test, raw-key vs real-Arabic copy, overriding the data provider instead of mocking HTTP, driving taps/steps, and asserting on provider state. Use when a feature adds or changes a screen with branching (access gating, empty/error states, wizard steps) or when adding anything under test/ that calls testWidgets.
---

# Widget testing (pumpApp + ProviderScope overrides)

Notifier logic is covered by plain `test()` (see `/notifier-testing`). A widget test covers what the notifier can't see: **which branch the screen renders and what a tap does** — a gated action showing the access UI instead, an empty list showing the empty view, a wizard's back button turning a page instead of popping. It does not re-test notifier logic through the UI.

## Step 0 — Does this UI need one?
Required when the screen/sheet has a branch a user can hit:
- **access gating** — whatever axis this app has: guest vs logged-in, owner vs staff permissions, plan tiers. CLAUDE.md "Project specifics" names the axis and how the app expresses it,
- empty / error / partial-data states the screen decides itself,
- multi-step flows (wizard / step screens, back behaviour, step validation blocking advance),
- a tap that must navigate, open a sheet/dialog, or mutate a provider,
- **external entry points** — push/notification taps and foreground messages, deep links, app resume — triggered while the app is in a **non-default state**: another tab selected, the target screen not mounted, logged out. These are where `UnmountedRefException` and writes to dead providers hide.

Not required for widgets that only lay out data they're given. Mirror the nearest existing `*_test.dart` under the same feature first.

## Step 1 — File and setup
`test/features/{feature}/…/{screen}_test.dart`, mirroring the `lib/` path.
```dart
import '../../helpers/pump_app.dart';

void main() {
  setUp(setUpWidgetTest); // mock SharedPreferences, quiet + init EasyLocalization
  …
}
```
Never re-roll the `ProviderScope` + `EasyLocalization` + `ScreenUtilInit` + `MaterialApp` tree in a test file — that lives in `test/helpers/pump_app.dart`. If a test needs something the helper lacks, add a parameter there.

## Step 2 — Pump with overrides at the data seam
```dart
final container = await pumpApp(
  tester,
  const SomeScreen(),                          // or Scaffold(body: …) for a bare widget
  overrides: [
    someDataProvider.overrideWith((ref) async => _data()),               // FutureProvider → canned future
    someFamilyProvider(7).overrideWith(_LoadedSome.new),                 // AsyncNotifier family → subclass
    userProvider.overrideWith(() => FakeUserProvider(initialUser: user)), // Notifier → fake
  ],
);
```
- Override the **provider the screen watches** with canned data — not Dio, not the repository's HTTP. For an `AsyncNotifier`, either override the repository provider with a `Mock` (`overrideWithValue`) and let the real notifier run, or subclass the notifier and override `build()`.
- Notifier dependencies use a hand-rolled subclass (`FakeUserProvider` in `test/helpers/` for the user), never a `Mock` — same trap as `/notifier-testing` Step 2. A fake shared by several files moves to `test/helpers/`.
- Access state: drive it through the user fake — a guest is `FakeUserProvider(isLoggedIn: false)`; a permissioned user is a `UserModel` built with the fields this app gates on (see "Project specifics").
- Loading state / endless animation: `settle: false`, then `await tester.pump()` per frame.

## Step 3 — Pick the copy
- `TestCopy.keys` (default): every `LocaleKeys.x` renders as its raw key, so `find.text(LocaleKeys.x)` matches exactly. Use for behaviour.
- `TestCopy.arabic`: the shipped `ar.json`. Use when the test is about layout — overflow with real string lengths, RTL order. Finders still work through `LocaleKeys.x` (it resolves to the Arabic).

## Step 4 — Act and assert
```dart
await tester.tap(find.text(LocaleKeys.next));
await tester.pumpAndSettle();

expect(find.text(LocaleKeys.someStepTitle), findsOneWidget);   // what rendered
expect(container.read(someFlowProvider).step, 1);              // what state did
```
- Assert both sides when a tap matters: the rendered result **and** the provider state from the returned `container`.
- Gated actions: check "Project specifics" for whether this app **hides** or **disables** them. Hidden → `findsNothing` on the action; disabled → assert the disabled state; replaced (e.g. a login prompt for a guest) → assert the replacement UI **and** `findsNothing` on the gated widget.
- Off-screen children: `await tester.scrollUntilVisible(finder, 200)` before tapping.
- Overflow: any `RenderFlex overflowed` fails the test automatically — no extra assertion needed.
- External entry points: put the app in the non-default state first (e.g. tap another tab), then call the same handler the push / deep link calls, `await tester.pumpAndSettle()`, and assert `expect(tester.takeException(), isNull)` plus the expected result (badge updated, screen opened, or nothing — whatever the spec says).
- Text fields: `await tester.enterText(find.byType(TextFormField).first, 'x')`.

## Step 5 — Run
- One file: `flutter test test/features/…/x_test.dart`
- All: `flutter test`

## Checklist
- [ ] `setUp(setUpWidgetTest)` and `pumpApp(...)` — no hand-built app shell
- [ ] Overrides at the watched provider (or repository for an AsyncNotifier), fakes for Notifiers
- [ ] One `testWidgets` per branch: each access state, empty/data, each wizard step
- [ ] Taps assert rendered result + provider state
- [ ] Gated actions asserted the way this app expresses gating (hidden / disabled / replaced)
