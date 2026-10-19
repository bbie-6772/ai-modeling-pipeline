"""Declared shape constraints with provenance; never an image interpreter or approval."""
import argparse
import json
from pathlib import Path

from .drawing import layout
from .files import digest, local_file
from .measure import measure
from .specification import UNIT_METERS, nonempty, number


def verify_drawings(path, candidate_sha256):
    path = Path(path).resolve()
    manifest = json.loads(path.read_text(encoding='utf-8'))
    if manifest['kind'] != 'orthographic-drawings-v1' or manifest['source_sha256'] != candidate_sha256:
        raise ValueError('Drawing manifest belongs to another candidate')
    required = {'snapshot.json', 'parts.json', 'render-config.json', 'sheet.svg'}
    required.update(name+extension for name in ('front','side','top') for extension in ('.png','.svg'))
    if not required <= set(manifest['files']):
        raise ValueError('Drawing bundle is incomplete')
    for name, sha in manifest['files'].items():
        if Path(name).name != name or digest(local_file(path.parent, name)) != sha:
            raise ValueError('Drawing output hash mismatch: '+name)
    snapshot = json.loads((path.parent/'snapshot.json').read_text(encoding='utf-8'))
    if snapshot['source_sha256'] != candidate_sha256:
        raise ValueError('Drawing snapshot belongs to another candidate')
    settings = manifest['settings']
    actual = layout(snapshot, settings['meters_per_pixel'], settings['resolution'], settings['center_m'], settings['units'])
    if actual != settings or json.loads((path.parent/'render-config.json').read_text()) != settings:
        raise ValueError('Drawing camera or scale metadata contradicts geometry')
    mapping = json.loads((path.parent/'parts.json').read_text(encoding='utf-8'))
    if mapping != {part: record['objects'] for part,record in snapshot['parts'].items()}:
        raise ValueError('Drawing part mapping mismatch')
    return snapshot, manifest


def evaluate(contract, snapshot, root):
    if contract['schema_version'] != 'shape-contract-v1' or contract['units'] not in UNIT_METERS:
        raise ValueError('Unsupported shape contract version or units')
    for key in ('asset_id','design_revision'):
        nonempty(contract[key])
    parts, references = contract['parts'], contract['references']
    if not parts or set(parts) != set(snapshot['parts']):
        raise ValueError('Shape contract must cover exactly the snapshot parts')
    for ref in references.values():
        if ref['view'] not in ('front','side','top','oblique','text'):
            raise ValueError('Explicit reference view required')
        if digest(local_file(Path(root), ref['path'])) != ref['sha256']:
            raise ValueError('Shape reference hash mismatch')
    def provenance(rule):
        if rule['basis'] not in ('observed','inferred','unknown'):
            raise ValueError('Constraint basis must be observed, inferred or unknown')
        nonempty(rule['description'])
        ids = rule['reference_ids']
        if not isinstance(ids,list) or not ids or not set(ids) <= set(references):
            raise ValueError('Constraint must cite registered references')
        return rule['basis'] == 'observed'
    findings, planned = [], dict(units=contract['units'], features={'repeated':True}, dimensions={}, symmetry={}, anchors=[])
    for part, record in parts.items():
        if record['objects'] != snapshot['parts'][part]['objects'] or not record['observations']:
            raise ValueError('Shape part mapping or observations missing: '+part)
        for observation in record['observations']:
            if not provenance(observation):
                findings.append(dict(check='F03',part=part,status='UNKNOWN',reason=observation['description']))
    for category,check in (('dimensions','F02'),('symmetry','R02'),('anchors','F04')):
        rules = contract.get(category, [] if category=='anchors' else {})
        entries = ((r['part'],r) for r in rules) if category=='anchors' else rules.items()
        for part, rule in entries:
            if part not in parts:
                raise ValueError('Constraint part outside contract scope')
            if not provenance(rule):
                findings.append(dict(check=check,part=part,status='UNKNOWN',reason=rule['description']))
            elif category=='anchors':
                planned[category].append(rule)
            else:
                planned[category][part] = rule
    # No declaration is never interpreted as shape conformance.
    measured = measure(planned, snapshot['parts'], scene_units=snapshot.get('scene_units'))
    for outline in contract.get('outlines', []):
        if outline['part'] not in parts:
            raise ValueError('Outline outside contract scope')
        if not provenance(outline):
            findings.append(dict(check='F01',part=outline['part'],status='UNKNOWN',reason=outline['description']))
            continue
        threshold = number(outline['minimum_iou'])
        if threshold > 1:
            raise ValueError('IoU threshold must be between zero and one')
        result = measure(dict(units=contract['units']), snapshot['parts'], [outline], snapshot.get('scene_units'))[0]
        result.update(limit=threshold, result='within' if result['value'] >= threshold else 'outside')
        measured.append(result)
    for result in measured:
        if result['result'] in ('outside','unknown'):
            findings.append(dict(check=result['check'],part=result['part'],
                                 status='FAIL' if result['result']=='outside' else 'UNKNOWN', reason=result['kind']))
    for uncertainty in contract['uncertainties']:
        if uncertainty['part'] not in parts or type(uncertainty['blocking']) is not bool:
            raise ValueError('Explicit uncertainty part and blocking boolean required')
        nonempty(uncertainty['description'])
        if uncertainty['blocking']:
            findings.append(dict(check='F03',part=uncertainty['part'],status='UNKNOWN',reason=uncertainty['description']))
    if not measured:
        findings.append(dict(check='F02',status='UNKNOWN',reason='No observed measurable constraints'))
    return dict(status='needs-review' if findings else 'within-declared-constraints',
                measurements=measured, findings=findings, uncertainties=contract['uncertainties'],
                approval='not_granted', scope='declared constraints only')


def validate_run(run, evidence):
    contract = evidence.read_json(run['shape_contract'], 'shape-contract')
    spec = run['specification']
    if contract['asset_id'] != spec['asset_id'] or contract['design_revision'] != spec['design_revision']:
        raise ValueError('Shape contract design revision mismatch')
    for ref in contract['references'].values():
        evidence.require([ref['path']], {'reference'})
    snapshot, manifest = verify_drawings(local_file(evidence.root,run['drawing_manifest']),
                                         evidence.assets[run['candidate']]['sha256'])
    evidence.require([run['drawing_manifest']], {'drawing-manifest'})
    latest = evidence.read_json(run['revisions'][-1]['after_snapshot'],'geometry')
    if latest != snapshot or set(contract['parts']) != set(spec['scope']):
        raise ValueError('Drawing snapshot must equal the latest revision snapshot')
    # Register every bundle file in the run so bundle approval cannot omit its hashes.
    folder = local_file(evidence.root,run['drawing_manifest']).parent
    for name in manifest['files']:
        evidence.require([(folder/name).relative_to(evidence.root.resolve()).as_posix()])
    return evaluate(contract,snapshot,evidence.root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('contract',type=Path)
    parser.add_argument('--candidate',required=True,type=Path)
    parser.add_argument('--drawing-manifest',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args()
    try:
        contract = json.loads(args.contract.read_text(encoding='utf-8'))
        snapshot,_ = verify_drawings(args.drawing_manifest,digest(args.candidate))
        report = evaluate(contract,snapshot,args.contract.resolve().parent)
        with args.output.open('x',encoding='utf-8') as stream:
            json.dump(report,stream,indent=2,ensure_ascii=False,allow_nan=False)
        print(json.dumps(report,ensure_ascii=False,allow_nan=False))
        return 0 if not report['findings'] else 2
    except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:
        print(json.dumps({'status':'blocked','errors':[str(exc)]},ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
