from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import run as run_benchmark
from .engine import build, retrieve
from .doctor import inspect
from .config import load_config
from .scaffold import init_vault
from .uncertainty import compile_registry


def main() -> int:
    parser = argparse.ArgumentParser(prog="loby")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init"); init.add_argument("vault", type=Path); init.add_argument("--force", action="store_true")
    index = commands.add_parser("index"); index.add_argument("vault", type=Path); index.add_argument("--rebuild", action="store_true")
    query = commands.add_parser("retrieve"); query.add_argument("vault", type=Path); query.add_argument("query"); query.add_argument("--mode", choices=("quick", "standard", "deep"), default="standard"); query.add_argument("--explain", action="store_true")
    bench = commands.add_parser("benchmark"); bench.add_argument("vault", type=Path); bench.add_argument("questions", type=Path); bench.add_argument("--mode", default="standard")
    contradictions = commands.add_parser("contradictions"); contradictions.add_argument("vault", type=Path)
    doctor = commands.add_parser("doctor"); doctor.add_argument("vault", type=Path)
    configure = commands.add_parser("configure"); configure.add_argument("vault", type=Path); configure.add_argument("--provider", choices=("lexical", "ollama"), required=True)
    args = parser.parse_args()
    if args.command == "init":
        print(json.dumps({"created": [str(p) for p in init_vault(args.vault, args.force)]}, indent=2))
    elif args.command == "index":
        print(json.dumps(build(args.vault, args.rebuild), indent=2))
    elif args.command == "retrieve":
        result = retrieve(args.vault, args.query, args.mode)
        print(json.dumps(result if args.explain else {"results": result["results"],
                                                     "context": result["context"]}, indent=2))
    elif args.command == "benchmark":
        print(json.dumps(run_benchmark(args.vault, args.questions, args.mode), indent=2))
    elif args.command == "contradictions":
        print(compile_registry(args.vault))
    elif args.command == "doctor":
        result = inspect(args.vault); print(json.dumps(result, indent=2)); return 0 if result["ready"] else 1
    else:
        path = args.vault / "config" / "loby.json"
        config = load_config(args.vault); config["retrieval_provider"] = args.provider
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"provider": args.provider, "config": str(path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
