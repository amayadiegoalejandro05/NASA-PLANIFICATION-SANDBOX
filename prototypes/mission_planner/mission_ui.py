"""Bounded localhost UI transport. No search, consumption or decision logic here."""
from dataclasses import asdict, replace
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import hashlib
import json
import threading
import uuid

from mars_route_planner import Terrain
from mars_mission_resources import (ResourceAllocation, ExcludedResource, Mobility,
    MotionModel, ResourceMissionPlanner, small_example_profile)
from mission_api import LocalFrame, TerrainReference, _profile_data
from mission_decisions import (DecisionRequest, MissionState, PersonalCharacteristics,
    RateScenario, declared_provenance, compare_alternatives, evaluate_options)
from demo_stage04 import demo_profile, DEMO_WINDOW

ROOT = Path(__file__).resolve().parents[2]
WEB = Path(__file__).with_name('web')
MAX_LABELS = 5000


class UIInputError(ValueError):
    """Expected construction/transport errors, never an engine failure."""


def strict(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)


class MissionBridge:
    def __init__(self, data_folder=ROOT/'data/jezero'):
        from jezero_adapter import load_ctx_crop
        self.ctx = load_ctx_crop(data_folder, DEMO_WINDOW)
        n = 7
        risk = [[0.]*n for _ in range(n)]
        for c in (2, 3, 4):
            risk[3][c] = 1.
        self.synthetic = TerrainReference.capture(Terrain([[0.]*n for _ in range(n)],
            [[False]*n for _ in range(n)], risk, [[0.]*n for _ in range(n)], 1.), 'synthetic-penalty')

    def original(self, scenario):
        if scenario == 'ctx':
            return self.ctx.terrain, self.ctx.frame
        if scenario == 'synthetic':
            return self.synthetic, LocalFrame('SYNTHETIC_EAST_SOUTH', 1., (0., 0.))
        raise ValueError('Escenario de mapa desconocido')

    def defaults(self, scenario, agent):
        self.original(scenario)
        if agent not in ('astronaut', 'rover'):
            raise ValueError('Agente desconocido')
        p = demo_profile(agent) if scenario == 'ctx' else small_example_profile(agent)
        if scenario == 'synthetic':
            p = replace(p, resources={k: replace(v, capacity=100., reserve=1.) for k, v in p.resources.items()})
        return dict(map=scenario, agent=agent, profile=_profile_data(p),
            base=[4, 2] if scenario == 'ctx' else [3, 0],
            current=[3, 3] if scenario == 'ctx' else [3, 1],
            goal=[2, 4] if scenario == 'ctx' else [3, 5],
            activity_status='pending', activity_min=2. if scenario == 'ctx' else 1.,
            remaining={k: v.capacity for k, v in p.resources.items()},
            scenario='nominal', factor=1.2, max_labels=MAX_LABELS, obstacles=[],
            personal={'body_mass_kg': None, 'height_m': None})

    def terrain(self, config):
        original, frame = self.original(config['map'])
        t = original.snapshot
        obstacles = [list(row) for row in t.obstacles]
        cells = config['obstacles']
        if type(cells) is not list or len(cells) > t.rows*t.cols:
            raise ValueError('Lista de obstáculos simulados inválida')
        for cell in cells:
            self.check_cell(cell, t)
            obstacles[cell[0]][cell[1]] = True
        return TerrainReference.capture(Terrain(t.heights_m, obstacles, t.risk, t.roughness, t.resolution_m), original.terrain_id), frame

    @staticmethod
    def check_cell(cell, t):
        if (type(cell) is not list or len(cell) != 2 or any(type(v) is not int for v in cell)
                or not (0 <= cell[0] < t.rows and 0 <= cell[1] < t.cols)):
            raise ValueError(f'Celda fuera del mapa; filas 0–{t.rows-1}, columnas 0–{t.cols-1}')

    def profile(self, config):
        seed = self.defaults(config['map'], config['agent'])['profile']
        p = demo_profile(config['agent']) if config['map'] == 'ctx' else small_example_profile(config['agent'])
        raw = config['profile']
        resources = {}
        expected = {'time', 'battery'} | ({'oxygen', 'water', 'nutrition'} if config['agent'] == 'astronaut' else set())
        for k, v in raw['resources'].items():
            if k not in {'time', 'battery', 'oxygen', 'water', 'nutrition'} or v.get('status') not in {'modeled', 'excluded', 'not_applicable'}:
                raise ValueError('Recurso o tratamiento experimental desconocido')
            if k not in expected:
                if v.get('status') != 'not_applicable':
                    raise ValueError('Recursos humanos: No aplica en rover')
                continue
            resources[k] = (ExcludedResource(v['reason']) if v['status'] == 'excluded' else
                ResourceAllocation(**{a: v[a] for a in ('capacity', 'reserve', 'movement_rate', 'activity_rate')}))
        # IDs retain the pre-defined simulated profile; revision records every edit.
        return replace(p, profile_id=seed['profile_id'], version=seed['version'],
            mobility=Mobility(**raw['mobility']), motion=MotionModel(**raw['motion']), resources=resources)

    def build(self, config):
        terrain, frame = self.terrain(config)
        profile = self.profile(config)
        for k in ('base', 'current', 'goal'):
            self.check_cell(config[k], terrain.snapshot)
        limit = config['max_labels']
        if type(limit) is not int or not 1 <= limit <= MAX_LABELS:
            raise ValueError('Límite: entero entre 1 y 5000 etiquetas por búsqueda')
        state = MissionState.capture('local-simulated-mission', terrain, profile,
            tuple(config['base']), tuple(config['current']), tuple(config['goal']), config['activity_min'],
            completed=config['activity_status'] == 'completed', remaining=config['remaining'])
        if config['activity_status'] not in ('pending', 'completed'):
            raise ValueError('Estado de actividad inválido')
        factors = {k: (1. if k == 'time' or config['scenario'] == 'nominal' else config['factor']) for k in state.remaining}
        scenario = RateScenario(config['scenario'], factors, 'Sensibilidad simulada de tasas; no probabilidad ni peor caso integral')
        personal = PersonalCharacteristics(**config['personal']) if config['agent'] == 'astronaut' else None
        return DecisionRequest('5.0', str(uuid.uuid4()), terrain, frame, profile, state,
            declared_provenance(profile, 'simulated'), scenario, limit, personal)

    def map_data(self, name):
        terrain, frame = self.original(name)
        t = terrain.snapshot
        cells = []
        for r in range(t.rows):
            for c in range(t.cols):
                cell = (r, c)
                cells.append(dict(cell=cell, planner_xy_m=frame.waypoint(cell),
                    east_north_m=self.ctx.mapping.cell_jezero(cell) if name == 'ctx' else ((c+.5), -(r+.5)),
                    height_m=t.heights_m[r][c], risk=t.risk[r][c]))
        return dict(**terrain.identity(), cells=cells, frame=asdict(frame),
            provenance=self.ctx.provenance if name == 'ctx' else {'nature':'synthetic', 'description':'Retícula plana con penalización simulada central'},
            description='CTX nativo 20 m sobre retícula de 4 m; ventana [60:67,60:67], 28 × 28 m. Alturas absolutas CTX. Sin HiRISE.' if name == 'ctx' else
                'Escenario sintético 7 × 7 m, celdas de 1 m. Franja central con penalización simulada = 1.')

    def inspect(self, config, cell):
        try:
            terrain, _ = self.terrain(config)
            self.check_cell(cell, terrain.snapshot)
            profile = self.profile(config)
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            raise UIInputError(str(error)) from error
        nav = ResourceMissionPlanner.from_profile(terrain.snapshot, profile).nav
        return dict(traversable=nav.traversable(tuple(cell)), cell=cell,
                    message='Celda transitable' if nav.traversable(tuple(cell)) else 'Celda no transitable con la huella y movilidad actuales; selección rechazada')

    def calculate(self, config, action):
        if action not in ('compare', 'evaluate'):
            raise UIInputError('Acción desconocida')
        try:
            q = self.build(config)
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            raise UIInputError(str(error)) from error
        result = (compare_alternatives(q) if action == 'compare' else evaluate_options(q)).to_dict()
        records = result.get('alternatives') or [result['continuation'], result['returning']]
        waypoints = []
        for item in records:
            if not item['plan']:
                continue
            plan = item['plan']
            for i, cell in enumerate(plan['path']):
                cell = tuple(cell)
                waypoints.append(dict(policy=item['policy'], mode=item['mode'], index=i, cell=cell,
                    phase='inbound' if plan['goal_index'] is None or i > plan['goal_index'] else 'outbound',
                    planner_xy_m=q.frame.waypoint(cell),
                    east_north_m=self.ctx.mapping.cell_jezero(cell) if config['map'] == 'ctx' else (cell[1]+.5, -cell[0]-.5),
                    height_m=q.terrain.snapshot.heights_m[cell[0]][cell[1]]))
        # Invalid semantic requests cannot be serialized by q.to_dict(). Keep submitted config.
        request = q.to_dict() if all(x['status'] != 'INVALID_INPUT' for x in records) else None
        payload = dict(ui_schema='6.0', mission_schema='3.0', decision_schema='5.0',
            calculation_id=q.request_id, created_utc=datetime.now(timezone.utc).isoformat(), action=action,
            input_sha256=hashlib.sha256(strict(config).encode()).hexdigest(), configuration=config,
            preset_profile=self.defaults(config['map'], config['agent'])['profile'],
            request=request, result=result, waypoints=waypoints,
            terrain=q.terrain.identity(), provenance=self.map_data(config['map'])['provenance'],
            perturbations={'nature':'SIMULATED', 'obstacles':config['obstacles'], 'original_ctx_unchanged':True},
            units={'distance':'m', 'height':'m', 'time':'min', 'battery':'Wh', 'oxygen':'simulated_u', 'water':'L', 'nutrition':'kcal'},
            frames={'planner':asdict(q.frame), 'display':'JEZERO_LOCAL_EQUIRECTANGULAR_EAST_NORTH' if config['map']=='ctx' else 'SYNTHETIC_EAST_NORTH'})
        return json.loads(strict(payload))


