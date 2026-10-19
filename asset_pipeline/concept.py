"""Prepare a frozen image-generation request and register an unapproved AI candidate."""
import argparse
import json
from pathlib import Path
import shutil

from .files import digest
from .specification import nonempty


def prepare(brief, output):
    for field in ('asset_id','design_revision','description'):
        nonempty(brief[field])
    if not isinstance(brief['parts'],list) or not brief['parts'] or len(set(brief['parts']))!=len(brief['parts']):
        raise ValueError('Unique proposed part IDs required')
    for part in brief['parts']:nonempty(part)
    for constraint in brief['constraints']:nonempty(constraint)
    prompt=('Create one unapproved game-prop design concept.\nSubject: '+brief['description']+
            '\nProposed parts: '+', '.join(brief['parts'])+'\nConstraints:\n'+
            '\n'.join('- '+value for value in brief['constraints'])+
            '\nSingle three-quarter view on a plain white background. No dimensions, text, logos, or technical drawing claims. '
            'Keep component boundaries readable. This image is a visual proposal, not measured geometry.\n')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    (output/'brief.json').write_text(json.dumps(brief,indent=2,ensure_ascii=False),encoding='utf-8')
    (output/'prompt.txt').write_text(prompt,encoding='utf-8')
    request=dict(schema_version='concept-request-v1',status='awaiting-generation',
                 brief_sha256=digest(output/'brief.json'),prompt_sha256=digest(output/'prompt.txt'))
    (output/'request.json').write_text(json.dumps(request,indent=2),encoding='utf-8')
    return prompt


def register(output, image, provider):
    output,image=Path(output),Path(image)
    nonempty(provider)
    if (output/'candidate.json').exists() or (output/'candidate.png').exists() or (output/'shape-draft.json').exists():
        raise ValueError('Candidate already registered; use a new request directory')
    request=json.loads((output/'request.json').read_text())
    if request['schema_version']!='concept-request-v1' or any(
            digest(output/name)!=request[key] for name,key in
            (('brief.json','brief_sha256'),('prompt.txt','prompt_sha256'))):
        raise ValueError('Generation request was modified')
    with image.open('rb') as stream:
        if stream.read(8)!=b'\x89PNG\r\n\x1a\n':raise ValueError('Generated PNG required')
    frozen=digest(image)
    with (output/'candidate.png').open('xb') as stream, image.open('rb') as source:
        shutil.copyfileobj(source,stream)
    if digest(output/'candidate.png')!=frozen:raise ValueError('Candidate changed while copying')
    brief=json.loads((output/'brief.json').read_text(encoding='utf-8'))
    draft=dict(schema_version='shape-contract-v1',asset_id=brief['asset_id'],design_revision=brief['design_revision'],units='m',
               references={'concept':dict(path='candidate.png',sha256=frozen,view='oblique')},
               parts={part:dict(objects=['REPLACE_WITH_EXACT_MESH_OBJECT'],observations=[
                   dict(basis='unknown',description='AI appearance requires human reference analysis',reference_ids=['concept'])])
                   for part in brief['parts']},
               dimensions={part:dict(size=None,tolerance=None,basis='unknown',
                   description='Physical size and hidden depth are not established by the image',reference_ids=['concept'])
                   for part in brief['parts']},
               uncertainties=[dict(part=part,description='Dimensions, hidden shape and exact mesh mapping await review',blocking=True)
                              for part in brief['parts']])
    (output/'shape-draft.json').write_text(json.dumps(draft,indent=2,ensure_ascii=False),encoding='utf-8')
    record=dict(schema_version='concept-candidate-v1',asset_id=brief['asset_id'],design_revision=brief['design_revision'],
                provider=provider,model_id=None,image='candidate.png',image_sha256=frozen,
                prompt_sha256=request['prompt_sha256'],brief_sha256=request['brief_sha256'],
                shape_draft_sha256=digest(output/'shape-draft.json'),status='pending-human-review',
                selected=False,approved=False,geometry_validation='not_run')
    with (output/'candidate.json').open('x',encoding='utf-8') as stream:
        json.dump(record,stream,indent=2,ensure_ascii=False)
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    create=commands.add_parser('prepare');create.add_argument('brief',type=Path);create.add_argument('--output',type=Path,required=True)
    add=commands.add_parser('register');add.add_argument('output',type=Path);add.add_argument('--image',type=Path,required=True)
    add.add_argument('--provider',required=True)
    args=parser.parse_args()
    try:
        result=prepare(json.loads(args.brief.read_text(encoding='utf-8')),args.output) if args.command=='prepare' else register(args.output,args.image,args.provider)
        print(json.dumps(result,ensure_ascii=False));return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps(dict(status='blocked',error=str(exc)),ensure_ascii=False));return 2


if __name__=='__main__':raise SystemExit(main())
