"""Run the original two factors in a counterbalanced, non-destructive replay.

Blender (input CPU settings unchanged across conditions) is run sequentially to
avoid CPU contention. Each condition starts from the same adopted baseline.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time
import math
from PIL import Image, ImageDraw, ImageChops


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def overlay(output, mode, proposal):
    """Diagnostic 40% overlay with uniform scale and bbox-center translation only.

    Camera is uncalibrated: residuals are not a source-conformance score.
    """
    source = proposal['main']
    box = source['crop_xyxy']
    with Image.open(source['path']) as im:
        ref = im.crop(box).convert('RGBA').resize(((box[2]-box[0])*4, (box[3]-box[1])*4))
    raw = output / ('FL_front.png' if mode == 'individual8' else 'overlay_front.png')
    with Image.open(raw) as im:
        model = im.convert('RGBA')
    bbox = model.getchannel('A').getbbox()
    assert bbox is not None
    points = [p['xy'] for p in proposal['points'] if p['kind'] == 'silhouette']
    lo = [min(p[i] for p in points) for i in (0, 1)]
    hi = [max(p[i] for p in points) for i in (0, 1)]
    factor = (hi[0]-lo[0])*4 / (bbox[2]-bbox[0])
    cropped = model.crop(bbox)
    cropped = cropped.resize((round(cropped.width*factor), round(cropped.height*factor)))
    center = [((lo[i]+hi[i])/2-box[i])*4 for i in (0, 1)]
    layer = Image.new('RGBA', ref.size)
    layer.alpha_composite(cropped, (round(center[0]-cropped.width/2), round(center[1]-cropped.height/2)))
    alpha = layer.getchannel('A').point(lambda a: round(a*.4))
    layer.putalpha(alpha)
    mixed = Image.alpha_composite(ref, layer)
    canvas = Image.new('RGB', (ref.width*2, ref.height+45), 'white')
    canvas.paste(ref.convert('RGB'), (0, 45))
    canvas.paste(mixed.convert('RGB'), (ref.width, 45))
    ImageDraw.Draw(canvas).text((10, 10), 'Source | 40% overlay. Uniform width fit only; camera NOT calibrated.', fill='black')
    canvas.save(output / 'source_overlay.png')
    return {'opacity': .4, 'alignment': 'uniform width fit plus bbox-center translation',
            'camera_calibrated': False, 'image': 'source_overlay.png'}


def run(root, project, blender, round_number):
    script = Path(__file__).with_name('experiment.py').resolve()
    recipe = root / 'recipe.json'
    source = Path(json.loads(recipe.read_text())['source'])
    baseline = source.with_name('model_ear_v02_cpu.blend')
    inputs = [source, baseline, recipe, project / 'state.json', project / 'pipeline/asset_contract.json']
    proposal_path = project / 'reviews/reference_batch_20261015/legs/A01.json'
    proposal = json.loads(proposal_path.read_text(encoding='utf-8'))
    inputs.extend([proposal_path, Path(proposal['main']['path'])])
    before = {str(p): sha(p) for p in inputs}
    # Same two original factors; cross-controls separate grouping from fewer views.
    order = [('A', 'individual8'), ('B', 'individual8'), ('A', 'group3'), ('B', 'group3')]
    if round_number % 2 == 0:
        order.reverse()
    records = []
    for method, views in order:
        output = root / f'round-{round_number}-{method}-{views}'
        command = [str(blender), '--background', '--disable-autoexec', str(baseline),
                   '--python-exit-code', '1', '--python', str(script), '--', method,
                   '--project', str(project), '--out', str(output), '--recipe', str(recipe),
                   '--review-mode', views]
        started = time.perf_counter()
        completed = subprocess.run(command, capture_output=True, timeout=180)
        seconds = time.perf_counter() - started
        (root / (output.name + '.log')).write_bytes(completed.stdout + completed.stderr)
        assert completed.returncode == 0, output
        check_command = [str(blender), '--background', '--disable-autoexec', str(output / 'candidate.blend'),
                         '--python-exit-code', '1', '--python', str(script), '--', 'check',
                         '--project', str(project), '--out', str(output), '--recipe', str(recipe)]
        check = subprocess.run(check_command, capture_output=True, timeout=60)
        (root / (output.name + '-check.log')).write_bytes(check.stdout + check.stderr)
        assert check.returncode == 0, 'Reopen failed: ' + str(output)
        metric = json.loads((output / 'metrics.json').read_text())
        board_started = time.perf_counter()
        overlay_info = overlay(output, views, proposal)
        board_seconds = time.perf_counter() - board_started
        records.append({'round': round_number, 'method': method, 'review_mode': views,
                        'process_seconds': seconds, 'build_seconds': metric['build_seconds'],
                        'render_seconds': metric['render_seconds'], 'render_count': metric['render_count'],
                        'board_seconds': board_seconds, 'overlay': overlay_info, 'output': output.name})
        assert {str(p): sha(p) for p in inputs} == before, 'Input modified'
        print('CONDITION_PASS', output.name, flush=True)
    with (root / f'round-{round_number}.json').open('x') as f:
        json.dump({'order': order, 'script_sha256': sha(script), 'inputs': before, 'records': records}, f, indent=2)


def summarize(root):
    rounds = [json.loads((root / f'round-{n}.json').read_text()) for n in (1, 2, 3)]
    assert all(r['inputs'] == rounds[0]['inputs'] for r in rounds)
    assert len({r['script_sha256'] for r in rounds}) == 1
    records = [v for r in rounds for v in r['records']]
    reference = None
    max_error = 0
    for record in records:
        output = root / record['output']
        geometry = json.loads((output / 'geometry.json').read_text())
        if reference is None:
            reference = geometry
        for leg in reference:
            assert all(reference[leg][k] == geometry[leg][k] for k in ('faces', 'materials', 'smooth'))
            assert len(reference[leg]['vertices']) == len(geometry[leg]['vertices'])
            max_error = max(max_error, max(math.dist(p, q) for p, q in zip(reference[leg]['vertices'], geometry[leg]['vertices'])))
        assert max_error < 1e-6
        assert json.loads((output / 'reopen_check.json').read_text())['passed']
    summary = {}
    for method in ('A', 'B'):
        for mode in ('individual8', 'group3'):
            rows = [r for r in records if r['method'] == method and r['review_mode'] == mode]
            summary[method + '_' + mode] = {k: {'median': statistics.median(r[k] for r in rows),
                                                'min': min(r[k] for r in rows), 'max': max(r[k] for r in rows)}
                                            for k in ('build_seconds', 'render_seconds', 'process_seconds', 'board_seconds')}
    same_camera_pixels = []
    for n in (1, 2, 3):
        paths = [root / f'round-{n}-A-individual8/FL_front.png',
                 root / f'round-{n}-B-individual8/FL_front.png',
                 root / f'round-{n}-A-group3/overlay_front.png',
                 root / f'round-{n}-B-group3/overlay_front.png']
        with Image.open(paths[0]) as im:
            reference_image = im.convert('RGBA')
        for path in paths[1:]:
            with Image.open(path) as im:
                difference = ImageChops.difference(reference_image, im.convert('RGBA'))
                pixel_error = max(high for low, high in difference.getextrema())
            same_camera_pixels.append(pixel_error)
    assert max(same_camera_pixels) == 0, 'Identical-camera representative renders differ'
    for path, expected in rounds[0]['inputs'].items():
        assert sha(Path(path)) == expected
    result = {'runs': 12, 'repeats_per_condition': 3, 'summary': summary,
              'max_world_vertex_difference_m': max_error, 'reopen_and_protection_checks_passed': 12,
              'all_input_hashes_unchanged': True, 'fresh_trace_modeling_tested': False,
              'max_representative_render_pixel_channel_difference': max(same_camera_pixels),
              'human_review_seconds': None, 'rework_count': None, 'model_tokens': None,
              'source_design_accuracy_certified': False,
              'scope': 'Deterministic paw-shell replay. Original processing/review factors only. No candidate adopted.'}
    with (root / 'final-result.json').open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root', type=Path)
    ap.add_argument('--round', type=int, choices=[1, 2, 3])
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--blender', type=Path, required=True)
    args = ap.parse_args()
    if args.round:
        run(args.root.resolve(), args.project, args.blender, args.round)
    else:
        summarize(args.root.resolve())
