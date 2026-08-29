"""SuperApp - unified entry point merging OneAgent + the BA/QA suite.

Usage:
    python superapp.py modules
    python superapp.py ask "question"
    python superapp.py agent "task"
"""

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

_secrets = Path.home() / "secrets"
if _secrets.is_dir():
    sys.path.insert(0, str(_secrets))
    try:
        import load_env  # noqa: F401 - optional local env injection
    except ImportError:
        pass

ROOT = Path(__file__).parent
ONEAGENT = ROOT / "oneagent"
BAQA = ROOT / "baqa"

for p in (str(ONEAGENT), str(BAQA)):
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)


def cmd_modules(_args):
    rows = []
    try:
        sys.path.insert(0, str(BAQA))
        import cli as baqa_cli
        # baqa's own modules command lists everything; run it
        r = subprocess.run([sys.executable, "cli.py", "modules"],
                           cwd=str(BAQA), capture_output=True, text=True,
                           timeout=60)
        baqa_out = (r.stdout or "").strip()
    except Exception as e:
        baqa_out = "(registry unavailable: %s)" % e

    try:
        oneagent_main = __import__("main")
        caps = getattr(oneagent_main, "CAPABILITIES", None)
        rows.append(("oneagent", ", ".join(list(caps)[:6]) if caps
                     else "autonomous agent loop"))
    except Exception as e:
        rows.append(("oneagent", "unavailable: %s" % e))

    print("SuperApp modules")
    print("=" * 60)
    print("--- BA/QA suite ---")
    print(baqa_out)
    print("--- OneAgent ---")
    for name, desc in rows:
        print("  %-28s %s" % (name, desc))


def cmd_ask(args):
    os.chdir(BAQA)
    sys.path.insert(0, str(BAQA))
    import cli as baqa_cli
    ns = argparse.Namespace(question=args.question)
    ns.prompt = args.question
    ns.task = "general"
    ns.module = None
    if hasattr(baqa_cli, "cmd_ask"):
        asyncio.run(baqa_cli.cmd_ask(ns))
    else:
        print("ask not available in baqa cli")


def cmd_agent(args):
    import runpy
    os.chdir(ONEAGENT)
    try:
        runpy.run_path(str(ONEAGENT / "main.py"), run_name="__main__")
    except SystemExit:
        pass


def main():
    parser = argparse.ArgumentParser(prog="superapp",
                                     description="Unified Super App")
    sub = parser.add_subparsers(dest="cmd")

    p_ask = sub.add_parser("ask", help="ask the LLM router a question")
    p_ask.add_argument("question")

    sub.add_parser("modules", help="list all available modules")

    p_agent = sub.add_parser("agent", help="run autonomous OneAgent loop")
    p_agent.add_argument("task", nargs="?", default="")

    args = parser.parse_args()
    if args.cmd == "ask":
        cmd_ask(args)
    elif args.cmd == "modules":
        cmd_modules(args)
    elif args.cmd == "agent":
        cmd_agent(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
