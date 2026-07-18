from __future__ import annotations

import hashlib
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


def _stamp_guard(task_id: str) -> str:
    """Run-stamp guard shared by every scheduled prompt.

    The naive form of this guard ("if the stamp exists, stop") has a proven
    failure mode: a run that writes its stamp and then dies mid-work blocks
    every later retry, silently, for the rest of the day. The `done:` marker
    distinguishes "already completed" from "started and never finished" so a
    dead run gets taken over instead of trusted.
    """
    return f"""Run-stamp guard, before any work, using the local date for YYYY-MM-DD:

1. Read `automations/runs/{task_id}-YYYY-MM-DD.md` if it exists.
2. If it contains a `done:` line, stop and report that this run was already
   completed.
3. If it exists WITHOUT a `done:` line and its timestamp is more than two hours
   old, the earlier run stamped and then died mid-work. Say so in your report,
   then take the run over and continue as a fresh run — a dead stamp must not
   silently block the work.
4. If it exists without a `done:` line and is less than two hours old, another
   run may still be in progress: stop and report that instead.
5. Otherwise create it immediately with the current timestamp and task ID.

When the work is complete, append a final line `done: <timestamp> — <one-line
summary>` to the same stamp file. If you stop early because a required system
is unavailable, leave the stamp WITHOUT a `done:` line and say why — that is
what lets a later retry take the run over instead of skipping the day.
"""


PROMPTS = {
    "weekday-startup": f"""# Weekday second-brain startup

{_stamp_guard("weekday-startup")}
Work only inside this vault. Read the agent entry point, retrieve current priorities,
open or create today's daily note, and prepare a short startup brief with priorities,
appointments already recorded in the vault, open loops, and likely blockers. Mark
unknowns as unknown.

Surface capture gaps: if yesterday included meetings or decisions that left no note
in the vault, list them plainly so the user can record them before they fade — an
unwritten decision does not exist. If nothing has meaningfully changed since
yesterday's brief, say so in one line rather than restating yesterday's content.

Do not send messages or change external systems.
""",
    "weekly-review": f"""# Weekly review and next-week setup

{_stamp_guard("weekly-review")}
Work only inside this vault. Review this week's daily notes, projects, meetings,
decisions, and action items. Create a dated weekly review containing wins, completed
work, open loops, blockers, promises owed by or to the user, and the top priorities
for next week. Cite source note paths.

List decisions made this week that still have no written record in
`wiki/decisions.md`: record the ones with clear evidence in the vault, and name the
ones only the user can state — if it isn't written down, it didn't happen. Close or
archive action items that are resolved; an item whose own text says DONE or RESOLVED
must not stay listed as open.

Update current-state pages only when the evidence is clear. Do not send the review
automatically.
""",
    "memory-maintenance": f"""# Weekly memory maintenance

{_stamp_guard("memory-maintenance")}
Work only inside this vault. Review recent notes for durable preferences, decisions,
and stable facts. Propose a compact MEMORY.md update, preserve source links, and keep
temporary task state out of durable memory. Preserve contradictions instead of
silently choosing a side. Do not modify external systems.
""",
    "weekly-health-check": f"""# Weekly Mindwell health check

{_stamp_guard("weekly-health-check")}
Work only inside this vault. Read `config/installation.json`. Try the recorded
`runner` command first; if it fails, retry with `runner_hint` (a portable form such as
`python3 -m mindwell.cli`) from this environment's own install before concluding the
CLI is unreachable — a `runner` path from a different machine or a past sandbox
session is expected to be dead here, not a failure. If `installation.json` records
`environment: sandbox`, or the recorded `runner` path does not exist on this machine,
treat a missing CLI as expected and report it once as INFO rather than an actionable
failure. Confirm the required core files are present. If the external index is
missing, that is expected too — it self-heals on the next `mindwell retrieve` call —
note it rather than flagging it.

Review `automations/plan.json` plus the last seven days of run stamps for missing
runs, duplicate runs, and stamps with no `done:` line. A stamp without `done:` is a
run that started and never finished — count it as a failed run, not a completed one.
Before declaring any automation dead on the evidence of a single stale file,
corroborate against the other recent stamps and reports: on a synced vault, one
lagging file replica can look stale while everything around it is current.

Write a dated report under `automations/health/`. Reserve "actionable failure" for
missing core files, a corrupt config, or failed/missing/duplicate runs. If everything
is healthy and nothing has changed since last week's report, keep the report to a few
lines instead of restating it. Do not repair files, register schedules, contact
anyone, or change external systems automatically.
""",
}


