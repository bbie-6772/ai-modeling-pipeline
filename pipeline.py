"""Offline evidence gate. Never opens Blender or modifies input assets."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def local_file(root, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError('Expected a relative file path')
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Missing file or path outside project: ' + value)
    return path


def validate(config, root):
    errors = []
    try:
        if config['project'] != 'Minor On Air' or config['variant'] != 'C':
            raise ValueError('Project/variant mismatch')
        if config['mode'] != 'validate-only':
            raise ValueError('Only validate-only is implemented')
        assets = config['assets']
        if not isinstance(assets, list) or not assets:
            raise ValueError('No baseline assets')
        roles = {a['role'] for a in assets}
        if not {'design', 'reference', 'baseline', 'candidate', 'evidence'} <= roles:
            raise ValueError('Missing required asset roles')
        paths = []
        hashes = {}
        for asset in assets:
            path = local_file(root, asset['path'])
            if path in paths:
                raise ValueError('Asset paths must be distinct')
            paths.append(path)
            actual = digest(path)
            if asset['sha256'] != actual:
                raise ValueError('SHA-256 mismatch: ' + asset['path'])
            hashes[asset['path']] = actual
        approval = config['approval']
        if approval['status'] != 'approved' or not approval['reviewer'].strip():
            raise ValueError('Human approval missing')
        expected = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
        if approval['bundle_sha256'] != expected:
            raise ValueError('Approval is stale or bound to another evidence bundle')
        if not approval['reviewed_at'].strip():
            raise ValueError('Approval timestamp missing')
    except (KeyError, TypeError, ValueError, AttributeError, OSError) as exc:
        errors.append(str(exc))
    return {'status': 'blocked' if errors else 'evidence-consistent',
            'errors': errors, 'blender_validation': 'not_run',
            'design_conformance': 'not_evaluated', 'assets_modified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding='utf-8'))
        result = validate(config, args.config.resolve().parent)
    except (OSError, ValueError) as exc:
        result = {'status': 'blocked', 'errors': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result['status'] == 'blocked' else 0


if __name__ == '__main__':
    raise SystemExit(main())
