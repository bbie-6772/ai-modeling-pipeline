"""Profile policy is separate from the executor and cannot disable core checks."""
from pathlib import Path
import json

PROFILE_PATH = Path(__file__).resolve().parents[1] / 'profiles' / 'assets.json'


def policy(spec):
    profiles = json.loads(PROFILE_PATH.read_text(encoding='utf-8'))
    profile = profiles[spec['profile']]
    required = set(profile['required'])
    exceptions = {}
    for check, rule in profile['conditional'].items():
        if spec['features'][rule['feature']] or (check == 'R03' and spec['features']['lod']):
            required.add(check)
        else:
            exceptions[check] = rule['exception']
    return required, exceptions
