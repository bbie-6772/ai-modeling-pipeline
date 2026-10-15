"""python -m asset_pipeline RUN.json -- offline evidence gate only."""
import argparse
import json
from pathlib import Path
from .workflow import validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--blender', type=Path, help='Opt-in Blender executable for a registered vertex edit plan')
    parser.add_argument('--output', help='New relative .blend candidate path; requires --blender')
    args = parser.parse_args()
    try:
        run = json.loads(args.run.read_text(encoding='utf-8'))
        root = args.run.resolve().parent
        if bool(args.blender) != bool(args.output):
            raise ValueError('--blender and --output must be provided together')
        if args.blender:
            from .blender_adapter import execute_blender
            result = execute_blender(run, root, args.output, args.blender)
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
            return 0 if result['status'] == 'candidate-pending-qa' else 2
        result = validate(run, root)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        result = {'status': 'blocked', 'errors': [str(exc)], 'transition_allowed': False,
                  'execution_allowed': False, 'detail_allowed': False, 'assets_modified': False}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result['transition_allowed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
