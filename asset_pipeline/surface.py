"""Fail-closed surface evidence checks; does not infer shape from images."""
import hashlib
import json
import math

ASPECTS = ('orientation', 'curvature', 'depth', 'edges', 'silhouette', 'junction_anchors')


def text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Expected nonempty evidence text')
    return value


def surface_digest(config, hashes):
    review = dict(config['surface_review'])
    review['approval'] = {k: v for k, v in review['approval'].items() if k != 'bundle_sha256'}
    payload = dict(project=config['project'], design_revision=config['design_revision'],
                   scope=config['scope'], assets=config['assets'], asset_hashes=hashes, surface_review=review)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()


def human_approval(approval, expected, registered):
    if approval['status'] != 'approved':
        raise ValueError('Core shape human approval missing')
    for field in ('reviewer', 'reviewed_at', 'statement'):
        text(approval[field])
    registered(approval['evidence'], 'human-review')
    if approval['bundle_sha256'] != expected:
        raise ValueError('Core shape approval is stale')


def geometry(record):
    vertices, faces = record['vertices'], record['faces']
    if not isinstance(vertices, list) or not vertices or not isinstance(faces, list) or not faces:
        raise ValueError('Empty mesh snapshot')
    for vertex in vertices:
        if not isinstance(vertex, list) or len(vertex) != 3 or any(
                type(v) not in (int, float) or not math.isfinite(v) for v in vertex):
            raise ValueError('Invalid world-space vertex')
    for face in faces:
        if not isinstance(face, list) or len(face) < 3 or any(
                type(i) is not int or not 0 <= i < len(vertices) for i in face):
            raise ValueError('Invalid mesh face')
    return vertices, faces


def geometry_delta(before, after):
    bv, bf = geometry(before)
    av, af = geometry(after)
    # Ignore vertex reindexing/cyclic starts, but preserve face winding.
    def surfaces(vs, fs):
        result = set()
        for face in fs:
            points = tuple(tuple(vs[i]) for i in face)
            result.add(min(points[i:] + points[:i] for i in range(len(points))))
        return result
    old, new = set(map(tuple, bv)), set(map(tuple, av))
    removed_vertices = len(old - new)
    removed_faces = len(surfaces(bv, bf) - surfaces(av, af))
    moved = old ^ new
    return dict(before_vertices=len(bv), after_vertices=len(av), before_faces=len(bf),
                after_faces=len(af), removed_or_moved_vertices=removed_vertices,
                replaced_faces=removed_faces,
                changed=(old != new or surfaces(bv, bf) != surfaces(av, af)),
                existing_surface_changed=bool(removed_vertices or removed_faces),
                # Where to point review cameras: box of positions that appeared or disappeared.
                changed_bounds=[[min(p[i] for p in moved) for i in range(3)],
                                [max(p[i] for p in moved) for i in range(3)]] if moved else None)


def topology(record):
    """S01 measurement counts, never a verdict: open shells or touching objects can be intended."""
    vertices, faces = geometry(record)
    edges, degenerate = {}, 0
    for face in faces:
        if len(set(face)) != len(face):
            raise ValueError('Invalid mesh face')  # a repeated index would fake a matched edge pair
        points = [vertices[i] for i in face]
        # Newell vector = twice the polygon area vector; robust for planar n-gons.
        normal = [sum(p[(k + 1) % 3] * q[(k + 2) % 3] - p[(k + 2) % 3] * q[(k + 1) % 3]
                      for p, q in zip(points, points[1:] + points[:1])) for k in range(3)]
        # shortcut: absolute 1e-12 unit^2 tolerance, make it scale-relative if sub-mm assets appear.
        degenerate += math.hypot(*normal) <= 1e-12
        for a, b in zip(face, face[1:] + face[:1]):
            edges.setdefault(frozenset((a, b)), []).append((a, b))
    uses = list(edges.values())
    return dict(triangles=sum(len(f) - 2 for f in faces),
                boundary_edges=sum(len(u) == 1 for u in uses),
                nonmanifold_edges=sum(len(u) > 2 for u in uses),
                inconsistent_winding_edges=sum(len(u) == 2 and u[0] == u[1] for u in uses),
                degenerate_faces=degenerate,
                coincident_vertices=len(vertices) - len(set(map(tuple, vertices))))


