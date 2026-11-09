"""Offline 2 km CTX workspace. Original RegionalBridge fixtures stay intact."""
import hashlib
import json
from pathlib import Path
from regional_ui import RegionalBridge
from jezero_adapter import GridMapping, CropWindow
from jezero_map import raster
from mars_route_planner import Terrain
from mission_api import TerrainReference


class ExpandedBridge(RegionalBridge):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        folder=Path(__file__).resolve().parents[2]/'data/mission_planner_ctx_2km'
        raw=(folder/'terrain.json').read_bytes()
        meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
        if hashlib.sha256(raw).hexdigest()!=meta['output_sha256']:
            raise ValueError('CTX 2 km: checksum inválido; no se sustituye el terreno')
        data=json.loads(raw)
        if len(data['heights_m'])!=100 or any(len(r)!=100 for r in data['heights_m']) or data['resolution_m']!=20:
            raise ValueError('CTX 2 km: forma/resolución incompatible')
        zero=[[0.]*100 for _ in range(100)]
        self.region=TerrainReference.capture(Terrain(data['heights_m'],[[False]*100 for _ in range(100)],zero,zero,20.),'jezero-ctx-2km-20m')
        self.mapping=GridMapping((100,100),(-1000.,20.,0.,1000.,0.,-20.),CropWindow(0,0,100,100))
        self.region_provenance=dict(source=meta,snapshot=self.region.identity(),mapping=self.mapping.metadata(),
                                    limitation='Solo 2 km; no todo el cráter. Sin obstáculos observados ni alturas HiRISE.')
        self.rasters={k:raster(self.region,k)[0] for k in ('elevation','relief')}

    def defaults(self,name,agent):
        q=super().defaults(name,agent)
        if name=='regional':q.update(base=[50,49],current=[50,49],goal=[50,51])
        return q

    def calculate(self,config,action):
        if config.get('planning_method')=='fast' and action=='compare':
            from fast_mission import fast_calculate
            return fast_calculate(self,config)
        payload=super().calculate(config,action)
        result=payload['result']
        for item in result.get('alternatives') or [result['continuation'],result['returning']]:
            if item['plan']:
                item['mission_conditions']=dict(kind='COMPUTED_ROUTE',
                    message='Para esta ruta calculada necesitas estos saldos iniciales, incluyendo las reservas.',
                    resources=[dict(resource=k,unit=v['unit'],required_initial=v['consumed']+v['reserve'],
                                    current_initial=v['capacity'],satisfied=v['margin_above_reserve']>=-1e-9)
                               for k,v in item['plan']['total']['resources'].items() if v['status']=='modeled'])
            elif (item.get('ui_diagnostic') or {}).get('resources'):
                item['mission_conditions']=dict(kind='OPTIMISTIC_MINIMUM',
                    message='Estos mínimos aún no bastan para garantizar una ruta: los desvíos y pendientes pueden exigir más.',
                    resources=[dict(resource=v['resource'],unit=v['unit'],
                        required_initial=v['minimum_consumption']+config['profile']['resources'][v['resource']]['reserve'],
                        current_initial=config['remaining'][v['resource']],satisfied=False)
                        for v in item['ui_diagnostic']['resources']])
        return payload
