"""Reproducible numeric audit evidence. Run with SANDBOX .venv Python from root."""
from pathlib import Path
import sys
import json
import platform
import subprocess
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'prototypes/mission_planner'))
from expanded_ui import ExpandedBridge
from mission_ui import strict

b = ExpandedBridge()
config = b.defaults('regional','astronaut')
config.update(planning_method='fast',goal=[50,80],obstacles=[[49,60],[50,60],[51,60]])
before = b.calculate(config,'compare')
prepared = deepcopy(config)
changes = []
for r in before['result']['alternatives'][0]['mission_conditions']['resources']:
    k = r['resource']
    old = prepared['remaining'][k]
    value = max(old,r['required_initial'])
    if value>old:
        prepared['remaining'][k]=value
        prepared['profile']['resources'][k]['capacity']=max(prepared['profile']['resources'][k]['capacity'],value)
        changes.append(dict(resource=k,previous=old,adjusted=value))
prepared['resource_adjustments']=[dict(basis='MEASURED_CANDIDATE',calculation_id=before['calculation_id'],
                                      changes=changes,reserves_unchanged=True)]
after = b.calculate(prepared,'compare')
assert after['result']['alternatives'][0]['status']=='SUCCESS'
assert before['candidate_plan']['path']==after['candidate_plan']['path']
(OUT/'preparation.json').write_text(strict(dict(configuration=config,before=before,prepared=prepared,after=after)),encoding='utf-8')
environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),
                 dependencies=subprocess.check_output([sys.executable,'-m','pip','list','--format=json'],text=True))
(OUT/'environment.json').write_text(json.dumps(environment,indent=2),encoding='utf-8')
print('PASS: real CTX complete candidate -> unchanged reserves/rates/terrain -> SUCCESS; strict JSON saved.')
