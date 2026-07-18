"""The all-in-one `mindwell update`: bring the CLI package AND the vault current
in one invocation, so a user (or their agent) never has to think about the
package layer versus the vault layer separately.

Phases, in order:

1. Resolve a source checkout of the newest tagged release — a managed clone
   under the Mindwell cache (never a synced folder), fetched/refreshed each
   run, or any local checkout passed via --source (used by tests and offline
   machines).
2. Upgrade the installed package with `<this interpreter> -m pip install` into
   the environment that is running this very command — by definition the right
   target. Verified safe on Windows even when invoked through mindwell.exe:
   pip stashes the in-use launcher via os.rename (rename of a running exe is
   allowed on NTFS; deletion is not), so self-replacement works. Never
   downgrades: a source older than the installed version is skipped with a
   note instead of installed.
3. Run the vault reconcile as a CHILD process: `python -m mindwell.cli upgrade
   <vault>`. A fresh interpreter imports the just-installed package, so the
   vault phase always executes under the NEW version even though this parent
   process keeps the old code in memory. All of `upgrade`'s guarantees ride
   along unchanged (never overwrites AGENTS.md/AGENT.md or user-modified
   files, backs up before writing, idempotent, ends with doctor).

--dry-run previews both layers without changing anything: the source is still
fetched (read-only apart from the cache clone) so the target version is real,
pip is skipped, and the vault preview runs `upgrade --dry-run` under the
CURRENTLY-installed version — the result notes that a newer version may add
files the old one cannot predict.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from . import __version__
from .config import _cache_root

REPO_URL = "https://github.com/skyflyt/mindwell"
GIT_TIMEOUT = 300
PIP_TIMEOUT = 600


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = GIT_TIMEOUT):
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True, timeout=timeout)


def _version_tuple(version: str) -> tuple:
    return tuple(int(part) for part in re.findall(r"\d+", version)[:3] or [0])


def source_version(source_dir: Path) -> str | None:
    try:
        text = (source_dir / "pyproject.toml").read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r'^version = "([^"]+)"', text, re.M)
    return match.group(1) if match else None


def resolve_source(source: str | None) -> dict:
    """A checkout of the newest tagged release. With --source, the given
    directory is used as-is (no git required — offline/test path). Otherwise a
    managed clone under the cache root is created or fetched and the newest
    v-tag checked out. Returns {ok, dir, tag, version} or {ok: False, error,
    message}."""
    if source:
        src = Path(source).expanduser().resolve()
        version = source_version(src)
        if version is None:
            return {"ok": False, "error": "bad_source",
                    "message": f'"{src}" has no readable pyproject.toml version — not a Mindwell checkout.'}
        return {"ok": True, "dir": str(src), "tag": None, "version": version}

    src = _cache_root() / "src"
    try:
        if (src / ".git").exists():
            fetched = _run(["git", "fetch", "--tags", "--force", "origin"], cwd=src)
        else:
            fetched = _run(["git", "clone", REPO_URL, str(src)])
    except FileNotFoundError:
        return {"ok": False, "error": "git_missing",
                "message": "git is not available on PATH. Install git, or pass "
                           "--source <path-to-a-mindwell-checkout>."}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "git_timeout",
                "message": "git timed out reaching the repository. Check network "
                           "access to github.com, or pass --source <checkout>."}
    if fetched.returncode != 0:
        return {"ok": False, "error": "git_failed",
                "message": ("Could not reach the Mindwell repository "
                            f"({REPO_URL}): {fetched.stderr.strip()[:300]} — check "
                            "github.com egress, or pass --source <checkout>.")}

    tags = _run(["git", "tag", "--list", "v*", "--sort=-v:refname"], cwd=src)
    tag = tags.stdout.split()[0] if tags.returncode == 0 and tags.stdout.split() else None
    if tag is None:
        return {"ok": False, "error": "no_tags",
                "message": "No release tags found in the repository — refusing to "
                           "update from an untagged (prerelease) state."}
    checked = _run(["git", "checkout", "-q", "--force", tag], cwd=src)
    if checked.returncode != 0:
        return {"ok": False, "error": "git_checkout_failed",
                "message": checked.stderr.strip()[:300]}
    version = source_version(src)
    if version is None:
        return {"ok": False, "error": "bad_source",
                "message": f"Checked out {tag} but could not read its version."}
    return {"ok": True, "dir": str(src), "tag": tag, "version": version}


def decide_cli_action(installed: str, available: str) -> str:
    """"install" | "already-current" | "skip-newer-installed". Never downgrades:
    an installed version ahead of the newest tag (a dev machine) is left alone."""
    inst, avail = _version_tuple(installed), _version_tuple(available)
    if avail > inst:
        return "install"
    if avail == inst:
        return "already-current"
    return "skip-newer-installed"


def pip_install(source_dir: str) -> dict:
    result = _run([sys.executable, "-m", "pip", "install", "--upgrade",
                   "--no-input", source_dir], timeout=PIP_TIMEOUT)
    out = {"ok": result.returncode == 0}
    if not out["ok"]:
        out["error"] = (result.stderr or result.stdout).strip()[-600:]
    return out


def run_vault_upgrade(vault: Path, dry_run: bool) -> dict:
    """The vault phase, as a fresh child interpreter so it runs the
    just-installed package version, not the code loaded in this process."""
    cmd = [sys.executable, "-m", "mindwell.cli", "upgrade", str(vault)]
    if dry_run:
        cmd.append("--dry-run")
    result = _run(cmd, timeout=PIP_TIMEOUT)
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        payload = {"ok": False, "error": "upgrade_output_unreadable",
                   "message": (result.stderr or result.stdout).strip()[-600:]}
    return payload


def registered_schedule_note(vault: Path) -> str | None:
    """The post-upgrade reminder from AGENTS.md step 6: a scheduler that captured
    prompt text at registration time keeps running the old wording after an
    upgrade refreshes automations/prompts/*.md."""
    plan_path = vault / "automations" / "plan.json"
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if plan.get("registration_status") != "registered":
        return None
    return ("This vault's automation schedules are registered with a scheduler. "
            "If the upgrade updated any automations/prompts/*.md file, compare the "
            "registered prompts and offer to re-register the changed ones.")


def update(vault: Path, source: str | None = None, dry_run: bool = False) -> dict:
    """Both layers, one call. Returns one aggregated JSON-able result; ok is
    True only when every phase that ran succeeded."""
    vault = vault.expanduser().resolve()
    resolved = resolve_source(source)
    if not resolved["ok"]:
        return {"ok": False, "dry_run": dry_run, "phase": "resolve-source", **resolved}

    action = decide_cli_action(__version__, resolved["version"])
    cli_report = {
        "installed_version": __version__,
        "available_version": resolved["version"],
        "source_dir": resolved["dir"],
        "source_tag": resolved["tag"],
        "action": action,
    }
    if action == "skip-newer-installed":
        cli_report["note"] = ("Installed version is newer than the latest release "
                              "tag — leaving the package alone (never downgrades).")

    pip_report = None
    if action == "install" and not dry_run:
        pip_report = pip_install(resolved["dir"])
        if not pip_report["ok"]:
            return {"ok": False, "dry_run": dry_run, "phase": "pip-install",
                    "cli": cli_report, "pip": pip_report,
                    "message": "Package install failed; the vault was not touched. "
                               "Nothing is half-applied — fix the pip error and re-run."}
    elif action == "install" and dry_run:
        cli_report["note"] = (f"dry run: would install {resolved['version']} "
                              f"(currently {__version__}); vault preview below is "
                              "computed by the currently-installed version — a newer "
                              "version may add files it cannot predict.")

    vault_report = run_vault_upgrade(vault, dry_run)

    result = {
        "ok": bool(vault_report.get("ok")),
        "dry_run": dry_run,
        "cli": cli_report,
        "pip": pip_report,
        "vault_upgrade": vault_report,
    }
    note = registered_schedule_note(vault)
    if note:
        result["post_steps"] = [note]
    return result
