"""Generate three orthographic drawings from one saved Blender model.

python -m asset_pipeline.drawing model.blend --blender BLENDER --parts parts.json
    --output runs/drawing-01 --meters-per-pixel .002 --units mm
"""
import argparse
import base64
from html import escape
import json
import math
from pathlib import Path
import subprocess

from .files import digest
from .measure import finite
from .specification import UNIT_METERS, number
from .surface import geometry

VIEWS = {'front': (0, 2, (0, -1, 0)),
         'side': (1, 2, (1, 0, 0)),
         'top': (0, 1, (0, 0, 1))}
COLORS = ('#9ec5dc', '#e6bb8b', '#9fc5ac', '#c1afd4', '#dfb0bc', '#c5ca8b')


def layout(snapshot, meters_per_pixel, resolution, center, units):
    """Fixed world registration. No view-dependent fitting or perspective."""
    number(meters_per_pixel)
    if not meters_per_pixel or type(resolution) is not int or not 128 <= resolution <= 2048:
        raise ValueError('Positive meters-per-pixel and resolution 128..2048 required')
    finite(center, 3)
    if units not in UNIT_METERS:
        raise ValueError('Drawing units must be m, cm or mm')
    scene_units = snapshot['scene_units']
    if scene_units['system'] not in ('METRIC', 'IMPERIAL'):
        raise ValueError('Drawing requires physical scene units')
    scale = number(scene_units['scale_length'])
    if not scale:
        raise ValueError('Scene scale must be positive')
    parts = {}
    for name, record in sorted(snapshot['parts'].items()):
        vertices, _ = geometry(record)
        parts[name] = [[c * scale for c in v] for v in vertices]
    if not parts:
        raise ValueError('Drawing requires mesh parts')
    points = [v for vertices in parts.values() for v in vertices]
    low = [min(v[i] for v in points) for i in range(3)]
    high = [max(v[i] for v in points) for i in range(3)]
    half = resolution * meters_per_pixel / 2
    # Reserve 10 pixels around the actual geometry inside each render.
    if any(max(abs(low[i]-center[i]), abs(high[i]-center[i])) > half - 10*meters_per_pixel
           for i in range(3)):
        raise ValueError('Geometry exceeds fixed framing; explicitly adjust center or meters-per-pixel')
    distance = max(1.0, max(math.dist(p, center) for p in points) * 3)
    views = {}
    for name, (u, v, direction) in VIEWS.items():
        project = lambda p: [resolution/2 + (p[u]-center[u])/meters_per_pixel,
                             resolution/2 - (p[v]-center[v])/meters_per_pixel]
        views[name] = dict(axes=['XYZ'[u], 'XYZ'[v]], bounds_px=[project(low), project(high)],
                           dimensions=[(high[i]-low[i])/UNIT_METERS[units] for i in (u, v)],
                           origin_px=project([0, 0, 0]),
                           camera_location=[center[i]+direction[i]*distance for i in range(3)],
                           camera_target=center, projection='ORTHO',
                           ortho_scale_m=resolution*meters_per_pixel,
                           labels=[dict(part=part, point_px=project(
                               [(min(p[i] for p in vertices)+max(p[i] for p in vertices))/2
                                for i in range(3)])) for part, vertices in parts.items()])
    return dict(resolution=resolution, meters_per_pixel=meters_per_pixel, center_m=center,
                units=units, bounds_m=[low, high], distance_m=distance, views=views)


def panel(name, view, settings, png):
    """Standalone SVG panel with embedded raster and measured bounding dimensions."""
    size = settings['resolution']
    width, height = size+200, size+200
    x, y = 100, 65
    (left, bottom), (right, top) = view['bounds_px']
    ox, oy = view['origin_px']
    unit = settings['units']
    data = base64.b64encode(png).decode('ascii')
    text = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="white"/>',
            '<g font-family="Arial, sans-serif" font-size="13" fill="#243746">',
            f'<text x="20" y="25" font-size="19">{name.upper()} / ORTHOGRAPHIC</text>',
            f'<text x="20" y="45">{settings["meters_per_pixel"]:g} m/pixel · dimensions: {unit}</text>',
            f'<image x="{x}" y="{y}" width="{size}" height="{size}" href="data:image/png;base64,{data}"/>']
    line = lambda a,b,c,d,color='#627481',dash='': (
        f'<line x1="{a:.3f}" y1="{b:.3f}" x2="{c:.3f}" y2="{d:.3f}" stroke="{color}" {dash}/>')
    if 0 <= ox <= size:
        text.append(line(x+ox,y,x+ox,y+size,'#c5d1d8','stroke-dasharray="5 5"'))
    if 0 <= oy <= size:
        text.append(line(x,y+oy,x+size,y+oy,'#c5d1d8','stroke-dasharray="5 5"'))
    # Dimension extension lines start at the projected AABB, not a guessed feature.
    dy, dx = y+size+25, x-35
    for px in (left, right):
        text.append(line(x+px,y+bottom,x+px,dy+5))
        text.append(line(x+px-4,dy-4,x+px+4,dy+4))
    text.append(line(x+left,dy,x+right,dy))
    for py in (top, bottom):
        text.append(line(dx-5,y+py,x+left,y+py))
        text.append(line(dx-4,y+py-4,dx+4,y+py+4))
    text.append(line(dx,y+top,dx,y+bottom))
    text.append(f'<text x="{x+(left+right)/2}" y="{dy+19}" text-anchor="middle">'
                f'{view["axes"][0]} {view["dimensions"][0]:.6g} {unit}</text>')
    text.append(f'<text x="{dx-9}" y="{y+(top+bottom)/2}" text-anchor="middle" '
                f'transform="rotate(-90 {dx-9} {y+(top+bottom)/2})">'
                f'{view["axes"][1]} {view["dimensions"][1]:.6g} {unit}</text>')
    for i, label in enumerate(view['labels'], 1):
        px, py = label['point_px']
        text.append(f'<text x="{x+px}" y="{y+py}" text-anchor="middle" '
                    f'stroke="white" stroke-width="3" paint-order="stroke">{i}</text>')
    legend = ' | '.join(f'{i}: {label["part"]}' for i,label in enumerate(view['labels'],1))
    text.append(f'<text x="20" y="{height-38}">{escape(legend)}</text>')
    text.append(f'<text x="20" y="{height-18}">Measured model bounds; hidden lines omitted; not design approval.</text>')
    text.append('</g></svg>')
    return '\n'.join(text)


