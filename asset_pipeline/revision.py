"""Revision & Approval Manager: evidence-backed repair loops and regression gates."""
from .surface import geometry_delta
from .evidence import run_digest
from .specification import CHECKS, STAGES, nonempty, number

RISK_ORDER = {'low': 0, 'medium': 1, 'high': 2}


def approval(run, evidence, kind):
    expected = run_digest(run)
    matches = [a for a in run['approvals'] if a['kind'] == kind]
    if len(matches) != 1:
        raise ValueError('Exactly one human approval required: ' + kind)
    record = matches[0]
    for field in ('reviewer', 'reviewed_at', 'statement'):
        nonempty(record[field])
    evidence.require([record['evidence']], {'human-review'})
    if record['status'] != 'approved' or record['bundle_sha256'] != expected:
        raise ValueError('Missing/stale human approval: ' + kind)


def risk(operation):
    value = RISK_ORDER[operation['risk']]
    if operation['changes_design'] or operation['destructive']:
        value = 2
    elif operation['rebuild']:
        value = max(value, 1)
    return tuple(RISK_ORDER)[value]


def authorize(run, evidence):
    approval(run, evidence, 'design-lock')
    operation = run['operation']
    if not isinstance(operation['parts'], list) or not operation['parts'] or not set(operation['parts']) <= set(run['specification']['scope']):
        raise ValueError('Operation exceeds approved part scope')
    for flag in ('changes_design', 'destructive', 'rebuild'):
        if type(operation[flag]) is not bool:
            raise ValueError('Operation flag must be boolean')
    if operation['changes_design']:
        raise ValueError('Design changes require a new specification/revision and design lock')
    level = risk(operation)
    # A repair inherits the risk of an unresolved issue in its affected parts.
    for issue in run['issues']:
        if issue['part'] in operation['parts'] and issue['status'] != 'verified':
            if RISK_ORDER[issue['severity']] > RISK_ORDER[level]:
                level = issue['severity']
    if level != 'low':
        approval(run, evidence, 'operation-' + level)
    if STAGES.index(run['stage']) >= 5:
        approval(run, evidence, 'core-shape')
    if run['stage'] == STAGES[-1]:
        approval(run, evidence, 'final')
    return level


def revisions(run, evidence):
    history = run['revisions']
    ids = set()
    previous = None
    deltas = []
    findings = []
    for event in history:
        nonempty(event['id'])
        if event['id'] in ids:
            raise ValueError('Duplicate geometry revision')
        ids.add(event['id'])
        before = evidence.read_json(event['before_snapshot'], 'geometry')
        after = evidence.read_json(event['after_snapshot'], 'geometry')
        for snapshot in (before, after):
            evidence.require([snapshot['source_asset']], {'baseline', 'candidate', 'revision', 'blockout'})
            evidence.bind({'candidate_sha256': snapshot['source_sha256']}, snapshot['source_asset'])
            if snapshot['coordinate_space'] != 'world' or set(snapshot['parts']) != set(run['specification']['scope']):
                raise ValueError('Revision snapshot scope/coordinate space mismatch')
        if previous and previous != event['before_snapshot']:
            raise ValueError('Broken geometry revision chain')
        if not previous and before['source_asset'] != run['baseline']:
            raise ValueError('History must start at frozen baseline')
        previous = event['after_snapshot']
        changed = {p: geometry_delta(before['parts'][p], after['parts'][p]) for p in before['parts']}
        actual = {p for p, delta in changed.items() if delta['changed']}
        if not isinstance(event['parts'], list) or set(event['parts']) != actual or not actual <= set(run['specification']['scope']):
            raise ValueError('Geometry change log does not match actual edited parts')
        nonempty(event['reason'])
        checks = event['regression']
        if set(checks) != set(CHECKS):
            raise ValueError('Regression requires all QA IDs')
        for check, record in checks.items():
            if record['status'] not in ('PASS', 'N/A', 'FAIL', 'SUSPECT', 'UNKNOWN'):
                raise ValueError('Invalid regression status: ' + check)
            if event is history[-1] and record['status'] != run['qa'][check]['status']:
                raise ValueError('Latest regression contradicts current QA: ' + check)
            engine_not_due = check.startswith('I') and STAGES.index(run['stage']) < 7
            if event is history[-1] and record['status'] not in ('PASS', 'N/A') and not engine_not_due:
                findings.append({'revision': event['id'], 'check': check, 'status': record['status']})
            # Current-candidate policy and verdicts cannot be bypassed with a generic PASS.
            if record['status'] == 'N/A' and run['qa'][check]['status'] != 'N/A':
                raise ValueError('Regression N/A contradicts current policy')
            evidence.bind(record, after['source_asset'])
            if record['status'] != 'UNKNOWN':
                evidence.require(record['evidence'], {'engine-report'} if check.startswith('I') else {'render', 'measurement', 'engine-report', 'geometry'})
        deltas.append({'id': event['id'], 'parts': changed})
    if history and after['source_asset'] != run['candidate']:
        raise ValueError('History must end at current candidate')
    if run['baseline'] != run['candidate'] and STAGES.index(run['stage']) >= 4 and not history:
        raise ValueError('Geometry history required after reconstruction')
    return deltas, findings


