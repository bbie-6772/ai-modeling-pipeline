"""Local evidence must be revision-bound and stay inside the run directory."""
import hashlib
import json
from .files import digest, local_file
from .profiles import PROFILE_PATH
from .specification import nonempty


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def run_digest(run):
    payload = {k: v for k, v in run.items() if k != 'approvals'}
    payload['profile_policy_sha256'] = digest(PROFILE_PATH)
    return canonical_hash(payload)


class Evidence:
    def __init__(self, run, root):
        self.root = root
        self.assets = {}
        resolved = set()
        for asset in run['assets']:
            path = local_file(root, asset['path'])
            if path in resolved:
                raise ValueError('Duplicate evidence file')
            resolved.add(path)
            nonempty(asset['role'])
            if digest(path) != asset['sha256']:
                raise ValueError('Evidence hash mismatch: ' + asset['path'])
            self.assets[asset['path']] = asset

    def require(self, paths, roles=None):
        if not isinstance(paths, list) or not paths or len(set(paths)) != len(paths):
            raise ValueError('Explicit unique evidence paths required')
        for path in paths:
            asset = self.assets[path]
            if roles and asset['role'] not in roles:
                raise ValueError('Wrong evidence role: ' + path)

    def read_json(self, path, role):
        self.require([path], {role})
        return json.loads(local_file(self.root, path).read_text(encoding='utf-8'))

    def bind(self, record, candidate):
        if record['candidate_sha256'] != self.assets[candidate]['sha256']:
            raise ValueError('Stale candidate evidence')
