"""Compare replay outputs, check input hashes, and make an evidence board."""
import hashlib
import json
import math
from pathlib import Path
import sys

from PIL import Image, ImageDraw


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main(root):
    recipe = json.loads((root / 'recipe.json').read_text())
    a, b = [json.loads((root / m / 'geometry.json').read_text()) for m in ('A', 'B')]
    ma, mb = [json.loads((root / m / 'metrics.json').read_text()) for m in ('A', 'B')]
    checks = [json.loads((root / m / 'reopen_check.json').read_text()) for m in ('A', 'B')]
    assert ma['baseline_sha256'] == mb['baseline_sha256']
    assert ma['recipe_sha256'] == mb['recipe_sha256'] == sha(root / 'recipe.json')
    assert sha(Path(recipe['source'])) == recipe['source_sha256']
    baseline = Path(recipe['source']).with_name('model_ear_v02_cpu.blend')
    assert sha(baseline) == ma['baseline_sha256'], 'Adopted baseline changed'
    errors = {}
    for leg in a:
        assert len(a[leg]['vertices']) == len(b[leg]['vertices'])
        assert a[leg]['faces'] == b[leg]['faces']
        assert a[leg]['materials'] == b[leg]['materials']
        assert a[leg]['smooth'] == b[leg]['smooth']
        errors[leg] = max(math.dist(p, q) for p, q in zip(a[leg]['vertices'], b[leg]['vertices']))
    assert max(errors.values()) < 1e-6
    assert all(c['passed'] for c in checks)
    result = {'experiment': 'paw-workflow-pilot-01', 'status': 'replay_complete_human_quality_review_pending',
              'scope': 'Four paw shells only; trace interpretation/modeling/human gates are NOT benchmarked.',
              'max_vertex_difference_m': errors,
              'topology_materials_smoothing_equal': True, 'input_models_unchanged': True,
              'protected_scene_objects_unchanged_on_reopen': True,
              'methods': {m['method']: {'build_seconds': m['build_seconds'], 'render_seconds': m['render_seconds'],
                                        'render_count': m['render_count']} for m in (ma, mb)},
              'render_time_reduction_percent': 100*(1-mb['render_seconds']/ma['render_seconds']),
              'sample_size_per_method': 1, 'execution_order': ['A', 'B'],
              'human_review_seconds': None, 'tokens_by_method': None, 'rework_count': None,
              'source_conformance': 'not_scored_no_independent_calibration',
              'inference': 'Fewer renders reduce render time; no evidence yet that grouping preserves source accuracy or reduces total project cost.'}
    with (root / 'result.json').open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    board = Image.new('RGB', (1600, 960), '#e8e8e8')
    draw = ImageDraw.Draw(board)
    draw.text((20, 15), 'A: independent shells / 32 views     |     B: shared mirror recipe / 3 group views', fill='black')
    draw.text((20, 35), 'Replay only. Same input baseline. Not a source-conformance or AI-token benchmark.', fill='black')
    entries = [('A/FL_front.png', 'A - FL front close-up'), ('A/FL_oblique1.png', 'A - FL oblique close-up'),
               ('B/group_front.png', 'B - group front (rear shells occluded)'), ('B/group_oblique.png', 'B - group oblique'),
               ('A/RL_rear.png', 'A - RL rear close-up'), ('A/FL_bottom.png', 'A - FL bottom close-up'),
               ('B/group_bottom.png', 'B - group bottom'), ('A/RR_oblique2.png', 'A - RR opposite oblique')]
    for i, (path, label) in enumerate(entries):
        x, y = (i % 4)*400, 75+(i // 4)*430
        with Image.open(root / path) as original:
            image = original.convert('RGBA')
            image.thumbnail((390, 390))
            tile = Image.new('RGBA', image.size, '#ffffff')
            tile.alpha_composite(image)
            board.paste(tile.convert('RGB'), (x, y))
        draw.text((x+8, y+395), label, fill='black')
    board.save(root / 'comparison.png')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main(Path(sys.argv[1]))