def validate_surface(config, root, hashes, local_file):
    assets = {a['path']: a for a in config['assets']}

    def registered(path, role):
        if path not in assets or assets[path]['role'] != role:
            raise ValueError('Unregistered or wrong-role evidence: ' + str(path))
        return local_file(root, path)

    review = config['surface_review']
    if review['blockout_is_proxy'] is not True:
        raise ValueError('Blockout must remain a replaceable proxy')
    scope = config['scope']
    if not isinstance(scope, list) or not scope or any(not isinstance(p, str) or not p.strip() for p in scope) or len(set(scope)) != len(scope):
        raise ValueError('Expected unique, explicit part scope')
    parts = review['parts']
    if not isinstance(parts, list) or len(parts) != len(scope) or {p['part'] for p in parts} != set(scope):
        raise ValueError('Every scoped part must be re-evaluated exactly once')
    snapshots = []
    for phase, role in (('before', 'blockout'), ('after', 'candidate')):
        snapshot = json.loads(registered(review[phase + '_snapshot'], 'geometry').read_text(encoding='utf-8'))
        registered(snapshot['source_asset'], role)
        if snapshot['source_sha256'] != hashes[snapshot['source_asset']]:
            raise ValueError('Snapshot belongs to another asset revision')
        if snapshot['coordinate_space'] != 'world' or set(snapshot['parts']) != set(scope):
            raise ValueError('Snapshot scope/coordinate system mismatch')
        snapshots.append(snapshot)
    if snapshots[0]['source_asset'] == snapshots[1]['source_asset']:
        raise ValueError('Blockout and candidate must be separate files')
    deltas = {}
    for part in parts:
        name = part['part']
        delta = geometry_delta(snapshots[0]['parts'][name], snapshots[1]['parts'][name])
        deltas[name] = delta
        decision = part['decision']
        if decision not in ('edit', 'rebuild', 'retain'):
            raise ValueError('Choose edit, rebuild, or retain: ' + name)
        text(part['decision_reason'])
        text(part['change_log'])
        if decision == 'retain' and delta['changed']:
            raise ValueError('Retain decision contradicts geometry: ' + name)
        if decision != 'retain' and not delta['existing_surface_changed']:
            raise ValueError('No existing surface changed; added detail is insufficient: ' + name)
        views = part['views']
        if not isinstance(views, list) or not views:
            raise ValueError('Aligned before/after renders missing: ' + name)
        render_paths = set()
        for view in views:
            registered(view['reference'], 'reference')
            registered(view['before'], 'render')
            registered(view['after'], 'render')
            if view['before'] == view['after']:
                raise ValueError('Before/after renders must be separate')
            alignment = json.loads(registered(view['alignment'], 'alignment').read_text(encoding='utf-8'))
            if alignment['reference'] != view['reference']:
                raise ValueError('Alignment reference mismatch')
            for field in ('source_view', 'crop_pixels', 'projection', 'registration_method', 'uncertainty'):
                if not alignment[field]:
                    raise ValueError('Incomplete alignment: ' + field)
            for field in ('camera', 'renderer', 'resolution'):
                if not alignment['before'][field] or alignment['before'][field] != alignment['after'][field]:
                    raise ValueError('Before/after comparison settings differ: ' + field)
            if alignment['before']['geometry_sha256'] != hashes[review['before_snapshot']] or alignment['after']['geometry_sha256'] != hashes[review['after_snapshot']]:
                raise ValueError('Render alignment references stale geometry')
            render_paths.update((view['before'], view['after']))
        checks = part['checks']
        if set(checks) != set(ASPECTS):
            raise ValueError('All six surface aspects are required: ' + name)
        corrected = False
        for aspect, check in checks.items():
            if check['status'] not in ('match', 'corrected'):
                raise ValueError('Unresolved surface mismatch: ' + name + '/' + aspect)
            for field in ('source_observation', 'before_observation', 'after_observation', 'surface_region'):
                text(check[field])
            if not check['evidence'] or not set(check['evidence']) <= render_paths:
                raise ValueError('Surface check must cite registered comparison renders')
            if check['status'] == 'corrected':
                corrected = True
                if not delta['existing_surface_changed']:
                    raise ValueError('Correction claimed without surface geometry change')
        if decision != 'retain' and not corrected:
            raise ValueError('Surface edit needs a corrected aspect')
        # Explicitly enumerate both differences and uncertainty, including empty lists.
        for field in ('unresolved_differences', 'uncertainties'):
            if not isinstance(part[field], list):
                raise ValueError('Expected explicit issue list: ' + field)
            for issue in part[field]:
                text(issue['description'])
                text(issue['reason'])
                if issue['disposition'] != 'accepted-nonblocking':
                    raise ValueError('Unresolved blocking issue: ' + name)
    return deltas


def approve_surface(config, hashes):
    def registered(path, role):
        if not any(a['path'] == path and a['role'] == role for a in config['assets']):
            raise ValueError('Unregistered human approval evidence')
    human_approval(config['surface_review']['approval'], surface_digest(config, hashes), registered)
