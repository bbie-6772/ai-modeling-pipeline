"""Asset Specification and fixed process vocabulary."""
import math

STAGES = (
    'brief-reference', 'reference-decomposition', 'proxy-blockout',
    'geometry-reconstruction', 'visual-critique-revision', 'detail-procedural',
    'game-ready-optimization', 'in-engine-validation',
)
STATUSES = ('PASS', 'SUSPECT', 'FAIL', 'UNKNOWN', 'N/A')
CHECKS = {
    'F01': 'silhouette', 'F02': 'proportion', 'F03': 'primary-form-and-depth',
    'F04': 'functional-assembly', 'V01': 'multi-view-correspondence',
    'V02': 'surface-and-shading', 'V03': 'visual-hierarchy',
    'V04': 'material-readability', 'S01': 'topology-and-normals',
    'S02': 'scale-pivot-transforms', 'S03': 'uv-and-texture',
    'R01': 'rig-and-deformation', 'R02': 'repetition-and-symmetry',
    'R03': 'collision-and-lod', 'I01': 'engine-import', 'I02': 'runtime-budget',
}


def nonempty(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Expected nonempty text')
    return value


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('Expected finite nonnegative number')
    return value


def validate_spec(spec):
    for field in ('asset_id', 'project', 'design_revision', 'profile', 'target_engine', 'units'):
        nonempty(spec[field])
    scope = spec['scope']
    if not isinstance(scope, list) or not scope or len(set(scope)) != len(scope):
        raise ValueError('Explicit unique part scope required')
    for part in scope:
        nonempty(part)
    if not isinstance(spec['design_constraints'], dict) or not spec['design_constraints']:
        raise ValueError('Approved design constraints required')
    for key, value in spec['design_constraints'].items():
        nonempty(key)
        nonempty(value)
    for feature in ('deforming', 'repeated', 'collision', 'lod', 'textured'):
        if type(spec['features'][feature]) is not bool:
            raise ValueError('Feature must be explicit boolean: ' + feature)
    for budget in ('triangles', 'materials', 'texture_mib', 'frame_ms'):
        number(spec['budgets'][budget])
