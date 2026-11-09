"""Geometric A* candidate; resource accounting remains in the original engine."""
from datetime import datetime,timezone
from dataclasses import asdict
from types import SimpleNamespace
import hashlib
from mars_route_planner import NoSafeRouteError,RouteSearchLimitReachedError
from mars_mission_resources import ResourceMissionPlanner,Usage,MissionPlan
from mission_decisions import effective_future_profile
from mission_api import _breakdown,_profile_data
from mission_ui import strict,UIInputError
from jezero_map import en_to_planet


def fast_calculate(bridge,config):
    try:q=bridge.build(config);q.validate()
    except (ValueError,TypeError,KeyError) as e:raise UIInputError(str(e)) from e
    s=q.state
    a=dict(schema_version='5.0',policy='geometric_astar',mode='continue',status=None,reason_code=None,message=None,
           request=q.to_dict(),effective_profile=None,plan=None,
           search_metrics={'generated_labels':None,'max_expansions_per_leg':5000,
                           'meaning':'Geometric A* expansion cap per leg; detailed max_labels does not control this search'},ui_diagnostic=None)
    candidate=None
    if any(s.remaining[k]<s.reserves[k] for k in s.remaining):
        a.update(status='INFEASIBLE',reason_code='BALANCE_BELOW_RESERVE',message='Un saldo es menor que su reserva. Corrígelo antes de buscar.')
    else:
        profile=effective_future_profile(q)
        a['effective_profile']=_profile_data(profile)
        planner=ResourceMissionPlanner.from_profile(q.terrain.snapshot,profile)
        try:
            out=planner.nav.plan(s.current,s.goal,max_expansions=5000)
            back=planner.nav.plan(s.goal,s.original_base,max_expansions=5000)
            path=tuple(out.cells)+tuple(back.cells[1:]);goal_index=len(out.cells)-1;total=Usage()
            for x,y in zip(path,path[1:]):total=total+planner.movement_usage(x,y,planner.nav._edge(x,y)[1])
            pending=s.activity_status=='pending'
            if pending:total=total+planner.activity_consumption.stationary(s.pending_activity_min)
            plan=MissionPlan(path,goal_index,total,out.total_cost+back.total_cost,0)
            proxy=SimpleNamespace(profile=profile,activity_min=s.pending_activity_min,goal=s.goal,base=s.original_base,frame=q.frame)
            candidate=_breakdown(proxy,planner,plan,include_activity=pending)
            candidate['cost_objective']='Geometric terrain-weighted A* cost, not multiresource cost'
            fits=planner.budget.fits(total)
            a.update(status='SUCCESS' if fits else 'INFEASIBLE',reason_code='FAST_ROUTE_FITS' if fits else 'FAST_ROUTE_NEEDS_RESOURCES',
                     message='Recorrido comprobado con ida, actividad, regreso y reservas.' if fits else 'Encontré un recorrido transitable. Faltan recursos para completarlo con las reservas.')
            a['mission_conditions']=dict(kind='MEASURED_CANDIDATE',message='Recursos del recorrido completo encontrado, incluyendo pendientes, desvíos y reservas.',
                resources=[dict(resource=k,unit=v['unit'],required_initial=v['consumed']+v['reserve'],current_initial=v['capacity'],satisfied=v['margin_above_reserve']>=-1e-9)
                           for k,v in candidate['total']['resources'].items() if v['status']=='modeled'])
            if fits:a['plan']=candidate
            else:a['ui_diagnostic']=dict(kind='CANDIDATE_BUDGET',summary=a['message'],next_step='Pulsa «Preparar recursos para este recorrido». Se conserva el terreno y se verifica otra vez; estos recursos pertenecen a un recorrido completo, no a una línea recta.')
        except RouteSearchLimitReachedError:
            a.update(status='SEARCH_LIMIT_REACHED',reason_code='GEOMETRIC_LIMIT',message='La búsqueda se interrumpió; todavía no sabemos si hay un recorrido. Acerca los puntos o revisa obstáculos.')
        except NoSafeRouteError:
            a.update(status='INFEASIBLE',reason_code='NO_GEOMETRIC_ROUTE',message='El terreno, los obstáculos o la movilidad impiden unir esos puntos. Aumentar recursos no elimina este bloqueo.')
    if a['status']!='SUCCESS' and not a['ui_diagnostic']:
        a['ui_diagnostic']=dict(kind=a['reason_code'],summary=a['message'],next_step='Revisa puntos y obstáculos. Los ajustes avanzados permiten cambiar la movilidad declarada.')
    result=dict(schema_version='5.0',alternatives=[a],recommendation='geometric_astar' if a['plan'] else None,
                distinct_successful_routes=1 if a['plan'] else 0,coincident_routes=[['geometric_astar']] if a['plan'] else [],
                rule='A* geométrico; consumos comprobados después. No busca el óptimo multirrecurso. Un presupuesto insuficiente rechaza este recorrido, no todos los posibles.')
    waypoints=[]
    if a['plan']:
        for i,cell in enumerate(a['plan']['path']):
            en=list(bridge.mapping.cell_jezero(tuple(cell)))
            waypoints.append(dict(index=i,cell=cell,policy='geometric_astar',mode='continue',east_north_m=en,latlon=en_to_planet(*en),
                                  planner_xy_m=q.frame.waypoint(tuple(cell)),height_m=q.terrain.snapshot.heights_m[cell[0]][cell[1]]))
    return dict(ui_schema='6.1',planning_method='geometric_astar',mission_schema='3.0',decision_schema='5.0',
                calculation_id=q.request_id,created_utc=datetime.now(timezone.utc).isoformat(),configuration=config,
                input_sha256=hashlib.sha256(strict(config).encode()).hexdigest(),request=q.to_dict(),result=result,
                candidate_plan=candidate,waypoints=waypoints,terrain=q.terrain.identity(),provenance=bridge.region_provenance,
                frames={'planner':asdict(q.frame),'display':'MARS_PLANETOCENTRIC_LATITUDE_EAST_LONGITUDE'},
                units={'distance':'m','time':'min','battery':'Wh','oxygen':'simulated_u','water':'L','nutrition':'kcal'},
                perturbations={'nature':'SIMULATED','obstacles':config['obstacles']})
