"""Synthetic evidence fixture only. Never a human approval or production asset."""
import copy
import json
from asset_pipeline.surface import ASPECTS, surface_digest
from asset_pipeline.files import digest
from asset_pipeline.legacy import bundle_digest


def add_surface_fixture(config, root):
    def asset(name, role, content):
        path = root / name
        path.write_text(json.dumps(content) if not isinstance(content, str) else content, encoding='utf-8')
        config['assets'].append(dict(path=name, role=role, sha256=digest(path)))
        return name
    asset('blockout.txt', 'blockout', 'synthetic proxy')
    mesh = dict(vertices=[[0, 0, 0], [1, 0, 0], [0, 1, 0]], faces=[[0, 1, 2]])
    for phase, source in [('before', 'blockout.txt'), ('after', 'candidate.txt')]:
        geometry = copy.deepcopy(mesh)
        if phase == 'after':
            geometry['vertices'][0][2] = .2
        asset(phase + '.json', 'geometry', dict(source_asset=source, source_sha256=digest(root/source),
              coordinate_space='world', parts={'body': geometry}))
        asset(phase + '.png', 'render', 'synthetic render placeholder ' + phase)
    settings = dict(camera={'projection': 'ORTHO', 'matrix': list(range(16)), 'scale': 2},
                    renderer={'engine': 'synthetic'}, resolution=[640, 640])
    alignment = dict(reference='reference.txt', source_view='front', crop_pixels=[0, 0, 640, 640],
                     projection='orthographic', registration_method='fixed calibrated fixture', uncertainty='fixture only')
    for phase in ('before', 'after'):
        alignment[phase] = dict(settings, geometry_sha256=digest(root/(phase+'.json')))
    asset('alignment.json', 'alignment', alignment)
    asset('human.txt', 'human-review', 'SYNTHETIC TEST ONLY: approval fixture')
    config.update(stage='final', scope=['body'], surface_review=dict(
        blockout_is_proxy=True, before_snapshot='before.json', after_snapshot='after.json',
        parts=[dict(part='body', decision='edit', decision_reason='Move original face to match depth',
                    change_log='Original vertex 0 moved from z=0 to z=.2',
                    views=[dict(reference='reference.txt', before='before.png', after='after.png', alignment='alignment.json')],
                    checks={a: dict(status='corrected' if a == 'depth' else 'match',
                         surface_region='primary face 0', source_observation='synthetic target depth .2',
                         before_observation='synthetic depth 0', after_observation='synthetic depth .2',
                         evidence=['before.png', 'after.png']) for a in ASPECTS},
                    unresolved_differences=[], uncertainties=[])],
        approval=dict(status='approved', reviewer='synthetic-only', reviewed_at='2026-10-15',
                      statement='SYNTHETIC TEST ONLY', evidence='human.txt', bundle_sha256='')))
    resign(config)


def resign(config):
    hashes = {a['path']: a['sha256'] for a in config['assets']}
    config['surface_review']['approval']['bundle_sha256'] = surface_digest(config, hashes)
    config['approval']['bundle_sha256'] = bundle_digest(config, hashes)
