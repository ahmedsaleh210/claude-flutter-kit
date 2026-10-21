---
name: pagination
description: Wire an infinite-scroll / paginated list in a feature-based Riverpod Flutter app using PaginatedListView + the createPaginatedProvider factory. Covers the provider factory (plain vs family), the two ways a filter reaches the fetch (family arg vs ref.watch inside the callback), the repository method with page/pageSize/cancelToken, the { pagination, result } envelope unwrap, the .fromListView/.fromSliverList/.fromGridView variants, filter-driven re-reset via key, and inline item mutations. Two decisions require asking the user first: auto-dispose vs keep-alive, and family-arg vs ref.watch for the filter. Use when a screen shows a backend-backed list that loads more on scroll.
---

# Paginated list (infinite scroll)

The whole system lives in `lib/src/core/widgets/paginated_list_view/`. You declare a provider with a factory, point it at a repository method, and render it with `PaginatedListView`. The `PaginatedListNotifier`/`PaginatedListState` machinery is already built — **don't re-roll loading/loadMore/error/reachedMax logic**.

## Step 0 — ASK before declaring the provider: auto-dispose or keep-alive?

The factory takes `isAutoDispose` (defaults to `true`). This is a real product decision, not a default to assume — **stop and ask the user which they want** before writing the provider, unless they already told you. Frame it like this:

- **`isAutoDispose: true`** (auto-dispose) — provider disposes when the screen is popped and no longer listened to. Re-entering the screen **re-fetches from page 1**. Right for lists that should feel fresh on each visit, or where staleness matters.
- **`isAutoDispose: false`** (keep-alive) — provider survives screen exit; scroll position and loaded pages persist. Re-entering shows the same data without a re-fetch. Right for tab-switched lists where the user bounces in and out and a re-fetch would be jarring / wasteful.

To see what this repo already does, grep the paginated providers for `isAutoDispose: false` — that's precedent, not a rule; confirm with the user for the list you're building.

## Step 0b — Check the endpoint pages by number, not by key
The factory counts **pages**. Over a feed that takes constant top-inserts, page numbers repeat or skip rows, so a keyset-paged endpoint (cursor / last-seen id) must hand-roll its paging in an `AsyncNotifier` instead. Everything below assumes a page-numbered endpoint.

## Step 1 — Pick plain vs family, AND how the filter reaches the fetch — ASK

Two independent choices here. The first (plain vs family) is mechanical; the **second is a real preference — ask the user** when the list is filter/sort-driven, unless they already said.

**Plain vs family:**
- **No filters/sort/args at all** → `createPaginatedProvider<T>` — callback gets `(ref, cancelToken, pageNumber, maxRows)`.
- **Driven by a filter/sort/id** → there are two ways to feed it in (below).

**How the filter reaches `onPageChanged` — ask which the user wants:**

The callback receives `ref`, so a filter can arrive **either** as a family arg **or** by reading another provider inside the callback. Both are valid — pick per the user's preference, don't assume.

