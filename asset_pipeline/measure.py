"""Deterministic checks on the latest world snapshot: QA evidence, never a PASS.

Results are within/outside/unknown/reported. Only a proven 'outside' that
contradicts a PASS verdict becomes a finding (see contradictions()).
"""
import math
from .specification import UNIT_METERS, number
from .surface import geometry

AXES = {'x': 0, 'y': 1, 'z': 2}
# Orthographic reference image (u right, v down) -> world axes seen by that view.
VIEWS = {'front': (0, 2), 'side': (1, 2), 'top': (0, 1)}
NEIGHBOURS = [(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1)]


def finite(values, size):
    if not isinstance(values, list) or len(values) != size or any(
            type(v) not in (int, float) or not math.isfinite(v) for v in values):
        raise ValueError('Expected %d finite numbers' % size)
    return values


def mesh(parts, part):
    if part not in parts:
        raise ValueError('Measured part not in snapshot: ' + str(part))
    return geometry(parts[part])


def box(points):
    return [min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]


def unmatched(points, others, tolerance):
    """Points with no counterpart within tolerance; tolerance-sized cells make the 27-cell search exact."""
    cell = lambda p: tuple(math.floor(c / tolerance) for c in p)
    grid = {}
    for q in others:
        grid.setdefault(cell(q), []).append(q)
    return sum(not any(math.dist(p, q) <= tolerance for d in NEIGHBOURS
                       for q in grid.get(tuple(a + b for a, b in zip(cell(p), d)), ()))
               for p in points)


def dimensions(spec, parts):
    for part, rule in spec.get('dimensions', {}).items():
        low, high = box(mesh(parts, part)[0])
        size = [h - l for l, h in zip(low, high)]
        error = max(abs(s - e) for s, e in zip(size, finite(rule['size'], 3)))
        yield dict(check='F02', kind='dimensions', part=part, value=size, limit=rule['size'],
                   result='within' if error <= number(rule['tolerance']) else 'outside')


def symmetry(spec, parts):
    """Declared mirror/offset copies must match vertex-for-vertex: verification, not symmetry detection."""
    declared = spec.get('symmetry', {})
    # Profiles tie R02 to 'repeated'; without it R02 may be N/A and a violation would go unseen.
    if declared and not spec['features']['repeated']:
        raise ValueError('Declared symmetry requires the repeated feature')
    for part, rule in declared.items():
        if ('mirror' in rule) == ('offset' in rule):
            raise ValueError('Symmetry needs exactly one of mirror/offset: ' + str(part))
        tolerance = number(rule['tolerance'])
        if not tolerance:
            raise ValueError('Symmetry tolerance must be positive')
        source = mesh(parts, rule['of'])[0]
        if 'mirror' in rule:
            axis, plane = AXES[rule['mirror']], finite([rule['plane']], 1)[0]
            source = [[2 * plane - c if i == axis else c for i, c in enumerate(p)] for p in source]
        else:
            offset = finite(rule['offset'], 3)
            source = [[c + o for c, o in zip(p, offset)] for p in source]
        target = mesh(parts, part)[0]
        count = unmatched(source, target, tolerance) + unmatched(target, source, tolerance)
        yield dict(check='R02', kind='symmetry', part=part, value=count, limit=0,
                   result='outside' if count else 'within')


def anchors(spec, parts):
    for rule in spec.get('anchors', []):
        (a0, a1), (b0, b1) = box(mesh(parts, rule['part'])[0]), box(mesh(parts, rule['to'])[0])
        # The box gap never exceeds the true surface distance, so each relation is provable one way only.
        gap = math.hypot(*(max(0, a0[i] - b1[i], b0[i] - a1[i]) for i in range(3)))
        limit = number(rule['distance'])
        if rule['relation'] == 'contact':
            result = 'outside' if gap > limit else 'unknown'
        elif rule['relation'] == 'clearance':
            result = 'within' if gap >= limit else 'unknown'
        else:
            raise ValueError('Anchor relation must be contact or clearance')
        yield dict(check='F04', kind='anchor-' + rule['relation'], part=rule['part'], to=rule['to'],
                   value=gap, limit=limit, result=result)


