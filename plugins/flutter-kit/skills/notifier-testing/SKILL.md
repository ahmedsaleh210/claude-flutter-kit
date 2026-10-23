---
name: notifier-testing
description: Write a unit test for a Riverpod Notifier / AsyncNotifier / action-notifier (or an interceptor that touches Riverpod state) in a feature-based Riverpod Flutter app, using ProviderContainer + mocktail. Covers the Mock-vs-Fake trap for NotifierProviders, container lifecycle, fallback registration, and the three-point outcome assertion. Use when adding or updating anything under test/.
---

# Notifier unit testing (ProviderContainer + mocktail)

In this architecture notifiers return **outcomes** and never touch UI, so they test as plain `test()` — no `testWidgets`, no pumped `MaterialApp`, no `ScreenUtilInit`. If a notifier calls `MessageUtils.showSnackBar` / `Go.*` / `showSuccessBottomSheet`, fix the notifier (see `/riverpod`) — don't paper over it with a widget test. What the *screen* does with the outcome (which branch renders, what a tap opens) is a widget test: see `/widget-testing`.

## Step 0 — Mirror the nearest existing test
If the repo already has a `*_provider_test.dart` (or a testing guide alongside one), copy its structure — same `setUp`/`tearDown`, mock declarations, and Arrange/Act/Assert shape. Start from scratch only when there's no prior test.

## Step 1 — Container lifecycle (isolation)
Create a fresh `ProviderContainer` in `setUp`, dispose it in `tearDown` — leaked listeners across tests cause flaky CI failures.
```dart
late ProviderContainer container;
setUp(() {
  container = ProviderContainer(overrides: [ /* see Step 3 */ ]);
});
tearDown(() => container.dispose());
```

## Step 2 — THE trap: Mock works for `Provider`, NOT for `NotifierProvider`
mocktail `Mock` intercepts every member — which breaks a `Notifier`'s `build()` / `state` machinery and makes Riverpod crash. So:
- **Plain `Provider` dependency** (a repository, a service) → `class _MockRepo extends Mock implements FeatureRepository {}` and `overrideWithValue(_MockRepo())`.
- **The dependency is itself a Riverpod `Notifier`** → **hand-roll a real subclass**, override only the methods the unit under test calls, record calls with plain counters/last-value fields, and `overrideWith(() => fake)`. The shared `UserProvider` is the most common such dependency:
```dart
class _FakeUserProvider extends UserProvider {
  int setUserLoggedInCalls = 0;
  UserModel? lastLoggedInUser;
  @override
  Future<void> setUserLoggedIn({required UserModel user}) async {
    setUserLoggedInCalls++;
    lastLoggedInUser = user;
  }
}
```
If `test/helpers/fake_user_provider.dart` exists, reuse its `FakeUserProvider` instead of declaring a new one. A fake carries only the surface the unit actually touches — override one method if the unit calls one, two if it calls two. Don't stub methods the code path never reaches.

## Step 3 — Wire the overrides
```dart
container = ProviderContainer(overrides: [
  networkServiceProvider.overrideWithValue(_MockNetworkService()), // plain Provider → value
  featureRepositoryProvider.overrideWithValue(repo),               // plain Provider → value
  userProvider.overrideWith(() => userFake),                       // NotifierProvider → factory
]);
```
- `overrideWithValue(x)` — hands the container an already-built instance (plain `Provider`s).
- `overrideWith(() => notifier)` — Riverpod calls the factory then runs `build()` on it (`NotifierProvider`s only).

## Step 4 — Register fallbacks for custom param types
Any non-nullable custom type passed to `any()` / `captureAny()` needs a one-time fallback in `setUpAll`, or you get `null is not a valid value for parameter of type Foo`:
```dart
setUpAll(() {
  registerFallbackValue(const FeatureParams(/* minimal valid instance */));
});
```
Register one per param type matched with `any()`.

## Step 5 — Arrange / Act / Assert with three orthogonal checks
```dart
test('success: calls repo, persists, returns success', () async {
  // Arrange
  final model = _model();
  when(() => repo.save(any())).thenAnswer((_) async => _wrap(model));
  container.read(featureProvider.notifier).setField('value');

  // Act
  final outcome = await container.read(featureProvider.notifier).save();

  // Assert — 1) output, 2) outbound interaction, 3) side effects
  expect(outcome.result, SaveResult.success);                          // 1 output
  final params = verify(() => repo.save(captureAny())).captured.single as FeatureParams;
  expect(params.field, 'value');                                       // 2 outbound + args
  expect(userFake.setUserLoggedInCalls, 1);                            // 3 side effect (if relevant)
});
```
- `thenAnswer((_) async => …)` for `Future` returns; `thenThrow(const ServerException('boom'))` for failures.
- Failure case: assert `result == failure` and `errorMessage` (often `contains(...)`); notifiers catch only `ServerException`.
- A skipped path: prove it with `verifyNever(() => repo.x(any()))`.
- A method that rethrows: `await expectLater(container.read(p.notifier).save(), throwsException);`

## Step 5b — Cancellation & lifecycle
A notifier the UI calls through `ref.read` has no listener — Riverpod may dispose it while its request is in flight. A plain `container.read(...)` in a test reproduces exactly that, so test it directly:
```dart
test('requote: request survives with nothing watching the notifier', () async {
  CancelToken? sent;
  when(() => repo.requote(any(), cancelToken: any(named: 'cancelToken')))
      .thenAnswer((invocation) async {
    sent = invocation.namedArguments[#cancelToken] as CancelToken?;
    await Future<void>.delayed(Duration.zero); // let a dispose happen mid-request
    return _ok();
  });

  final outcome = await container.read(requoteProvider.notifier).requote(params); // no listener

  expect(outcome.result, RequoteResult.success);
  expect(sent?.isCancelled ?? false, isFalse); // fails if a token tied to the notifier comes back
});
```
- **Writes** (create, book, pay, submit, delete): assert no cancel token is passed at all (`captureAny(named: 'cancelToken')` → `isNull`).
- **Screen reads** that should cancel on leave: listen to the provider (`container.listen(p, (_, __) {})`), close the subscription, and assert the token was cancelled.
- After a dispose mid-request, the notifier must not touch state: no exception, nothing written (`ref.mounted` guard).

## Step 6 — Run & verify
- One test: `flutter test --plain-name 'success: calls repo'`
- One file: `flutter test test/<...>_test.dart`
- All: `flutter test`

## Checklist
- [ ] `ProviderContainer` fresh in `setUp`, disposed in `tearDown`
- [ ] Notifier dependencies use a hand-rolled subclass + `overrideWith`; plain Providers use `Mock` + `overrideWithValue`
- [ ] `registerFallbackValue` in `setUpAll` for every custom param type used with `any()`
- [ ] Each test asserts output + outbound `verify().called(n)` + side-effect counters
- [ ] Every `ref.read`-called notifier has a cancellation test (Step 5b)
- [ ] Plain `test()` (no `testWidgets` — UI branches belong in `/widget-testing`); only `ServerException` paths exercised for failures
