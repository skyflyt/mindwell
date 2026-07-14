from __future__ import annotations

import json
from pathlib import Path


CORE_TASKS = [
    {
        "id": "weekday-startup",
        "title": "Weekday second-brain startup",
        "schedule": {"days": ["mon", "tue", "wed", "thu", "fri"], "time": "08:00"},
        "prompt_file": "automations/prompts/weekday-startup.md",
        "enabled": True,
    },
    {
        "id": "weekly-review",
        "title": "Weekly review and next-week setup",
        "schedule": {"days": ["fri"], "time": "15:30"},
        "prompt_file": "automations/prompts/weekly-review.md",
        "enabled": True,
    },
    {
        "id": "memory-maintenance",
        "title": "Weekly memory maintenance",
        "schedule": {"days": ["mon"], "time": "07:45"},
        "prompt_file": "automations/prompts/memory-maintenance.md",
        "enabled": True,
    },
    {
        "id": "weekly-health-check",
        "title": "Weekly Mindwell health check",
        "schedule": {"days": ["sun"], "time": "09:00"},
        "prompt_file": "automations/prompts/weekly-health-check.md",
        "enabled": True,
    },
]


PROMPTS = {
    "weekday-startup": """# Weekday second-brain startup

Before work, check `automations/runs/weekday-startup-YYYY-MM-DD.md` using the local
date. If it exists, stop and report that this run was already completed. Otherwise,
create it immediately with the timestamp and task ID.

Work only inside this vault. Read the agent entry point, retrieve current priorities,
open or create today's daily note, and prepare a short startup brief with priorities,
appointments already recorded in the vault, open loops, and likely blockers. Mark
unknowns as unknown. Do not send messages or change external systems.
""",
    "weekly-review": """# Weekly review and next-week setup

Before work, check `automations/runs/weekly-review-YYYY-MM-DD.md` using the local date.
If it exists, stop and report that this run was already completed. Otherwise, create
it immediately with the timestamp and task ID.

Work only inside this vault. Review this week's daily notes, projects, meetings,
decisions, and action items. Create a dated weekly review containing wins, completed
work, open loops, blockers, promises owed by or to the user, and the top priorities
for next week. Cite source note paths. Update current-state pages only when the
evidence is clear. Do not send the review automatically.
""",
    "memory-maintenance": """# Weekly memory maintenance

Before work, check `automations/runs/memory-maintenance-YYYY-MM-DD.md` using the local
date. If it exists, stop and report that this run was already completed. Otherwise,
create it immediately with the timestamp and task ID.

Work only inside this vault. Review recent notes for durable preferences, decisions,
and stable facts. Propose a compact MEMORY.md update, preserve source links, and keep
temporary task state out of durable memory. Preserve contradictions instead of
silently choosing a side. Do not modify external systems.
""",
    "weekly-health-check": """# Weekly Mindwell health check

Before work, check `automations/runs/weekly-health-check-YYYY-MM-DD.md` using the local
date. If it exists, stop and report that this run was already completed. Otherwise,
create it immediately with the timestamp and task ID.

Work only inside this vault. Read `config/installation.json`, run the recorded
Mindwell doctor command if available, confirm the required core files and external
index are present, and review `automations/plan.json` plus the last seven days of run
stamps for missing or duplicate runs. Write a dated report under
`automations/health/`. Surface actionable failures clearly. Do not repair files,
register schedules, contact anyone, or change external systems automatically.
""",
}


def write_automation_plan(vault: Path, bundle: str = "core",
                          timezone: str = "local", force: bool = False) -> list[Path]:
    if bundle not in {"none", "core"}:
        raise ValueError(f"unknown automation bundle: {bundle}")
    root = vault / "automations"
    root.mkdir(parents=True, exist_ok=True)
    tasks = [] if bundle == "none" else CORE_TASKS
    created = []
    for task in tasks:
        path = vault / task["prompt_file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if force or not path.exists():
            path.write_text(PROMPTS[task["id"]], encoding="utf-8")
            created.append(path)
    plan = {
        "schema_version": 1,
        "bundle": bundle,
        "timezone": timezone,
        "registration_status": "not_registered",
        "safety": {
            "external_sends": "never_without_confirmation",
            "default_output": "vault_note_or_draft",
        },
        "tasks": tasks,
    }
    plan_path = root / "plan.json"
    if force or not plan_path.exists():
        plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        created.append(plan_path)
    register = root / "REGISTER-WITH-YOUR-AGENT.md"
    if force or not register.exists():
        register.write_text("""# Register the Mindwell automations

Ask your AI agent:

> Read `automations/plan.json` and each referenced prompt. Show me the proposed
> schedules in my local timezone. If this AI product supports scheduled tasks,
> offer to register every enabled task. Ask before creating them, avoid duplicates,
> and never enable automatic external sending. If scheduling is unavailable, explain
> that clearly and give me a simple manual fallback.

After registration, update `registration_status` to `registered` and record the task
IDs returned by the scheduler. The plan remains the human-readable source of truth.
""", encoding="utf-8")
        created.append(register)
    return created
