#!/usr/bin/env python3
"""UserPromptSubmit hook: names the session when a prompt starts with /spec-batch.

- `/spec-batch <spec paths or Figma links>` -> "<spec names> · planning"
- `/spec-batch <plan> merge`                -> "<plan> · merge"
- `/spec-batch` or `/spec-batch <plan> [label]` -> "<plan> · Batch N: <title>", read from
  specs/_progress/<plan>.md (the in-progress batch, else the first pending one whose
  design isn't deferred).

Prints nothing — leaving the generated title alone — when the prompt isn't /spec-batch,
the session already has a custom name, several plans are active and none was named,
or no batch is left. Labels are Arabic when FLUTTER_KIT_LANG=ar, or when unset and the
plan file contains Arabic; English otherwise. Never fails the prompt.
"""

import json
import os
import re
import sys

COMMAND = re.compile(r"^\s*/(?:flutter-kit:)?spec-batch(?:\s+(.*))?$", re.S)
STATUS_ACTIVE = re.compile(r"^Status:\s*active\b", re.M | re.I)
# Status is the LAST " — " segment, so titles may contain dashes themselves.
BATCH = re.compile(r"^###\s+(\d+)\.\s+(.+)\s+—\s+(in-progress|pending|done|deferred)\b", re.M | re.I)
DESIGN = re.compile(r"^Design:\s*(.*)$", re.M | re.I)
ARABIC = re.compile(r"[؀-ۿ]")
MAX_LEN = 80

LABELS = {
    "en": {"batch": "Batch", "planning": "planning", "merge": "merge"},
    "ar": {"batch": "الدفعة", "planning": "تخطيط", "merge": "دمج"},
}


def language(text: str) -> str:
    forced = os.environ.get("FLUTTER_KIT_LANG", "").strip().lower()
    if forced in LABELS:
        return forced
    return "ar" if ARABIC.search(text or "") else "en"


def read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def plan_files(cwd: str) -> dict:
    folder = os.path.join(cwd, "specs", "_progress")
    if not os.path.isdir(folder):
        return {}
    return {
        name[:-3]: os.path.join(folder, name)
        for name in sorted(os.listdir(folder))
        if name.endswith(".md")
    }


def next_batch(text: str):
    """Returns (number, title) of the batch to work on, or None."""
    batches = []
    for match in BATCH.finditer(text):
        body_end = text.find("\n###", match.end())
        body = text[match.end(): body_end if body_end != -1 else len(text)]
        design = DESIGN.search(body)
        batches.append({
            "number": match.group(1),
            "title": match.group(2).strip(),
            "status": match.group(3).lower(),
            "deferred": bool(design and design.group(1).strip().lower().startswith("deferred")),
        })
    for batch in batches:
        if batch["status"].startswith("in-progress"):
            return batch["number"], batch["title"]
    for batch in batches:
        if batch["status"].startswith("pending") and not batch["deferred"]:
            return batch["number"], batch["title"]
    return None


def spec_label(token: str) -> str:
    if token.startswith("http"):
        return "Figma"
    stem = os.path.splitext(os.path.basename(token.rstrip("/")))[0] or token
    return re.sub(r"-flutter$", "", stem.lstrip("_"))


def title_for(prompt: str, cwd: str):
    match = COMMAND.match(prompt)
    if not match:
        return None
    args = (match.group(1) or "").split()
    plans = plan_files(cwd)

    # First word naming an existing plan -> continue it; the rest is a label (or "merge").
    is_plan_name = bool(args) and args[0] in plans
    if args and not is_plan_name:
        if len(args) == 1 and "/" not in args[0] and not args[0].endswith(".md") \
                and not args[0].startswith("http"):
            return None  # a plan name that doesn't exist here
        # Planning run: name it after the specs (or Figma) it starts from.
        names = []
        for token in args:
            label = spec_label(token)
            if label not in names:
                names.append(label)
        shown = ", ".join(names[:2]) + ("…" if len(names) > 2 else "")
        sample = " ".join(read(path)[:4000] for path in plans.values())
        return f"{shown} · {LABELS[language(sample)]['planning']}"

    if is_plan_name:
        plan, text = args[0], read(plans[args[0]])
        if len(args) > 1 and args[1].lower() == "merge":
            return f"{plan} · {LABELS[language(text)]['merge']}"
    else:
        active = {name: read(path) for name, path in plans.items()}
        active = {name: text for name, text in active.items() if STATUS_ACTIVE.search(text)}
        if len(active) != 1:
            return None
        plan, text = next(iter(active.items()))

    batch = next_batch(text)
    if not batch:
        return None
    number, title = batch
    return f"{plan} · {LABELS[language(text)]['batch']} {number}: {title}"


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("session_title"):
        return 0  # the user (or an earlier hook) already named this session
    try:
        title = title_for(data.get("prompt") or "", data.get("cwd") or os.getcwd())
    except Exception:
        return 0
    if not title:
        return 0
    if len(title) > MAX_LEN:
        title = title[: MAX_LEN - 1].rstrip() + "…"
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "sessionTitle": title}
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
