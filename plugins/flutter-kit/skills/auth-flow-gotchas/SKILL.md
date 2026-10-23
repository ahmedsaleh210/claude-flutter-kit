---
name: auth-flow-gotchas
description: Implement or modify an authentication / onboarding / profile-mutation flow in a feature-based Riverpod Flutter app — login, social sign-in, register, OTP, change-email/phone, or any endpoint that rotates tokens. Surfaces the silent-failure auth contracts (backend-specific login outcomes, bearer-only vs logged-in, token-rotation order, the autoDispose no-cancelToken rule, and UserProvider's 3-store coordination). Use when touching auth, onboarding, or profile-mutation notifiers.
---

# Auth flow gotchas

Auth is where the "notifier returns an outcome" pattern meets token/session state. These fail **silently** (user looks logged in but isn't, a token update is dropped, a 401 loop logs them out). Each is its own contract.

## 1 — Login outcomes are a backend contract — read it, don't assume it
How login signals "credentials OK but not finished" differs per backend: some return **403** with a discriminating `key` (e.g. `verify_otp` → route to OTP), some are phone-OTP-first (`codeSent`), some return 200 with a flag. **Read CLAUDE.md "Project specifics → Auth" before writing the catch blocks.** Whatever the contract, the shape is the same:
- The login notifier returns an outcome enum with one case per screen the user can land on (`success`, `needsOtp`/`codeSent`, `failed`, …) — the view routes on it (`/riverpod` action notifier).
- Catch the **specific** exception (`ForbiddenException`, …) **before** the general `ServerException`, and discriminate with `e.matchesKey(...)` — never string-compare messages. A 403 the contract doesn't name carries a localized message: return it as `failed` with `errorMessage: e.toString()`.
- `ForbiddenException` / `ServerException` live in `lib/src/core/error/exceptions.dart`.

## 2 — Bearer-only vs logged-in: never collapse them
An account that has a token but hasn't finished onboarding (profile incomplete, phone unverified) is **not** logged in. Confusing the two makes a half-onboarded user look authenticated.
- **Unfinished** (e.g. social sign-in with `user.profileCompleted == false`) → `ref.userController.setBearerOnly(token)` — the token lives in `NetworkService` only, **no persistence** — so complete-profile / verify-otp can authenticate. Return a `needsProfile`-style outcome carrying what the next step needs (`user`, `provider`).
- **Finished** → `await ref.userController.setUserLoggedIn(user: user)` (full auth + persistence).
- **Abandoned onboarding** (user backs out, taps "continue as guest") → every such path owes `ref.userController.clearBearerOnly()`. Otherwise the bearer outlives the flow and the "guest" browses signed-in as far as the backend is concerned. `clearBearerOnly` is a no-op once a real session owns the token, so it's safe on the success path too.
- Model the outcome enum per state that actually exists in this backend (e.g. `SocialAuthResult { cancelled, failed, loggedIn, needsProfile }`) — Project specifics lists them.

## 3 — On a token-rotating mutation, `updateToken` BEFORE `updateUser`
Profile mutations (change-email, change-phone, edit-profile) can return a fresh auth payload with rotated tokens. Persist the token **first**, then the user — reversed order signs the user write with the about-to-be-invalidated old token:
```dart
final user = response.data;
final token = user.token;
if (token != null && token.isNotEmpty) {
  await userController.updateToken(token: token, refreshToken: user.refreshToken);
}
await userController.updateUser(user); // AFTER updateToken
```

## 4 — autoDispose action notifiers: NO cancelToken, capture `ref` BEFORE the await
This is the auth case of the general rule in `/riverpod` → "Cancellation": a token is tied to the provider's lifetime, and these are writes. An action-only notifier with no build state (change-email/phone, OTP verify) auto-disposes *during* its network call. So:
- Pass **no `cancelToken`** — the token would cancel the in-flight request when the notifier disposes.
- Resolve every `ref`-dependent value **before** the `await` — post-`await` `ref` access on a disposed notifier no-ops silently and drops the user/token update:
```dart
final repository = ref.read(profileRepositoryProvider);
final userController = ref.userController; // captured BEFORE await
final response = await repository.verifyEmailChange(params);
await userController.updateToken(...); // uses captured refs, not ref.*
await userController.updateUser(response.data);
```

## 5 — `UserProvider` coordinates three stores; never call `Languages.setLocale()` directly
`ref.userController` (the `UserProvider`) keeps **three** stores in sync: `SecureStorage` (tokens), `CacheStorage` (user payload), and `NetworkService` (bearer). `setUserLoggedIn` writes all three; `setBearerOnly` writes only the network bearer; `logout()` clears all three; `init()` hydrates on startup. When backend-localized profile fields must refresh on a language switch, `refreshProfile()` re-fetches and **carries over the current tokens** (the profile response omits them — forgetting the carry-over logs the user out). Change language only via `ref.read(appLanguageProvider.notifier).change(...)`, never `Languages.setLocale()` directly (Riverpod/easy_localization drift).

## Related
- New unauthenticated endpoint? Register it in `RefreshTokenInterceptor._authEndpoints` (see `/wire-endpoint`) or a 401 triggers the refresh loop → logout.
- Outcome enum + view-dispatch mechanics → `/riverpod` (Action Notifier). Testing these flows → `/notifier-testing`.