- **(A) Family arg** → `createFamilyPaginatedProvider<T, ArgT>`, callback `(ref, arg, cancelToken, pageNumber, maxRows)`. The screen builds the provider instance with the filter: `myListProvider((status: ..., query: ...))`. Use a record type for `ArgT` with several fields. **Trade-off:** explicit and self-contained, but the widget must set `key: ValueKey((...filter...))` to reset on filter change (Step 4), and the filter must be resolvable at the call site.
- **(B) `ref.watch` inside the callback** → plain `createPaginatedProvider<T>`, and inside `onPageChanged` do `final filter = ref.watch(myFilterProvider);` then fetch with it. **Trade-off:** the provider re-runs and resets pagination *automatically* when the watched filter changes (no `key` juggling), and the screen just renders `myListProvider` with no arg — but the dependency is implicit and the provider is coupled to that filter provider. Requires `isAutoDispose: true` (or the watch won't drive a rebuild the way you expect on re-entry) — flag this when combining with the Step 0 choice.

Confirm A vs B with the user before writing the provider. Default lean: **A (family arg)** when the filter is owned by the screen and you want it explicit; **B (`ref.watch`)** when the filter is a shared/global provider that several things react to.

```dart
// Family example — typedef the filter as a record
typedef MyListFilter = ({Status status, String query, SortOption sort});

const _kMaxRows = 10;

final myListProvider = createFamilyPaginatedProvider<ItemModel, MyListFilter>(
  placeholder: ItemModel.placeholder(),     // fake item for the Skeletonizer first-load shimmer
  maxRows: _kMaxRows,
  isAutoDispose: false,                       // ← decided in Step 0
  onPageChanged: (ref, filter, cancelToken, pageNumber, maxRows) async {
    final response = await ref.read(itemRepositoryProvider).getItems(
          ItemQueryParams(
            status: filter.status,
            search: filter.query,
            sortBy: filter.sort.sortBy,
            page: pageNumber,
            pageSize: maxRows,
          ),
          cancelToken: cancelToken,
        );
    return response.data;                      // return List<T> only
  },
);
```

```dart
// Plain example — no filter at all
final itemsProvider = createPaginatedProvider<ItemModel>(
  placeholder: ItemModel.placeholder(),
  maxRows: 10,
  isAutoDispose: true,
  onPageChanged: (ref, cancelToken, pageNumber, maxRows) async =>
      (await ref.read(itemRepositoryProvider).getItems(
            page: pageNumber, maxRows: maxRows, cancelToken: cancelToken,
          )).data,
);
```

```dart
// Option B — plain provider that ref.watch-es a shared filter inside the callback.
// Changing myFilterProvider re-runs build() and resets pagination automatically —
// the screen renders `itemsProvider` with NO arg and NO key.
final itemsProvider = createPaginatedProvider<ItemModel>(
  placeholder: ItemModel.placeholder(),
  maxRows: _kMaxRows,
  isAutoDispose: true,                         // ← B relies on auto-dispose; see Step 0
  onPageChanged: (ref, cancelToken, pageNumber, maxRows) async {
    final filter = ref.watch(myFilterProvider); // implicit dependency; re-fetches on change
    final response = await ref.read(itemRepositoryProvider).getItems(
          ItemQueryParams(
            status: filter.status,
            search: filter.query,
            page: pageNumber,
            pageSize: maxRows,
          ),
          cancelToken: cancelToken,
        );
    return response.data;
  },
);
```

Rules:
- The callback must return `List<T>` — the notifier appends pages itself and infers `reachedMax = result.length < maxRows`. Don't read pagination metadata.
- **Always** pass `cancelToken: cancelToken` through to the repo method (it's the token the notifier registered via `ref.cancelToken()`).
- The model needs a `.placeholder()` factory (fully-populated fake) for the shimmer.
- Keep `_kMaxRows` as a screen-local `const`, not a magic number at the call site.

## Step 2 — Repository method + params

The model is built per "Repository Pattern" and "Params Classes" conventions. The default backend contract wraps paginated lookups as `{ pagination, result: [...] }` (confirm against CLAUDE.md "Backend contract") — **the mapper unwraps `result` and returns just the items**; pagination metadata is ignored (client infers end-of-list).

```dart
Future<BaseModel<List<ItemModel>>> getItems(
  ItemQueryParams params, {
  CancelToken? cancelToken,
}) {
  return _networkService.callApi<List<ItemModel>>(
    NetworkRequest<List<ItemModel>>(
      method: RequestMethod.get,
      path: ApiConstants.items,
      queryParameters: params.toQueryParameters(),
      cancelToken: cancelToken,
    ),
    mapper: (json) {
      final result = (json as Map<String, dynamic>)['result'] as List? ?? [];
      return result
          .map((entry) => ItemModel.fromJson(entry as Map<String, dynamic>))
          .toList();
    },
  );
}
```

Params class exposes `toQueryParameters()` and ends with `.removeNullValues()`. Include `page` and `pageSize`; map them to the backend's exact casing (check the API spec / CLAUDE.md "Backend contract").

## Step 3 — Render with PaginatedListView

Three variants — pick by container:
- `.fromListView` — standalone scrollable list.
- `.fromSliverList` — inside a `CustomScrollView`; supports `headers:` (slivers prepended above the list) and `builder:` (wrap the sliver, e.g. SliverPadding).
- `.fromGridView` — grid; requires `gridDelegate:`.

```dart
final filter = ref.watch(myFilterProvider);
final provider = myListProvider((status: filter.status, query: filter.query, sort: filter.sort));

return RefreshIndicator(
  onRefresh: () async => ref.refresh(provider),
  child: PaginatedListView<ItemModel>.fromListView(
    provider: provider,
    physics: const AlwaysScrollableScrollPhysics(),
    key: ValueKey((filter.status, filter.sort)),   // ← see Step 4
    padding: EdgeInsetsDirectional.fromSTEB(16.w, 0, 16.w, bottomPadding),
    separator: 12.szH,
    itemBuilder: (context, index, item) => ItemCard(item: item),
  ),
);
```

Notes:
- `itemBuilder` is `(context, index, item)` — the unwrapped item, not an AsyncValue.
- Empty / error / loading states are handled internally (lottie empty view, `NoInternetConnectionException` → InternetException widget, Skeletonizer shimmer from `placeholder`). Override only via `onEmpty:` / `onError:` / `initialLoader:` / `bottomLoader:` if the defaults don't fit.
- Scroll triggers `loadMoreData()` at `loadMoreThreshold` (default `0.98`).
- Wrap in `RefreshIndicator` calling `ref.refresh(provider)` for pull-to-refresh.

## Step 4 — Resetting pagination on filter change

**Only relevant for Option A (family arg).** Changing the filter arg creates a *new* provider instance, but the `PaginatedListView` State (scroll controller) is reused unless its `key` changes. **Set `key: ValueKey((...filter fields...))`** so a filter change rebuilds the widget and resets scroll/pages cleanly. Don't imperatively reset — let the key do it.

**Option B needs no key** — the `ref.watch(myFilterProvider)` inside `onPageChanged` re-runs `build()` on filter change and resets pagination itself. Adding a `key` there is redundant.

## Step 5 — Inline item mutations (no refetch)

The notifier exposes immutable item ops — use these to patch one row after a local action (toggle active, delete) instead of refetching:

```dart
ref.read(provider.notifier).updateItem<int>(
  id: item.id,
  idGetter: (entry) => entry.id,
  item: item.copyWith(isActive: isActive),
);
// also: addItem, insertItem, removeItem<ID>(id:, idGetter:), reset(), clear()
```

## Gotchas

- **Built-in reactive watches.** The base `PaginatedListNotifier` may already `ref.watch(...)` global providers (e.g. app language/locale) in `build()`, so those refetch from page 1 automatically — you don't wire them. Check the notifier in `paginated_list_notifier.dart` for what's watched before adding your own; don't duplicate a watch that's already there.
- **`reachedMax` is inferred** from `result.length < maxRows`. If the backend ever returns a full final page exactly equal to `maxRows`, one extra empty fetch happens — that's expected, not a bug.
- Return `List<T>` from `onPageChanged`, never the `BaseModel` — use `response.data`.
- Don't store filter state inside the paginated provider; keep it in a separate `Notifier` and pass it as the family arg.