def make_server(bridge, port=8766):
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def reply(self, code, value, kind='application/json; charset=utf-8'):
            payload = strict(value).encode() if kind.startswith('application/json') else value
            self.send_response(code)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; img-src 'self' blob: data: https://trek.nasa.gov; object-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(payload)

        def trusted(self):
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            return self.headers.get('Host') in allowed and self.headers.get('Origin', 'http://'+self.headers.get('Host', '')) in {'http://'+x for x in allowed}

        def do_GET(self):
            if not self.trusted():
                return self.reply(403, {'message':'Solo acceso local del mismo origen'})
            if self.path == '/api/catalog':
                if hasattr(bridge,'catalog'):
                    return self.reply(200, bridge.catalog())
                return self.reply(200, dict(maps={k:bridge.map_data(k) for k in ('ctx','synthetic')},
                    defaults={m:{a:bridge.defaults(m,a) for a in ('astronaut','rover')} for m in ('ctx','synthetic')}))
            if self.path in ('/regional-elevation.png','/regional-relief.png') and hasattr(bridge,'rasters'):
                return self.reply(200,bridge.rasters['elevation' if 'elevation' in self.path else 'relief'],'image/png')
            files = {'/':('index.html','text/html'), '/app.js':('app.js','text/javascript'), '/style.css':('style.css','text/css'),
                     '/map-app.js':('map-app.js','text/javascript'),'/map.css':('map.css','text/css'),
                     '/vendor/leaflet.js':('vendor/leaflet.js','text/javascript'),'/vendor/leaflet.css':('vendor/leaflet.css','text/css'),
                     '/legacy/':('legacy/index.html','text/html')}
            if self.path not in files:
                return self.reply(404, {'message':'Ruta desconocida'})
            file, kind = files[self.path]
            self.reply(200, (WEB/file).read_bytes(), kind+'; charset=utf-8')

        def do_POST(self):
            if not self.trusted():
                return self.reply(403, {'message':'Solo acceso local del mismo origen'})
            if self.path not in ('/api/calculate','/api/inspect','/api/select'):
                return self.reply(404, {'message':'Ruta desconocida'})
            if not lock.acquire(blocking=False):
                return self.reply(409, {'message':'Cálculo en curso; espere su resultado'})
            try:
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= 65536:
                        raise ValueError('Solicitud vacía o demasiado grande')
                    data = json.loads(self.rfile.read(size), parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Número no finito')))
                    config = data['configuration']
                    arg = data['action' if self.path.endswith('calculate') else 'point' if self.path.endswith('select') else 'cell']
                except (ValueError, TypeError, KeyError) as error:
                    raise UIInputError(str(error)) from error
                result = (bridge.calculate(config, arg) if self.path.endswith('calculate') else
                          bridge.select(config,arg) if self.path.endswith('select') and hasattr(bridge,'select') else bridge.inspect(config, arg))
                self.reply(200, result)
            except UIInputError as error:
                self.reply(400, dict(status='INVALID_INPUT', reason_code='UI_CONSTRUCTION_OR_VALIDATION', message=str(error)))
            except Exception:
                import traceback
                traceback.print_exc()
                self.reply(500, dict(status='INTERNAL_ERROR', message='Error interno; consulte la consola. No hay resultado válido.'))
            finally:
                lock.release()

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args()
    from expanded_ui import ExpandedBridge
    server = make_server(ExpandedBridge(), args.port)
    print(f'Mission Planner: http://127.0.0.1:{server.server_port} — detener con Ctrl+C', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    # RegionalBridge imports this module. Preserve one exception/class identity
    # when this very file is the executable entrypoint rather than an import.
    import sys
    sys.modules.setdefault('mission_ui', sys.modules[__name__])
    main()
