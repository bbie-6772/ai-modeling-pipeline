"""Static evaluated mesh handoff and isolated Unity Editor Play Mode smoke test."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from .files import digest
from .specification import number
from .surface import geometry


def export(snapshot, candidate_sha256, collision='none'):
    if snapshot['source_sha256']!=candidate_sha256 or snapshot['coordinate_space']!='world':
        raise ValueError('Handoff requires the current candidate world snapshot')
    if collision not in ('none','box'):raise ValueError('Supported diagnostic collision: none, box')
    if snapshot['scene_units']['system'] not in ('METRIC','IMPERIAL'):
        raise ValueError('Unity handoff requires physical scene units')
    scale=number(snapshot['scene_units']['scale_length'])
    if not scale:raise ValueError('Physical scale must be positive')
    parts=[];all_points=[]
    for name,record in sorted(snapshot['parts'].items()):
        points,_=geometry(record)
        # Blender right-handed Z-up -> Unity left-handed Y-up; reverse winding.
        vertices=[dict(x=p[0]*scale,y=p[2]*scale,z=p[1]*scale) for p in points]
        triangles=record['triangles']
        if not triangles or any(not isinstance(t,list) or len(t)!=3 or len(set(t))!=3 or
               any(type(i) is not int or not 0<=i<len(points) for i in t) for t in triangles):
            raise ValueError('Actual evaluated Blender triangle indices required')
        parts.append(dict(name=name,vertices=vertices,triangles=[i for a,b,c in triangles for i in (a,c,b)]))
        all_points.extend(vertices)
    if not parts:raise ValueError('Mesh parts required')
    low={axis:min(p[axis] for p in all_points) for axis in ('x','y','z')}
    high={axis:max(p[axis] for p in all_points) for axis in ('x','y','z')}
    return dict(kind='unity-static-mesh-v1',source_sha256=candidate_sha256,units='m',
                coordinate_space='Unity left-handed Y-up',parts=parts,bounds_min=low,bounds_max=high,
                collision=collision,material_mode='diagnostic-flat',rig='not_exported',uv='not_exported')


def run(snapshot_path,candidate,unity,output,collision='none',timeout=300):
    snapshot_path,candidate,output=Path(snapshot_path).resolve(),Path(candidate).resolve(),Path(output).resolve()
    frozen={p:digest(p) for p in (snapshot_path,candidate)}
    handoff=export(json.loads(snapshot_path.read_text(encoding='utf-8')),frozen[candidate],collision)
    output.mkdir(parents=True,exist_ok=False)
    input_path=output/'handoff.json'
    input_path.write_text(json.dumps(handoff,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    project=output/'project'
    def invoke(args,log):
        result=subprocess.run([str(unity),'-batchmode','-nographics','-logFile',str(log),*args],
                              capture_output=True,text=True,timeout=timeout)
        if result.returncode:raise ValueError(f'Unity exited {result.returncode}; inspect {log}')
    try:
        invoke(['-createProject',str(project),'-quit'],output/'create-project.log')
        scripts=Path(__file__).parent/'adapters'/'unity'
        (project/'Assets'/'Editor').mkdir(parents=True,exist_ok=True)
        shutil.copy2(scripts/'PipelineRuntimeProbe.cs',project/'Assets'/'PipelineRuntimeProbe.cs')
        shutil.copy2(scripts/'PipelineEditorImport.cs',project/'Assets'/'Editor'/'PipelineEditorImport.cs')
        raw=output/'engine-raw.json'
        invoke(['-projectPath',str(project),'-executeMethod','PipelineEditorImport.Run',
                '-pipelineInput',str(input_path),'-pipelineReport',str(raw)],output/'unity.log')
        report=json.loads(raw.read_text(encoding='utf-8'))
        if report['candidate_sha256']!=frozen[candidate] or report['import_ok'] is not True or report['runtime_ok'] is not True:
            raise ValueError('Unity import/runtime smoke failed')
        if any(digest(path)!=sha for path,sha in frozen.items()):raise ValueError('Protected Unity input changed')
        report.update(runtime_budget_verified=False,scope='Unity Editor headless Play Mode smoke only',
                      adopted=False,approval='not_granted',
                      material_mode='diagnostic-flat; source materials not verified',
                      handoff_sha256=digest(input_path),snapshot_sha256=frozen[snapshot_path],
                      qa={'I01':'import evidence available','I02':'UNKNOWN: target runtime benchmark not run'})
        report['measurements']['frame_ms']=None
        with (output/'engine-report.json').open('x',encoding='utf-8') as stream:
            json.dump(report,stream,indent=2,ensure_ascii=False,allow_nan=False)
        (output/'runtime-benchmark-request.json').write_text(json.dumps(dict(status='not_run',
            required_inputs=['target platform/device','representative game scene','approved budgets',
                             'rendering and measurement conditions']),indent=2),encoding='utf-8')
        return report
    except Exception as exc:
        (output/'failure.json').write_text(json.dumps(dict(status='failed',error=str(exc))),encoding='utf-8')
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True);parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--unity',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--collision',choices=('none','box'),default='none')
    args=parser.parse_args()
    try:
        report=run(args.snapshot,args.candidate,args.unity,args.output,args.collision)
        print(json.dumps(report,ensure_ascii=False));return 0
    except (OSError,ValueError,KeyError,TypeError,subprocess.TimeoutExpired) as exc:
        print(json.dumps(dict(status='failed',error=str(exc)),ensure_ascii=False));return 2


if __name__=='__main__':raise SystemExit(main())
