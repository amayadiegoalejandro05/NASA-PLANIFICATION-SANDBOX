"""Record bounded live engine evidence; these exports are never UI data sources."""
from copy import deepcopy
from pathlib import Path
import json
import platform

from mission_ui import MissionBridge, UIInputError, strict


def main():
    b=MissionBridge()
    ctx=b.defaults('ctx','astronaut')
    rover=b.defaults('ctx','rover')
    synthetic=b.defaults('synthetic','rover')
    cases={
        'ctx_compare':(deepcopy(ctx),'compare'),
        'ctx_rover':(deepcopy(rover),'compare'),
        'ctx_evaluate':(deepcopy(ctx),'evaluate'),
        'ctx_changed_activity':(dict(deepcopy(ctx),activity_min=3.),'compare'),
        'ctx_completed':(dict(deepcopy(ctx),activity_status='completed',activity_min=0.),'evaluate'),
        'ctx_limit':(dict(deepcopy(ctx),max_labels=1),'evaluate'),
        'ctx_invalid_semantic':(dict(deepcopy(ctx),goal=ctx['base'][:]),'evaluate'),
        'ctx_blocked_goal':(dict(deepcopy(ctx),obstacles=[ctx['goal'][:]]),'evaluate'),
        'ctx_conservative':(dict(deepcopy(ctx),scenario='conservative'),'compare'),
        'synthetic_compare':(deepcopy(synthetic),'compare'),
        'synthetic_obstacle':(dict(deepcopy(synthetic),obstacles=[[3,3]]),'compare'),
        'synthetic_restored':(deepcopy(synthetic),'compare'),
    }
    low=deepcopy(ctx);low['remaining']['battery']=9.
    cases['ctx_insufficient']=(low,'evaluate')
    error=deepcopy(ctx);error['activity_min']=-1.
    cases['ctx_invalid_construction']=(error,'compare')
    results={}
    for name,(config,action) in cases.items():
        try:results[name]=b.calculate(config,action)
        except UIInputError as e:results[name]=dict(configuration=config,error={'status':'INVALID_INPUT','message':str(e)})
    directory=Path(__file__).with_name('evidence')/'stage06'
    directory.mkdir(exist_ok=True)
    (directory/'functional.json').write_text(strict(dict(python=platform.python_version(),cases=results))+'\n',encoding='utf-8')
    (directory/'catalog.json').write_text(strict(dict(maps={m:b.map_data(m) for m in ('ctx','synthetic')},
        defaults={m:{a:b.defaults(m,a) for a in ('astronaut','rover')} for m in ('ctx','synthetic')}))+'\n',encoding='utf-8')
    lines=[]
    for name,v in results.items():
        result=v.get('result')
        states=[x['status'] for x in (result.get('alternatives') or [result['continuation'],result['returning']])] if result else [v['error']['status']]
        lines.append(name+': '+', '.join(states)+(('; decision='+result['decision']) if result and 'decision' in result else ''))
    (directory/'functional-summary.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines))


if __name__=='__main__':main()
