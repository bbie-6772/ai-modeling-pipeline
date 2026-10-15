"""Modeling Executor boundary for trusted local adapters, never an AI modeler.

The adapter gets only a new candidate path and approved part IDs. This is an
in-process contract, not an OS sandbox. Do not use an untrusted adapter.
"""
import copy
import json
from pathlib import Path
from pipeline import digest, local_file
from .workflow import validate


def execute(run, root, output, adapter):
    # Validate the same immutable request that is passed to the adapter.
    request = copy.deepcopy(run)
    root = Path(root).resolve()
    gate = validate(request, root)
    if not gate['execution_allowed']:
        raise ValueError('Execution blocked: ' + str(gate['errors'] or gate['findings']))
    target = Path(output)
    if target.is_absolute():
        raise ValueError('Output must be relative to the run directory')
    target = (root / target).resolve()
    receipt_path = target.with_name(target.name + '.receipt.json')
    if not target.is_relative_to(root) or target.exists() or receipt_path.exists():
        raise ValueError('Output must be a new candidate inside the run directory')
    frozen = {a['path']: digest(local_file(root, a['path'])) for a in request['assets']}
    source = local_file(root, request['candidate'])
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create preserves previous candidates even when requests collide.
    with target.open('xb') as stream:
        stream.write(source.read_bytes())
    error = None
    try:
        adapter(target, tuple(request['operation']['parts']))
    except Exception as exc:
        error = str(exc)
    changed = [p for p, sha in frozen.items() if digest(local_file(root, p)) != sha]
    if changed:
        raise ValueError('Adapter modified protected input files: ' + ', '.join(changed))
    if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(root):
        raise ValueError('Adapter output is not a local candidate file')
    after = digest(target)
    receipt = {'status': 'adapter-failed' if error is not None else 'candidate-pending-qa',
            'error': error, 'candidate': target.relative_to(root).as_posix(),
            'before_sha256': frozen[request['candidate']], 'after_sha256': after,
            'parts': request['operation']['parts'], 'stage': request['stage'],
            'adopted': False, 'requires_geometry_snapshot': True,
            'requires_regression': True}
    with receipt_path.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
    return receipt
