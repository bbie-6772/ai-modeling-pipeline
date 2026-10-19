"""Visual QA Engine validates evidence reports; it does not see or score pixels."""
from .profiles import policy
from .specification import CHECKS, STATUSES, STAGES, nonempty, number

# Required when entering a stage, after the preceding work can be completed.
REQUIRED_STAGE = dict.fromkeys(CHECKS, 'visual-critique-revision')
REQUIRED_STAGE.update({
    'V04': 'game-ready-optimization',
    'S03': 'in-engine-validation', 'R01': 'in-engine-validation',
    'R03': 'in-engine-validation', 'I01': 'in-engine-validation',
    'I02': 'in-engine-validation',
})


def needs_review(check, status, stage):
    if status in ('PASS', 'N/A'):
        return False
    # A known problem is never deferred; only not-yet-performed work may wait.
    return status != 'UNKNOWN' or stage >= STAGES.index(REQUIRED_STAGE[check])


def evaluate(run, evidence):
    spec = run['specification']
    required, exceptions = policy(spec)
    records = run['qa']
    if set(records) != set(CHECKS):
        raise ValueError('QA must enumerate all 16 requested IDs')
    active = STAGES.index(run['stage'])
    findings = []
    for check, record in records.items():
        status = record['status']
        if status not in STATUSES:
            raise ValueError('Invalid QA verdict: ' + check)
        nonempty(record['observation'])
        if status == 'N/A':
            if check in required or record['reason'] != exceptions[check]:
                raise ValueError('Profile does not permit this N/A: ' + check)
        elif status != 'UNKNOWN':
            evidence.bind(record, run['candidate'])
            evidence.require(record['evidence'], {'render', 'measurement', 'engine-report', 'geometry'})
            nonempty(record['method'])
            # R01 and R03 must cover each enabled subfeature, not just one easy check.
            if status == 'PASS' and check == 'R03':
                expected = {f for f in ('collision', 'lod') if spec['features'][f]}
                if not expected <= set(record['coverage']):
                    raise ValueError('Collision/LOD coverage missing')
            if check in ('I01', 'I02'):
                evidence.require(record['evidence'], {'engine-report'})
        if needs_review(check, status, active):
            findings.append({'check': check, 'status': status})
    if active == 7:
        engine = evidence.read_json(run['engine_report'], 'engine-report')
        if engine.get('runtime_budget_verified') is False:
            raise ValueError('Headless smoke does not verify target runtime budgets')
        evidence.bind(engine, run['candidate'])
        if engine['engine'] != spec['target_engine']:
            raise ValueError('Engine report target mismatch')
        nonempty(engine['version'])
        nonempty(engine['test_scene'])
        if engine['import_ok'] is not True or engine['runtime_ok'] is not True:
            raise ValueError('In-engine validation failed')
        for key, limit in spec['budgets'].items():
            if number(engine['measurements'][key]) > limit:
                raise ValueError('Engine budget exceeded: ' + key)
        for check in ('I01', 'I02'):
            if run['engine_report'] not in records[check]['evidence']:
                raise ValueError('Engine QA must cite the checked engine report')
    return findings
