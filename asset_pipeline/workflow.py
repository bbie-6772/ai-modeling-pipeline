"""Stage orchestration and compatibility bridge to the existing Surface Gate."""
from pathlib import Path
from .surface import validate_surface, approve_surface, topology
from .measure import measure, contradictions
from .files import local_file
from .evidence import Evidence
from .profiles import policy
from .specification import STAGES, validate_spec, nonempty
from .qa import evaluate
from .revision import authorize, revisions, issues, kpis


def validate(run, root):
    result = {'status': 'blocked', 'errors': [], 'findings': [],
              'transition_allowed': False, 'execution_allowed': False,
              'detail_allowed': False, 'assets_modified': False,
              'model_validation': 'not_run', 'design_conformance': 'not_evaluated'}
    try:
        if run['schema_version'] != '1.0':
            raise ValueError('Unsupported schema version')
        spec = run['specification']
        validate_spec(spec)
        policy(spec)
        stage = STAGES.index(run['stage'])
        completed = run['completed_stages']
        if [r['stage'] for r in completed] != list(STAGES[:stage]):
            raise ValueError('Completed stages must be the exact ordered prefix')
        evidence = Evidence(run, Path(root))
        for field, role in (('baseline', 'baseline'), ('candidate', 'candidate'), ('design', 'design')):
            evidence.require([run[field]], {role})
        if run['baseline'] == run['candidate']:
            raise ValueError('Candidate must be separate from baseline')
        evidence.require(run['references'], {'reference'})
        for record in completed:
            nonempty(record['summary'])
            evidence.require(record['evidence'])
        result['risk'] = authorize(run, evidence)
        result['geometry_deltas'], regression_findings = revisions(run, evidence)
        measured_findings = []
        if run['revisions']:
            # Re-reads the snapshot revisions() checked: ~0.14 s per 4.6 MB, cheaper than coupling them.
            latest = evidence.read_json(run['revisions'][-1]['after_snapshot'], 'geometry')
            result['mesh_topology'] = {p: topology(r) for p, r in latest['parts'].items()}
            budget = spec['budgets']['triangles']
            # Early DCC-side warning only; I02 is still decided from the engine report.
            result['triangle_budget_ratio'] = (sum(t['triangles'] for t in result['mesh_topology'].values())
                                               / budget if budget else None)
            outlines = [evidence.read_json(path, 'reference-outline') for path in run.get('outlines', [])]
            result['measurements'] = measure(spec, latest['parts'], outlines)
            measured_findings = contradictions(result['measurements'], run['qa'])
        result['findings'] = (evaluate(run, evidence) + issues(run, evidence) + regression_findings
                              + measured_findings)
        result['kpis'] = kpis(run)
        if stage >= 5:
            surface = dict(project=spec['project'], design_revision=spec['design_revision'],
                           scope=spec['scope'], assets=run['assets'], surface_review=run['surface_review'])
            hashes = {a['path']: a['sha256'] for a in run['assets']}
            if surface['surface_review']['after_snapshot'] != run['revisions'][-1]['after_snapshot']:
                raise ValueError('Surface Gate must inspect latest geometry revision')
            result['surface_deltas'] = validate_surface(surface, Path(root), hashes, local_file)
            approve_surface(surface, hashes)
        # Repair can execute during critique without pretending the stage has passed.
        result['execution_allowed'] = not result['findings'] or stage == 4
        result['transition_allowed'] = not result['findings']
        result['detail_allowed'] = stage >= 5 and not result['findings']
        result['status'] = 'evidence-consistent' if not result['findings'] else 'needs-revision'
    except (KeyError, TypeError, ValueError, AttributeError, OSError, IndexError) as exc:
        result['errors'].append(str(exc))
    return result