def generate(source, blender, parts_path, output, *, meters_per_pixel, resolution=640,
             center=None, units='mm', timeout=180, asset_path=None):
    source, parts_path, output = Path(source).resolve(), Path(parts_path).resolve(), Path(output).resolve()
    if source.suffix.lower() != '.blend' or not source.is_file():
        raise ValueError('Saved .blend source required')
    frozen = {p: digest(p) for p in (source, parts_path)}
    mapping = json.loads(parts_path.read_text(encoding='utf-8'))
    output.mkdir(parents=True, exist_ok=False)
    (output/'parts.json').write_text(json.dumps(mapping, ensure_ascii=False), encoding='utf-8')
    adapters = Path(__file__).parent/'adapters'/'blender'
    def run(args):
        result = subprocess.run([str(blender), '--background', '--factory-startup', '--disable-autoexec',
                                 '--python-exit-code', '1', *args], capture_output=True, text=True, timeout=timeout)
        if result.returncode:
            raise ValueError('Blender drawing failed: '+result.stdout[-4000:]+result.stderr[-4000:])
    try:
        run([str(source), '--python', str(adapters/'snapshot.py'), '--', '--parts', str(output/'parts.json'),
             '--output', str(output/'snapshot.json'), '--asset-path', asset_path or source.name])
        snapshot = json.loads((output/'snapshot.json').read_text(encoding='utf-8'))
        if snapshot['source_sha256'] != frozen[source]:
            raise ValueError('Snapshot source hash mismatch')
        settings = layout(snapshot, meters_per_pixel, resolution, [0,0,0] if center is None else center, units)
        (output/'render-config.json').write_text(json.dumps(settings, allow_nan=False), encoding='utf-8')
        run(['--python', str(adapters/'drawing.py'), '--', str(output)])
        for name, view in settings['views'].items():
            svg = panel(name, view, settings, (output/(name+'.png')).read_bytes())
            (output/(name+'.svg')).write_text(svg, encoding='utf-8')
        # A self-contained three-panel review sheet; all panels keep their pixel scale.
        w = resolution+200
        sheet = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w*3}" height="{w}">']
        for i, name in enumerate(VIEWS):
            svg = (output/(name+'.svg')).read_text(encoding='utf-8')
            sheet.append(svg.replace('<svg ', f'<svg x="{i*w}" ', 1))
        (output/'sheet.svg').write_text('\n'.join(sheet+['</svg>']), encoding='utf-8')
        if any(digest(path) != sha for path, sha in frozen.items()):
            raise ValueError('Drawing input changed during generation')
        files = {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()}
        manifest = dict(kind='orthographic-drawings-v1', source_asset=str(source),
                        source_sha256=frozen[source], parts_sha256=frozen[parts_path],
                        blender_version=snapshot['blender_version'], settings=settings,
                        source_frame=snapshot['frame'],
                        renderer=dict(engine='BLENDER_WORKBENCH', light='STUDIO', studio_light='paint.sl',
                                      color_type='OBJECT', render_aa='8', view_transform='Standard'),
                        files=files, source_modified=False, approval='not_requested',
                        limitations=['model bounding dimensions only', 'hidden lines omitted',
                                     'schematic part colors; original materials not rendered'])
        (output/'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        return manifest
    except Exception as exc:
        (output/'failure.json').write_text(json.dumps({'status':'failed', 'error':str(exc)}), encoding='utf-8')
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--blender', required=True, type=Path)
    parser.add_argument('--parts', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--meters-per-pixel', required=True, type=float)
    parser.add_argument('--resolution', default=640, type=int)
    parser.add_argument('--center', nargs=3, type=float, default=[0,0,0], metavar=('X','Y','Z'))
    parser.add_argument('--units', choices=tuple(UNIT_METERS), default='mm')
    parser.add_argument('--asset-path', help='Source identifier relative to the run root, e.g. assets/candidate.blend')
    args = parser.parse_args()
    try:
        generate(args.source, args.blender, args.parts, args.output,
                 meters_per_pixel=args.meters_per_pixel, resolution=args.resolution,
                 center=args.center, units=args.units, asset_path=args.asset_path)
        print(json.dumps({'status':'drawings-generated', 'output':str(args.output), 'approval':'not_requested'}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({'status':'failed', 'error':str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
