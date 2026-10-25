#!/usr/bin/env python3
"""UserPromptSubmit hook: names the session when a prompt starts with /spec-batch.

- `/spec-batch <new-plan> <spec paths or Figma links>` -> "<new-plan> · planning"
- `/spec-batch <spec paths or Figma links>` -> "<spec names> · planning", then
  "<plan> · planning" on a later prompt, once the planning run has written
  specs/_progress/<plan>.md with `Planning session: <this session id>`
- `/spec-batch <plan> merge`                -> "<plan> · merge"
- `/spec-batch` or `/spec-batch <plan> [label]` -> "<plan> · Batch N: <title>", read from
  specs/_progress/<plan>.md (the in-progress batch, else the first pending one whose
  design isn't deferred).

Prints nothing — leaving the generated title alone — when the prompt isn't /spec-batch,
the session already has a custom name (a planning name is still upgraded to the
plan's), several plans are active and none was named,
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
PLANNING_SESSION = re.compile(r"^Planning session:\s*(\S+)", re.M | re.I)
PLAN_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
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
    sample = " ".join(read(path)[:4000] for path in plans.values())
    # A new kebab-case name before the specs -> it's the new plan's name.
    if len(args) > 1 and not is_plan_name and PLAN_NAME.match(args[0]) \
            and not os.path.exists(os.path.join(cwd, args[0])):
        return f"{args[0]} · {LABELS[language(sample)]['planning']}"
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


def planned_here(session_id: str, cwd: str):
    """Returns "<plan> · planning" for the plan this session is planning, or None."""
    if not session_id:
        return None
    for name, path in plan_files(cwd).items():
        text = read(path)
        match = PLANNING_SESSION.search(text)
        if match and match.group(1) == session_id:
            return f"{name} · {LABELS[language(text)]['planning']}"
    return None


def is_planning_title(title: str) -> bool:
    return any(title.endswith(f" · {labels['planning']}") for labels in LABELS.values())


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    current = data.get("session_title") or ""
    cwd = data.get("cwd") or os.getcwd()
    try:
        if current:
            # Named already: only upgrade our own "<specs> · planning" to the plan's name.
            title = planned_here(data.get("session_id") or "", cwd) \
                if is_planning_title(current) else None
            if title == current:
                title = None
        else:
            title = title_for(data.get("prompt") or "", cwd)
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
