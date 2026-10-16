"""Offline evidence gate. Never opens Blender or modifies input assets."""
import argparse
import hashlib
import json
from pathlib import Path
from .surface import validate_surface, approve_surface
from .files import digest, local_file


def bundle_digest(config, hashes):
    """Bind evidence to its project and approved design revision."""
    payload = {key: value for key, value in config.items() if key != 'approval'}
    payload['asset_hashes'] = hashes
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def validate(config, root):
    errors = []
    deltas = {}
    try:
        for key in ('project', 'design_revision'):
            if not isinstance(config[key], str) or not config[key].strip():
                raise ValueError(key + ' must be a nonempty string')
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
        if config['stage'] not in ('detail-entry', 'final'):
            raise ValueError('Expected stage detail-entry or final')
        deltas = validate_surface(config, root, hashes, local_file)
        approve_surface(config, hashes)
        if config['stage'] == 'final':
            approval = config['approval']
            if approval['status'] != 'approved' or not approval['reviewer'].strip():
                raise ValueError('Human approval missing')
            expected = bundle_digest(config, hashes)
            if approval['bundle_sha256'] != expected:
                raise ValueError('Approval is stale or bound to another evidence bundle')
            if not approval['reviewed_at'].strip():
                raise ValueError('Approval timestamp missing')
    except (KeyError, TypeError, ValueError, AttributeError, OSError, IndexError) as exc:
        errors.append(str(exc))
    return {'status': 'blocked' if errors else 'evidence-consistent',
            'errors': errors, 'model_validation': 'not_run',
            'design_conformance': 'not_evaluated', 'assets_modified': False,
            'detail_allowed': not errors,
            'geometry_deltas': deltas}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding='utf-8'))
        result = validate(config, args.config.resolve().parent)
    except (OSError, ValueError) as exc:
        result = {'status': 'blocked', 'errors': [str(exc)], 'detail_allowed': False,
                  'assets_modified': False, 'geometry_deltas': {}}
    print(json.dumps(result, ensure_ascii=False))
    return 2 if result['status'] == 'blocked' else 0


if __name__ == '__main__':
    raise SystemExit(main())