REGISTER_GUIDE = """# Register the Mindwell automations

Ask your AI agent:

> Read `automations/plan.json` and each referenced prompt. Show me the proposed
> schedules in my local timezone. If this AI product supports scheduled tasks,
> offer to register every enabled task. Ask before creating them, avoid duplicates,
> and never enable automatic external sending. If scheduling is unavailable, explain
> that clearly and give me a simple manual fallback.

After registration, update `registration_status` to `registered` and record the task
IDs returned by the scheduler. The plan remains the human-readable source of truth.
"""


# sha256 digests of the automation files exactly as earlier releases wrote
# them (rendered from each tag's automations.py). `mindwell upgrade` treats a
# vault file matching one of these as unmodified — safe to bring current —
# even though the vault predates scaffold_hashes tracking for these files.
LEGACY_TEMPLATE_HASHES: dict[str, set[str]] = {
    "automations/prompts/weekday-startup.md": {
        # v0.3.0 through v0.4.1
        "e3e5653e250a0e206d2e9b7143cb021dc34b968e2d13a801cd0258dbe60b9ddf",
    },
    "automations/prompts/weekly-review.md": {
        # v0.3.0 through v0.4.1
        "db5a81e0e46b54500fd92dfffb7f85c048b9e58e56abbe84b8734481dc4881ae",
    },
    "automations/prompts/memory-maintenance.md": {
        # v0.3.0 through v0.4.1
        "28b8454ff6af78d42b9eb9a0c1596e1c35d3344a7f31a72d1f3481c2d145a184",
    },
    "automations/prompts/weekly-health-check.md": {
        # v0.3.0
        "59cdab708525b631560763714f3554d3d71a29728833fcde0208ac814f6bae6b",
        # v0.4.0, v0.4.1
        "5ce8bccba0943e8623c0bf391c9d52373d359fa8ddc5ab679a143d729ff0ac41",
    },
    "automations/REGISTER-WITH-YOUR-AGENT.md": {
        # v0.3.0 through v0.4.1
        "bacdc10102c5e45f25844a08ad49f48d5a42e510a3135feb17d3ccbd0b79ead7",
    },
}


def automation_template_files(bundle: str) -> dict[str, str]:
    """Relative-path -> template content for the reconcilable automation files.

    Everything here is a pure template, safe for the same hash-based
    create/repair/preserve reconciliation as the scaffold files. plan.json is
    deliberately excluded: it is stateful (registration_status, scheduler task
    IDs), so it is only ever created when missing, never reconciled.
    """
    if bundle == "none":
        return {}
    files = {task["prompt_file"]: PROMPTS[task["id"]] for task in CORE_TASKS}
    files["automations/REGISTER-WITH-YOUR-AGENT.md"] = REGISTER_GUIDE
    return files


def write_automation_plan(vault: Path, bundle: str = "core",
                          timezone: str = "local", force: bool = False,
                          scaffold_hashes: dict | None = None) -> list[Path]:
    if bundle not in {"none", "core"}:
        raise ValueError(f"unknown automation bundle: {bundle}")
    root = vault / "automations"
    root.mkdir(parents=True, exist_ok=True)
    tasks = [] if bundle == "none" else CORE_TASKS
    created = []

    def record(relative: str, body: str) -> None:
        if scaffold_hashes is not None:
            scaffold_hashes[relative] = hashlib.sha256(
                body.encode("utf-8")).hexdigest()

    for task in tasks:
        path = vault / task["prompt_file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if force or not path.exists():
            path.write_text(PROMPTS[task["id"]], encoding="utf-8")
            record(task["prompt_file"], PROMPTS[task["id"]])
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
        register.write_text(REGISTER_GUIDE, encoding="utf-8")
        record("automations/REGISTER-WITH-YOUR-AGENT.md", REGISTER_GUIDE)
        created.append(register)
    return created
