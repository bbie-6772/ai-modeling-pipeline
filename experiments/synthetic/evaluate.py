"""Reconstruct new synthetic references from PNGs, then score against hidden truth.

Reconstruction intentionally does not load truth or heldout views. This tests a
calibrated, fixed-topology inverse-graphics task, not general image understanding.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

from PIL import Image, ImageDraw


def write(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)


def mask(path):
    with Image.open(path) as im:
        return im.getchannel('A').point(lambda a: 255 if a >= 128 else 0)


def sections(path, config):
    image = mask(path)
    bbox = image.getbbox()
    assert bbox is not None
    _, top, _, bottom = bbox
    assert bottom-top >= 200, 'Low-resolution profile requires a different boundary estimator'
    scale = config['ortho_scale_m']/config['resolution']
    samples = []
    for ratio in config['section_height_fractions']:
        row = min(bottom-1, max(top, round(bottom-1-ratio*(bottom-top-1))))
        # ponytail: fixed 3px inset for clean 200+px profiles; use contour-line
        # fitting for smaller or occluded drawings. No truth values consulted.
        if ratio == 0:
            row = bottom-4
        elif ratio == 1:
            row = top+3
        spans = []
        for y in range(max(top, row-1), min(bottom, row+2)):
            extent = image.crop((0, y, image.width, y+1)).getbbox()
            if extent:
                spans.append(extent[2]-extent[0])
        assert spans
        samples.append(statistics.median(spans)*scale)
    return samples, (bottom-top)*scale


def reconstruct_part(folder, config):
    widths, front_height = sections(folder/'front.png', config)
    depths, side_height = sections(folder/'side.png', config)
    assert abs(front_height-side_height) <= 2*config['ortho_scale_m']/config['resolution']
    height = (front_height+side_height)/2
    vertices = []
    c = config['bevel_prior']
    for ratio, width, depth in zip(config['section_height_fractions'], widths, depths):
        for x, y in ((-1+c,-1),(1-c,-1),(1,-1+c),(1,1-c),(1-c,1),(-1+c,1),(-1,1-c),(-1,-1+c)):
            vertices.append([x*width/2,y*depth/2,(ratio-.5)*height])
    faces = [list(reversed(range(8))), list(range(16,24))]
    for ring in range(2):
        for n in range(8):
            faces.append([ring*8+n,ring*8+(n+1)%8,(ring+1)*8+(n+1)%8,(ring+1)*8+n])
    return {'vertices': vertices, 'faces': faces}


def reconstruct(root):
    config = json.loads((root/'public.json').read_text())
    candidates, timings = {}, {}
    for method in ('A', 'B'):
        rounds = []
        for repeat in range(3):
            started = time.perf_counter()
            cases = {}
            for case in config['cases']:
                cases[case] = {}
                representative = None
                for part in config['parts']:
                    if method == 'A' or representative is None:
                        representative = reconstruct_part(root/'reference'/case/part, config)
                    cases[case][part] = copy.deepcopy(representative)
            rounds.append(time.perf_counter()-started)
        candidates[method] = cases
        timings[method] = {'seconds': rounds, 'median_seconds': statistics.median(rounds),
                           'unique_source_images_read': len(config['cases'])*(8 if method=='A' else 2),
                           'model_tokens': None, 'human_review_seconds': None}
    write(root/'candidates.json', candidates)
    write(root/'reconstruction-metrics.json', timings)


def iou(a, b):
    ap, bp = a.tobytes(), b.tobytes()
    intersection = sum(bool(x) and bool(y) for x,y in zip(ap,bp))
    union = sum(bool(x) or bool(y) for x,y in zip(ap,bp))
    return intersection/union if union else 1


def evaluate(root):
    config = json.loads((root/'public.json').read_text())
    truth = json.loads((root/'evaluator/truth.json').read_text())
    candidates = json.loads((root/'candidates.json').read_text())
    metrics = json.loads((root/'reconstruction-metrics.json').read_text())
    records = []
    for method, cases in candidates.items():
        for case, parts in cases.items():
            for part, reconstruction in parts.items():
                target = truth[case][part]
                diagonal = math.sqrt(sum((max(v[i] for v in target['vertices'])-min(v[i] for v in target['vertices']))**2 for i in range(3)))
                rmse = math.sqrt(statistics.mean(math.dist(a,b)**2 for a,b in zip(target['vertices'],reconstruction['vertices'])))
                values = {}
                for view in ('front','side','heldout'):
                    reference = root/('evaluator' if view=='heldout' else 'reference')/case/part/(view+'.png')
                    values[view] = iou(mask(reference),mask(root/'rendered'/method/case/part/(view+'.png')))
                passed = rmse/diagonal <= config['predeclared_thresholds']['normalized_vertex_rmse'] and values['heldout'] >= config['predeclared_thresholds']['heldout_silhouette_iou']
                records.append({'method':method,'case':case,'part':part,'vertex_rmse_m':rmse,
                                'normalized_vertex_rmse':rmse/diagonal,'silhouette_iou':values,'passed':passed})
    # Runnable checks: detect a per-part exception and two-view ambiguity.
    bykey = {(r['method'],r['case'],r['part']):r for r in records}
    assert all(bykey[m,'S01',p]['passed'] for m in ('A','B') for p in config['parts'])
    assert bykey['A','S02','RR']['passed'] and not bykey['B','S02','RR']['passed']
    assert all(not bykey[m,'S03','RR']['passed'] for m in ('A','B'))
    result = {'status':'completed','thresholds':config['predeclared_thresholds'],
              'metrics':metrics,'records':records,'ground_truth_checks_passed':True,
              'conditions':{'S01':'Exact repeated geometry','S02':'RR depth is 22% greater',
                            'S03':'RR corner bevel differs while front/side silhouettes are identical'},
              'limits':'Known camera/scale and fixed topology; clean synthetic masks. Not LLM vision, token-cost, human-rework or production certification.'}
    write(root/'result.json',result)
    board = Image.new('RGB',(1600,1050),'#eeeeee')
    draw = ImageDraw.Draw(board)
    for row,case in enumerate(config['cases']):
        entries = [(root/'reference'/case/'RR/front.png','New source: front'),
                   (root/'evaluator'/case/'RR/heldout.png','Ground truth: heldout oblique'),
                   (root/'rendered/A'/case/'RR/heldout.png','A: per-part reconstruction'),
                   (root/'rendered/B'/case/'RR/heldout.png','B: shared representative')]
        for col,(path,label) in enumerate(entries):
            with Image.open(path) as im:
                im=im.convert('RGBA');im.thumbnail((360,300))
                tile=Image.new('RGBA',im.size,'white');tile.alpha_composite(im)
                board.paste(tile.convert('RGB'),(col*400+15,row*350+40))
            draw.text((col*400+15,row*350+10),case+' '+label,fill='black')
    board.save(root/'comparison.png')
    print(json.dumps({'ground_truth_checks_passed':True,'RR_records':[r for r in records if r['part']=='RR'],'metrics':metrics},indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stage',choices=['reconstruct','evaluate'])
    ap.add_argument('root',type=Path)
    args=ap.parse_args()
    (reconstruct if args.stage=='reconstruct' else evaluate)(args.root.resolve())
