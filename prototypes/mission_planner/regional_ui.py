"""Regional adapter to the unchanged stage 5 engine and legacy UI transport."""
from dataclasses import replace, asdict
import math
from mission_ui import MissionBridge, UIInputError
from mission_api import _profile_data
from jezero_map import regional, en_to_planet, planet_to_en, raster, LAYERS
from mars_mission_resources import ResourceMissionPlanner


class RegionalBridge(MissionBridge):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from mission_ui import ROOT
        self.region,self.mapping,self.region_provenance=regional(kwargs.get('data_folder',args[0] if args else ROOT/'data/jezero'))
        self.rasters={k:raster(self.region,k)[0] for k in ('elevation','relief')}

    def original(self, name):
        if name=='regional':return self.region,self.mapping.frame
        return super().original(name)

    def defaults(self, name, agent):
        if name!='regional':return super().defaults(name,agent)
        q=super().defaults('ctx',agent)
        q.update(map='regional',base=[12,10],current=[12,10],goal=[12,12],mission_mode='new',selections={})
        return q

    def profile(self, config):
        if config['map']!='regional':return super().profile(config)
        legacy=dict(config,map='ctx')
        return super().profile(legacy)

    def build(self, config):
        if config.get('mission_mode','ongoing') not in ('new','ongoing'):
            raise ValueError('Modo de misión desconocido')
        if config.get('mission_mode')=='new' and config['base']!=config['current']:
            raise ValueError('En una misión nueva, salida y posición actual deben coincidir')
        return super().build(config)

    def map_data(self, name):
        if name!='regional':return super().map_data(name)
        data=dict(**self.region.identity(),frame=asdict(self.mapping.frame),provenance=self.region_provenance,
            description=f'Área CTX: {self.region.snapshot.cols*20:g} × {self.region.snapshot.rows*20:g} m; celdas de 20 m. No equivale a todo Jezero.',
            bounds=[en_to_planet(*self.mapping.corner_jezero(self.region.snapshot.rows,0)),
                    en_to_planet(*self.mapping.corner_jezero(0,self.region.snapshot.cols))],cells=[])
        for r in range(self.region.snapshot.rows):
            for c in range(self.region.snapshot.cols):
                en=self.mapping.cell_jezero((r,c))
                data['cells'].append(dict(cell=[r,c],planner_xy_m=self.mapping.cell_planner((r,c)),east_north_m=en,
                    latlon=en_to_planet(*en),height_m=self.region.snapshot.heights_m[r][c],risk=0.))
        return data

    def catalog(self):
        names=('ctx','synthetic','regional')
        return dict(maps={k:self.map_data(k) for k in names},defaults={k:{a:self.defaults(k,a) for a in ('astronaut','rover')} for k in names},
            cartography=dict(layers=LAYERS,overview_bounds=[[18.05,77.05],[18.9,77.95]],
                crs='Mars sphere / equirectangular degrees. Planetocentric latitude; east longitude.',
                wmts=dict(origin=[-180,90],tile_size=256,matrix_width='2^(z+1)',matrix_height='2^z',matrix_set='default028mm'),
                radius_m=3396190.,origin_latlon=[18.45,77.45]))

    def select(self, config, point):
        try:
            if config['map']=='regional':
                en=planet_to_en(*point)
                cell=list(self.mapping.jezero_to_cell(en))
                used=en_to_planet(*self.mapping.cell_jezero(tuple(cell)))
            else:
                # Legacy testing maps use metric coordinates displayed as [north,east].
                en=[point[1],point[0]]
                if config['map']=='ctx':
                    cell=list(self.ctx.mapping.jezero_to_cell(en));used=list(reversed(self.ctx.mapping.cell_jezero(tuple(cell))))
                else:
                    t,_=self.original('synthetic');cell=[math.floor(-en[1]),math.floor(en[0])]
                    self.check_cell(cell,t.snapshot);used=[-(cell[0]+.5),cell[1]+.5]
        except (ValueError,TypeError,KeyError) as error:
            raise UIInputError('Punto fuera de la cobertura de cálculo o inválido. Explore el cráter, pero seleccione dentro del área delimitada. '+str(error)) from error
        info=self.inspect(config,cell)
        return dict(**info,chosen_latlon=point,used_latlon=used,
            height_m=self.original(config['map'])[0].snapshot.heights_m[cell[0]][cell[1]],
            adjustment_m=math.hypot(en[0]-(self.mapping.cell_jezero(tuple(cell))[0] if config['map']=='regional' else en[0]),
                                    en[1]-(self.mapping.cell_jezero(tuple(cell))[1] if config['map']=='regional' else en[1])))

    def calculate(self, config, action):
        payload=super().calculate(config,action)
        if config['map']=='regional':
            payload['provenance']=self.region_provenance
            payload['frames']['display']='MARS_PLANETOCENTRIC_LATITUDE_EAST_LONGITUDE'
            for w in payload['waypoints']:
                w['east_north_m']=list(self.mapping.cell_jezero(tuple(w['cell'])))
                w['latlon']=en_to_planet(*w['east_north_m'])
            from mission_explanations import explain
            result=payload['result']
            for item in result.get('alternatives') or [result['continuation'],result['returning']]:
                item['ui_diagnostic']=explain(self,config,item)
        return payload
