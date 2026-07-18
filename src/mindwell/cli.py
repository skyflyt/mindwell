from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import run as run_benchmark
from .engine import build, retrieve, OllamaUnavailable
from .doctor import inspect
from .config import load_config
from .guidance import ollama_unreachable_guidance
from .scaffold import init_vault, list_backups, restore_backup, upgrade_vault
from .updater import update as run_update
from .uncertainty import compile_registry
from .automations import write_automation_plan
from .advisor import recommend
from . import __version__


def main() -> int:
    parser = argparse.ArgumentParser(prog="mindwell")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init"); init.add_argument("vault", type=Path); init.add_argument("--force", action="store_true"); init.add_argument("--agent-name"); init.add_argument("--profile", choices=("basic", "personal-ops"), default="basic"); init.add_argument("--automations", choices=("none", "core"), default="none"); init.add_argument("--timezone", default="local"); init.add_argument("--private-workspaces", action="store_true"); init.add_argument("--environment", choices=("sandbox", "native"))
    upgrade = commands.add_parser("upgrade"); upgrade.add_argument("vault", type=Path); upgrade.add_argument("--agent-name"); upgrade.add_argument("--no-backup", action="store_true"); upgrade.add_argument("--dry-run", action="store_true")
    updater = commands.add_parser("update", help="all-in-one: fetch the latest release, upgrade the installed CLI package, then run the vault upgrade"); updater.add_argument("vault", type=Path); updater.add_argument("--source", help="use this local Mindwell checkout instead of fetching from GitHub"); updater.add_argument("--dry-run", action="store_true")
    backups = commands.add_parser("backups", help="list this vault's pre-upgrade backups, newest first"); backups.add_argument("vault", type=Path)
    restore = commands.add_parser("restore", help="restore vault files from a pre-upgrade backup (preview unless --yes)"); restore.add_argument("vault", type=Path); restore.add_argument("--backup", help="backup stamp to restore from (default: most recent)"); restore.add_argument("--yes", action="store_true", help="actually write; without it this is a preview")
    index = commands.add_parser("index"); index.add_argument("vault", type=Path); index.add_argument("--rebuild", action="store_true")
    query = commands.add_parser("retrieve"); query.add_argument("vault", type=Path); query.add_argument("query"); query.add_argument("--mode", choices=("quick", "standard", "deep"), default="standard"); query.add_argument("--explain", action="store_true"); query.add_argument("--no-refresh", action="store_true")
    bench = commands.add_parser("benchmark"); bench.add_argument("vault", type=Path); bench.add_argument("questions", type=Path); bench.add_argument("--mode", default="standard")
    contradictions = commands.add_parser("contradictions"); contradictions.add_argument("vault", type=Path)
    doctor = commands.add_parser("doctor"); doctor.add_argument("vault", type=Path)
    configure = commands.add_parser("configure"); configure.add_argument("vault", type=Path); configure.add_argument("--provider", choices=("lexical", "ollama"), required=True)
    automation = commands.add_parser("automations"); automation.add_argument("vault", type=Path); automation.add_argument("--bundle", choices=("none", "core"), default="core"); automation.add_argument("--timezone", default="local"); automation.add_argument("--force", action="store_true")
    advice = commands.add_parser("recommend"); advice.add_argument("vault", type=Path); advice.add_argument("--prefer-semantic", action="store_true"); advice.add_argument("--basic", action="store_true")
    args = parser.parse_args()
    if args.command == "init":
        result = init_vault(
            args.vault, args.force, args.agent_name, args.profile,
            args.automations, args.timezone, args.private_workspaces,
            args.environment)
        print(json.dumps({key: [str(p) for p in paths] for key, paths in result.items()},
                         indent=2))
    elif args.command == "upgrade":
        result = upgrade_vault(args.vault, args.agent_name,
                               backup=not args.no_backup, dry_run=args.dry_run)
        print(json.dumps(result, indent=2))
        if not result.get("ok"):
            return 1
        doctor_result = result.get("doctor")
        if doctor_result is not None and not doctor_result.get("ready"):
            return 1
    elif args.command == "update":
        result = run_update(args.vault, source=args.source, dry_run=args.dry_run)
        print(json.dumps(result, indent=2))
        if not result.get("ok"):
            return 1
    elif args.command == "backups":
        entries = list_backups(args.vault)
        print(json.dumps({"vault": str(args.vault), "backups": entries,
                          "count": len(entries)}, indent=2))
    elif args.command == "restore":
        result = restore_backup(args.vault, stamp=args.backup, apply=args.yes)
        print(json.dumps(result, indent=2))
        if not result.get("ok"):
            return 1
    elif args.command == "index":
        try:
            print(json.dumps(build(args.vault, args.rebuild), indent=2))
        except OllamaUnavailable as exc:
            guidance = ollama_unreachable_guidance(args.vault, exc.url)
            print(json.dumps({
                "error": "ollama_unreachable",
                "message": str(exc),
                "suggested_fallback": f'mindwell configure "{args.vault}" --provider lexical',
                "guidance": guidance["guidance"],
            }, indent=2))
            return 1
    elif args.command == "retrieve":
        result = retrieve(args.vault, args.query, args.mode, not args.no_refresh)
        if args.explain:
            output = result
        else:
            output = {"results": result["results"], "context": result["context"]}
            if result.get("warnings"):
                output["warnings"] = result["warnings"]
            if result.get("guidance"):
                output["guidance"] = result["guidance"]
        print(json.dumps(output, indent=2))
    elif args.command == "benchmark":
        print(json.dumps(run_benchmark(args.vault, args.questions, args.mode), indent=2))
    elif args.command == "contradictions":
        print(compile_registry(args.vault))
    elif args.command == "doctor":
        result = inspect(args.vault); print(json.dumps(result, indent=2)); return 0 if result["ready"] else 1
    elif args.command == "automations":
        print(json.dumps({"created": [str(p) for p in write_automation_plan(
            args.vault, args.bundle, args.timezone, args.force)]}, indent=2))
    elif args.command == "recommend":
        print(json.dumps(recommend(args.vault, args.prefer_semantic, args.basic), indent=2))
    else:
        path = args.vault / "config" / "mindwell.json"
        config = load_config(args.vault); config["retrieval_provider"] = args.provider
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        installation_path = args.vault / "config" / "installation.json"
        if installation_path.exists():
            installation = json.loads(installation_path.read_text(encoding="utf-8"))
            installation["provider"] = args.provider
            installation_path.write_text(json.dumps(installation, indent=2) + "\n",
                                         encoding="utf-8")
        print(json.dumps({"provider": args.provider, "config": str(path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
