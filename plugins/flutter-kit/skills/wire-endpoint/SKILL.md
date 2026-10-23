---
name: wire-endpoint
description: Wire a backend API endpoint end-to-end in a feature-based Riverpod Flutter app — verify the response shape against the API spec, add the endpoint constant, write the repository method (+ params class when needed) with cancelToken, register the repository provider, and expose a Riverpod provider. Use when integrating a new GET/POST/PUT/PATCH/DELETE endpoint or connecting a screen to real data.
---

# Wire a backend endpoint

## Step 1 — Verify the contract against the API spec
Before writing models, read the API spec to confirm field names and the response envelope. Where the spec lives (a live Swagger/OpenAPI URL, or a synced local copy) and the envelope shape are project facts — read CLAUDE.md "Backend contract" first. Don't guess field names from the screen design.
- Default envelope on this base: lookups return `{ data: { pagination, result } }`, most objects return `{ statusCode, data }`. If CLAUDE.md says otherwise, it wins.
- The `mapper` callback receives the **already-unwrapped `data` field**, not the full envelope.
- **Naming boundary:** when the in-app term differs from the backend's (e.g. app `region` ↔ backend `/states` + `state_id`), translate at the repository boundary — the method/provider use the app term, the `path` uses the backend term. Don't rename either side.

## Step 2 — Add the endpoint constant
Add to `ApiConstants` in `lib/src/core/network/constants/api_endpoints.dart`.
- **Unauthenticated endpoint?** (login / register / OTP / refresh / forgot-password / external-auth) — also register it in `RefreshTokenInterceptor._authEndpoints` (`lib/src/core/network/interceptors/refresh_token_interceptor.dart`). Otherwise a 401 from that endpoint triggers the token-refresh retry loop and force-logs-out the user.

## Step 3 — Params class (only if needed)
Any API-facing method with **more than 2 real params** (excluding `cancelToken`) groups them into a params class:
- GET → `toQueryParameters()`
- POST/PUT body → `toJson()`, then `.removeNullValues()` to strip empty entries.

**Locale/currency ride on headers, not the body.** `ConfigurationInterceptor` sends `Accept-Language` (and the currency header) on every request, so most params need NO locale token. Only add a body language field where an endpoint genuinely requires one — and match the backend's exact key (it is NOT `preferred_locale`). Don't append a locale key to every params class by reflex.

## Step 4 — Repository file + provider (co-located)
Hand-written repository (no codegen). The `xxxRepositoryProvider` is declared **at the top of the repository's own file**, directly above the class — NOT in `setup_service_locators.dart` (that file holds `networkServiceProvider`, the notification service, interceptors, and connectivity — never repositories).

File location:
- **Cross-feature / shared** repo (lookups, anything consumed by more than one feature) → `lib/src/core/shared/repositories/{name}_repository.dart`.
- **Feature-specific** repo → `lib/src/features/{feature}/data/repositories/{name}_repository.dart`.

```dart
final featureRepositoryProvider = Provider<FeatureRepository>(
  (ref) => FeatureRepository(ref.read(networkServiceProvider)),
);

class FeatureRepository {
  final NetworkService _networkService;
  const FeatureRepository(this._networkService);

  Future<BaseModel<DataModel>> fetchData({CancelToken? cancelToken}) =>
      _networkService.callApi<DataModel>(
        NetworkRequest<DataModel>(
          method: RequestMethod.get,
          path: ApiConstants.feature,
          cancelToken: cancelToken,
        ),
        mapper: (json) => DataModel.fromJson(json as Map<String, dynamic>),
      );
}
```
- **Every** method takes `CancelToken? cancelToken` and forwards it — fetches and actions alike. Whether a caller passes one is decided by `/riverpod` → "Cancellation".
- List response mapper: `(json) => List.from(json).map((item) => Model.fromJson(item as Map<String, dynamic>)).toList()`. For the paginated `{ pagination, result: [...] }` shape, read `json['result']`.
- `isFormData: true` ONLY when the body contains `File` objects (image uploads). Plain POSTs must not set it.
- Repeated boilerplate across methods → factor a private generic helper (e.g. a `_fetchList<T>` that reads `json['result']` and maps each element).

## Step 5 — Expose a Riverpod provider
Pick the provider type with the `/riverpod` skill. A read the screen watches passes `cancelToken: ref.cancelToken()`; for actions and writes follow `/riverpod` → "Cancellation" (writes are never cancelled; a token only on a provider something keeps alive):
```dart
final featureDataProvider = FutureProvider<DataModel>((ref) async {
  final response = await ref.read(featureRepositoryProvider)
      .fetchData(cancelToken: ref.cancelToken());
  return response.data;
});
```
- Plain `FutureProvider` for app-lifetime data; `.autoDispose` for screen-scoped data that should refresh on re-entry.
- `.family` for parameterized fetches.
- Locale/currency-reactive caches: check the existing localized-provider factory pattern before adding a plain cache.

## Step 6 — Consume + verify
- Screen consumes via `StatusBuilder` (default `.screenCircularLoading`).
- `flutter analyze` clean; then `/dtd-verify` against a real or mocked response.
