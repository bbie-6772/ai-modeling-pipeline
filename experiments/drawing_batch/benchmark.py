"""Read-only A/B: independent per-view capture versus existing batched drawing CLI.

This is a drawing-generation microbenchmark, not an AI/human modeling benchmark.
Every failure is retained; no retry or trial replacement is performed.
"""
import argparse
import json
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import time
from unittest.mock import patch

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO))
from asset_pipeline.drawing import generate,layout,panel,VIEWS
from asset_pipeline.files import digest
from asset_pipeline.shape_contract import verify_drawings

COMMON={'snapshot.json','parts.json','render-config.json','sheet.svg'}|{
    name+ext for name in VIEWS for ext in ('.png','.svg')}


def unbatched(plan,output,invoke):
    """Same inputs/settings/outputs, six real Blender processes instead of two."""
    source=Path(plan['source']);mapping=json.loads(Path(plan['parts']).read_text(encoding='utf-8'))
    output.mkdir()
    (output/'parts.json').write_text(json.dumps(mapping,ensure_ascii=False),encoding='utf-8')
    adapter=REPO/'asset_pipeline/adapters/blender'
    prefix=[plan['blender'],'--background','--factory-startup','--disable-autoexec','--python-exit-code','1']
    for name in VIEWS:
        folder=output/name;folder.mkdir()
        invoke([*prefix,str(source),'--python',str(adapter/'snapshot.py'),'--',
                '--parts',str(output/'parts.json'),'--output',str(folder/'snapshot.json'),'--asset-path',source.name],
               capture_output=True,text=True,timeout=plan['timeout_seconds'])
        snapshot=json.loads((folder/'snapshot.json').read_text(encoding='utf-8'))
        settings=layout(snapshot,plan['meters_per_pixel'],plan['resolution'],plan['center_m'],plan['units'])
        one=dict(settings,views={name:settings['views'][name]})
        (folder/'render-config.json').write_text(json.dumps(one,allow_nan=False),encoding='utf-8')
        invoke([*prefix,'--python',str(adapter/'drawing.py'),'--',str(folder)],
               capture_output=True,text=True,timeout=plan['timeout_seconds'])
        shutil.copy2(folder/(name+'.png'),output/(name+'.png'))
        (output/(name+'.svg')).write_text(panel(name,settings['views'][name],settings,
                                              (output/(name+'.png')).read_bytes()),encoding='utf-8')
        if name=='front':shutil.copy2(folder/'snapshot.json',output/'snapshot.json')
    (output/'render-config.json').write_text(json.dumps(settings,allow_nan=False),encoding='utf-8')
    width=plan['resolution']+200
    sheet=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width*3}" height="{width}">']
    for i,name in enumerate(VIEWS):
        sheet.append((output/(name+'.svg')).read_text(encoding='utf-8').replace('<svg ',f'<svg x="{i*width}" ',1))
    (output/'sheet.svg').write_text('\n'.join(sheet+['</svg>']),encoding='utf-8')
    files={p.name:digest(p) for p in sorted(output.iterdir()) if p.is_file()}
    manifest=dict(kind='orthographic-drawings-v1',source_asset=str(source),source_sha256=digest(source),
                  parts_sha256=digest(Path(plan['parts'])),blender_version=snapshot['blender_version'],
                  settings=settings,source_frame=snapshot['frame'],
                  renderer=dict(engine='BLENDER_WORKBENCH',light='STUDIO',studio_light='paint.sl',
                                color_type='OBJECT',render_aa='8',view_transform='Standard'),
                  files=files,source_modified=False,approval='not_requested',
                  limitations=['model bounding dimensions only','hidden lines omitted',
                               'schematic part colors; original materials not rendered'])
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    plan=json.loads(args.plan.read_text(encoding='utf-8'));output=args.output.resolve()
    if plan['order']!=['ABBA','BAAB','ABBA']:raise ValueError('Locked six-pair order required')
    if digest(Path(__file__))!=plan['runner_sha256']:raise ValueError('Benchmark runner changed after plan lock')
    for path,sha in plan['input_hashes'].items():
        if digest(Path(path))!=sha:raise ValueError('Frozen input changed: '+path)
    decision=json.loads(Path(plan['case_decision']).read_text(encoding='utf-8'))
    if decision['candidate_sha256']!=digest(Path(plan['source'])):raise ValueError('Case decision is stale')
    output.mkdir(parents=True,exist_ok=False)
    shutil.copy2(args.plan,output/'plan.json')
    real_run=subprocess.run;golden=None;records=[];quality_ok=True
    sequence=[('warmup-A','A',True),('warmup-B','B',True)]
    sequence.extend((f'measure-{i+1:02d}-{condition}',condition,False)
                    for i,condition in enumerate(''.join(plan['order'])))
    try:
        for name,condition,warmup in sequence:
            calls=[];row=dict(run=name,condition=condition,warmup=warmup,status='running')
            def invoke(command,**kwargs):
                begin=time.perf_counter()
                try:
                    result=real_run(command,**kwargs)
                    calls.append(dict(command=command,seconds=time.perf_counter()-begin,returncode=result.returncode))
                    if result.returncode:raise RuntimeError(result.stdout[-3000:]+result.stderr[-3000:])
                    return result
                except Exception as exc:
                    calls.append(dict(command=command,error=str(exc)));raise
            start=time.perf_counter()
            try:
                folder=output/name
                if condition=='A':unbatched(plan,folder,invoke)
                else:
                    # Observe real calls only; never stub or replace Blender results.
                    with patch('asset_pipeline.drawing.subprocess.run',invoke):
                        generate(plan['source'],plan['blender'],plan['parts'],folder,
                                 meters_per_pixel=plan['meters_per_pixel'],resolution=plan['resolution'],
                                 center=plan['center_m'],units=plan['units'],timeout=plan['timeout_seconds'])
                row['seconds']=time.perf_counter()-start
                snapshot,manifest=verify_drawings(folder/'manifest.json',plan['source_sha256'])
                actual={name:digest(folder/name) for name in sorted(COMMON)}
                if golden is None:golden=actual
                if actual!=golden:raise ValueError('Common deliverables differ; speed comparison rejected')
                if snapshot['blender_version']!=plan['blender_version']:raise ValueError('Blender version changed')
                if len(calls)!=(6 if condition=='A' else 2):raise ValueError('Unexpected actual process count')
                for path,sha in plan['input_hashes'].items():
                    if digest(Path(path))!=sha:raise ValueError('Frozen input changed during trial')
                row.update(status='ok',quality_equal=True,processes=len(calls),files=actual)
            except Exception as exc:
                row.update(status='failed',error=str(exc));quality_ok=False;raise
            finally:
                row['calls']=calls;records.append(row)
                with (output/'trials.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(row)+'\n')
                print(json.dumps({k:v for k,v in row.items() if k not in ('calls','files')}),flush=True)
        measured=[r for r in records if not r['warmup']]
        times={c:[r['seconds'] for r in measured if r['condition']==c] for c in ('A','B')}
        pairs=[]
        for i in range(0,len(measured),2):
            pair={r['condition']:r['seconds'] for r in measured[i:i+2]}
            pairs.append(dict(pair=i//2+1,A_seconds=pair['A'],B_seconds=pair['B'],
                              saved_fraction=1-pair['B']/pair['A']))
        stats={c:dict(n=len(v),median_seconds=statistics.median(v),mean_seconds=statistics.mean(v),
                      min_seconds=min(v),max_seconds=max(v)) for c,v in times.items()}
        report=dict(status='completed',scope='read-only drawing generation only',quality_equal=quality_ok,
                    conditions=dict(A='independent snapshot+render per view (6 actual processes)',
                                    B='existing batched generator (2 actual processes)'),
                    warmups_excluded=2,statistics=stats,paired_results=pairs,
                    median_paired_saved_fraction=statistics.median(p['saved_fraction'] for p in pairs),
                    source_sha256=plan['source_sha256'],plan_sha256=digest(args.plan),
                    platform=platform.platform(),python=sys.version,
                    human_time=None,tokens=None,end_to_end_modeling_savings=None,
                    limitations=['One approved scoped case on one host','Constructed unbatched technical reference, not an observed human baseline',
                                 'Warm filesystem/driver caches; interleaved order, no cache flushing',
                                 'No AI generation, modeling, human review, or Unity timing comparison'])
        (output/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report),flush=True)
    except Exception as exc:
        (output/'failure.json').write_text(json.dumps(dict(error=str(exc),records_retained=len(records),retry=False)),encoding='utf-8')
        raise


if __name__=='__main__':main()
