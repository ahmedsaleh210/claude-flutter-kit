#!/usr/bin/env bash
# PostToolUse hook: runs `dart format` on a .dart file right after Claude edits it,
# so formatting never needs its own step. Generated files are skipped. Always exits
# 0 — a formatting hiccup must never block an edit.

input=$(cat)
file=$(printf '%s' "$input" | python3 -I -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)

case "$file" in
  *.g.dart | *.freezed.dart | *.gen.dart | *.config.dart | *.mocks.dart) exit 0 ;;
  *.dart) ;;
  *) exit 0 ;;
esac

[ -f "$file" ] || exit 0
command -v dart >/dev/null 2>&1 || exit 0

dart format "$file" >/dev/null 2>&1
exit 0