def issues(run, evidence):
    seen = set()
    findings = []
    for issue in run['issues']:
        nonempty(issue['id'])
        if issue['id'] in seen or issue['check'] not in CHECKS or issue['part'] not in run['specification']['scope']:
            raise ValueError('Invalid/duplicate issue identity')
        seen.add(issue['id'])
        if issue['severity'] not in RISK_ORDER or issue['status'] not in ('open', 'diagnosed', 'repaired', 'verified'):
            raise ValueError('Invalid issue severity/state')
        for field in ('observation', 'expected', 'region'):
            nonempty(issue[field])
        evidence.require(issue['evidence'], {'render', 'measurement', 'engine-report', 'geometry'})
        evidence.bind(issue, issue['candidate'])
        if issue['status'] != 'open':
            nonempty(issue['diagnosis'])
        if issue['status'] in ('repaired', 'verified'):
            nonempty(issue['repair'])
            if issue['repair_revision'] not in {r['id'] for r in run['revisions']}:
                raise ValueError('Repair must cite a geometry revision')
        if issue['status'] == 'verified':
            nonempty(issue['verification'])
            if issue['verified_candidate'] != run['candidate']:
                raise ValueError('Verification belongs to an old candidate')
            evidence.require(issue['verification_evidence'], {'render', 'measurement', 'engine-report', 'geometry'})
        else:
            findings.append({'issue': issue['id'], 'status': issue['status']})
    reported = {i['check'] for i in run['issues'] if i['status'] != 'verified'}
    for check, result in run['qa'].items():
        if result['status'] in ('FAIL', 'SUSPECT') and check not in reported:
            raise ValueError('FAIL/SUSPECT requires evidence-based issue: ' + check)
    return findings


def kpis(run):
    metrics = run['metrics']
    # Null is unknown, never silently converted to a measured zero.
    seconds = {}
    for field in ('analysis', 'modeling', 'render', 'human_review', 'waiting', 'revision'):
        value = metrics['seconds'][field]
        seconds[field] = None if value is None else number(value)
    tokens = metrics['tokens']
    if tokens is not None:
        if type(tokens) is not int:
            raise ValueError('Tokens must be measured integer or null')
        number(tokens)
        nonempty(metrics['token_source'])
    requests = metrics['human_revision_requests']
    if requests is not None and (type(requests) is not int or requests < 0):
        raise ValueError('Human revision requests must be integer or null')
    verdicts = [q['status'] for q in run['qa'].values() if q['status'] != 'N/A']
    measured = [s for s in verdicts if s in ('PASS', 'FAIL')]
    return {'seconds': seconds, 'total_seconds': None if None in seconds.values() else sum(seconds.values()),
            'tokens': tokens, 'human_revision_requests': requests,
            'geometry_revisions': len(run['revisions']),
            'qa_pass_rate': measured.count('PASS') / len(measured) if measured else None,
            'qa_coverage': len(measured) / len(verdicts) if verdicts else None,
            'unresolved_issues': sum(i['status'] != 'verified' for i in run['issues'])}