def raster(shape, x0, y0, step):
    """Grid cells whose centre lies inside the polygon (even-odd rule)."""
    xs, ys = [p[0] for p in shape], [p[1] for p in shape]
    hits = set()
    for i in range(int((min(xs) - x0) / step), int((max(xs) - x0) / step) + 1):
        for j in range(int((min(ys) - y0) / step), int((max(ys) - y0) / step) + 1):
            x, y, inside = x0 + (i + .5) * step, y0 + (j + .5) * step, False
            for (ax, ay), (bx, by) in zip(shape, shape[1:] + shape[:1]):
                if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
                    inside = not inside
            if inside:
                hits.add((i, j))
    return hits


def silhouette(outline, parts, cells=128, meters_per_world_unit=1.0):
    """IoU of a part's orthographic projection and a registered outline.

    Placement comes only from the recorded origin and scale, never from fitting boxes.
    shortcut: 128-cell raster gives about one cell of edge error; raise cells for tighter checks.
    """
    u, v = VIEWS[outline['view']]
    scale, (u0, v0) = number(outline['meters_per_pixel']), finite(outline['origin_px'], 2)
    polygon = [((x - u0) * scale, (v0 - y) * scale) for x, y in (finite(p, 2) for p in outline['points'])]
    if len(polygon) < 3 or not scale:
        raise ValueError('Outline needs 3+ points and a positive scale')
    points, faces = mesh(parts, outline['part'])
    flat = [(p[u] * meters_per_world_unit, p[v] * meters_per_world_unit) for p in points]
    xs, ys = [p[0] for p in flat + polygon], [p[1] for p in flat + polygon]
    x0, y0 = min(xs), min(ys)
    step = max(max(xs) - x0, max(ys) - y0) / cells
    if not step:
        raise ValueError('Degenerate silhouette extent')
    model = set().union(*(raster([flat[i] for i in face], x0, y0, step) for face in faces))
    reference = raster(polygon, x0, y0, step)
    return len(model & reference) / (len(model | reference) or 1)


def measure(spec, parts, outlines=(), scene_units=None):
    """Compare declarations in spec units; outline coordinates always use meters.

    Legacy snapshots without units remain usable only when no measurement is requested.
    Raw snapshot geometry stays unchanged for revision and Surface Gate comparisons.
    """
    if not any(spec.get(key) for key in ('dimensions', 'symmetry', 'anchors')) and not outlines:
        return []
    if spec.get('units') not in UNIT_METERS:
        raise ValueError('Supported specification units: m, cm, mm')
    if not isinstance(scene_units, dict) or scene_units.get('system') not in ('METRIC', 'IMPERIAL'):
        raise ValueError('Measurements require explicit physical scene_units')
    scale = number(scene_units['scale_length'])
    if not scale:
        raise ValueError('scene_units.scale_length must be positive')
    factor = number(scale / UNIT_METERS[spec['units']])
    converted = {part: dict(record, vertices=[[c * factor for c in v] for v in record['vertices']])
                 for part, record in parts.items()}
    found = [*dimensions(spec, converted), *symmetry(spec, converted), *anchors(spec, converted)]
    for outline in outlines:
        found.append(dict(check='F01', kind='silhouette-' + str(outline['view']), part=outline['part'],
                          value=silhouette(outline, parts, meters_per_world_unit=scale),
                          limit=None, result='reported'))
    return found


def contradictions(measured, qa):
    """A proven violation cannot stand next to a PASS on the same QA check."""
    return [dict(check=m['check'], status='PASS', measurement=m['kind'], part=m['part'])
            for m in measured if m['result'] == 'outside' and qa[m['check']]['status'] == 'PASS']
