"""Generate a read-only AI asset task plan from an existing specification.

Usage: python -m asset_pipeline.plan_cli templates/ai-plan-request.example.json
       python -m asset_pipeline.plan_cli REQUEST.json --output PLAN.json
"""
import argparse
import json
import sys
from pathlib import Path

from .planner import build_plan, check_plan


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate an advisory asset task plan; no Blender or MCP calls")
    parser.add_argument("request", type=Path, help="JSON with specification and optional planning_options")
    parser.add_argument("--output", type=Path, help="Write a NEW JSON file (never overwrites an existing one)")
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        if not isinstance(request, dict) or not isinstance(request.get("specification"), dict):
            raise ValueError("Expected JSON object with specification")
        plan = build_plan(request["specification"], request.get("planning_options"))
        check_plan(plan)
        output = json.dumps(plan, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(output)
            print(str(args.output))
        else:
            print(output, end="")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
