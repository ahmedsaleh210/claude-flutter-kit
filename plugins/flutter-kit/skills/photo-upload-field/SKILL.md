---
name: photo-upload-field
description: Build a multi-photo / file picker that supports edit mode (existing remote photos + newly picked local files) in a feature-based Riverpod Flutter app — photo sections, room/gallery photos, avatar, document upload. Covers the two-list local/remote + removedIds model, CustomWidgetValidator min/max sync, the upload-then-merge sheet flow, and the sheet-disposal guards. Use when a screen mixes already-uploaded photos with new picks.
---

# Mixed local/remote photo upload field

The recurring trap: a picker that must show **already-uploaded** photos (remote, deletable) alongside **newly picked** ones (local `File`s, not yet uploaded), validate a min/max across both, and sync removals + additions in one call. Four steps, each with a distinct silent-failure mode. All the widgets/helpers below are shared core infra (`lib/src/core/widgets/`, `lib/src/core/helpers/`) — present in any project on this base.

## Step 1 — Carry TWO lists + a removed-ids set
Hold local picks and remote refs **separately**, plus the ids removed this session. Validation and display combine them:
```dart
late List<File> _photos;                 // new local picks (not yet uploaded)
late List<NetworkFileRef> _remotePhotos; // existing backend photos (NetworkFileRef from core/widgets)
List<int> _removedPhotoIds = const [];   // remote photos the user deleted

List<NetworkFileRef> get _remainingRemotePhotos {
  final removed = _removedPhotoIds.toSet();
  return _remotePhotos.where((p) => !removed.contains(p.id)).toList();
}
```
A single combined list makes per-photo removal and "uploaded vs pending" impossible. If the model serializes, `toJson` **omits `_photos`** — local files upload separately (Step 3).

## Step 2 — Validate min/max across BOTH lists via CustomWidgetValidator
Wrap the picker in `CustomWidgetValidator<List<File>>` and count local + remaining-remote together:
```dart
String? _validatePhotosMin(List<File>? files) {
  if (_minPhotos == 0) return null;
  final total = (files?.length ?? 0) + _remainingRemotePhotos.length;
  return total >= _minPhotos ? null : LocaleKeys.photosMinRequired.interpolate({'min': _minPhotos});
}
```
The picker widgets (`photos_picker_field/`, `photos_dropzone_field.dart`) sync the `FormField` by calling `field.didChange(files)` **inside `WidgetsBinding.addPostFrameCallback`** — a direct `didChange` during build clobbers the form rebuild. For a reactive (state-sourced) count, also `field.validate()` in the post-frame callback so the inline error appears.

## Step 3 — On save: short-circuit, else upload(photos, removedIds), then merge
The upload is an **action notifier** returning an outcome (`/riverpod`) — one call **appends** `photos` and **deletes** `removedIds` together; empty `photos` (pure removal) is allowed.
```dart
Future<void> _onSave() async {
  if (!(_formKey.currentState?.validate() ?? false)) return;

  // Nothing changed (no new files, no removals) → persist local state only, skip the endpoint.
  if (_photos.isEmpty && _removedPhotoIds.isEmpty) { _persistAndPop(); return; }

  final outcome = await ref.read(photoUploadProvider.notifier)
      .upload(photos: _photos, removedIds: _removedPhotoIds /* + section keys */);
  if (!mounted) return; // sheet stayed open during upload — guard before using context/ref

  switch (outcome.result) {
    case UploadResult.success: /* merge outcome.data back into the parent notifier */ _persistAndPop();
    case UploadResult.failure: MessageUtils.showSnackBar(outcome.errorMessage ?? '');
    case UploadResult.invalid: break;
  }
}
```
Two disposal rules — pick by which this sheet does:
- **Stays open during upload** → `if (!mounted) return;` after the `await`.
- **Pops immediately then persists** → capture `ref.read(...notifier)` **before** `Go.back()`; `ref`/`mounted` after pop fails because the sheet `State` is gone.

## Step 4 — Watch the id-less re-upload limitation
If the upload endpoint returns photo **urls but no ids**, photos uploaded **this session** stay as local `File`s — reopening the sheet **re-uploads** them and they can't be individually removed until the parent record is re-fetched. The clean fix is server-side (`{id, url}` pairs); don't paper over it client-side with brittle dedup. Check the repo's TODOs / memory for whether this is a known accepted limitation before "fixing" it.

## Producing the `File`s — reuse, don't rebuild
- `ImageHelper.showImagePicker(Offset)` — platform-adaptive source sheet, camera-permission gate, automatic crop; returns `File?`.
- `FilePickerHelper.pickSingle` / `pickMultiple` — enforces `AppConstants.maxFileSizeInBytes` with a snackbar on oversize.
Both are in `lib/src/core/helpers/`. Don't author a new image-source bottom sheet.

## Checklist
- [ ] Separate `List<File>` + `List<NetworkFileRef>` + `List<int> removedIds`; combined-count getter
- [ ] `CustomWidgetValidator` counts both lists; `didChange`/`validate` inside `addPostFrameCallback`
- [ ] Save short-circuits when nothing changed; otherwise one `upload(photos, removedIds)` call
- [ ] Correct disposal guard (`mounted` after await, or capture-before-`Go.back`)
- [ ] `File`s produced via `ImageHelper` / `FilePickerHelper`, not a hand-rolled picker
