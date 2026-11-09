"""UI explanations only; never changes a plan, status or recommendation.

An optimistic resource bound uses the ENGINE's Consumption and _resources.
Straight distances are bounds, never paths or guarantees of traversability.
"""
import math
from mars_mission_resources import ResourceMissionPlanner, Usage
from mission_api import _resources

NAMES={'time':'tiempo','battery':'batería','oxygen':'oxígeno simulado','water':'agua','nutrition':'demanda energética'}


def explain(bridge, config, item):
    status, reason = item['status'], item['reason_code']
    if status=='SUCCESS':
        return None
    if status=='SEARCH_LIMIT_REACHED':
        return dict(kind='INTERRUPTED', summary='La búsqueda detallada se interrumpió; todavía no sabemos si esta misión es posible.',
                    next_step='Prueba un destino más cercano o revisa los obstáculos. La interrupción no significa que falten recursos ni que no exista un camino.')
    if status=='INVALID_INPUT':
        return dict(kind='INVALID',summary='Hay datos de misión que deben corregirse.',next_step=item['message'])
    if reason=='BALANCE_BELOW_RESERVE':
        bad=[NAMES.get(k,k) for k,v in config['remaining'].items() if v<config['profile']['resources'][k]['reserve']]
        return dict(kind='BALANCE_BELOW_RESERVE',summary='El saldo actual es menor que la reserva obligatoria de '+', '.join(bad)+'.',
                    next_step='Revisa los saldos y reservas declarados. El motor conserva la reserva absoluta; no la reduce automáticamente.')
    for prefix,key,label in [('GOAL','goal','El destino'),('CURRENT','current','La posición actual'),('BASE','base','La salida/base')]:
        if reason.startswith(prefix+'_'):
            direct=config[key] in config['obstacles']
            if direct:
                return dict(kind='POINT_ON_SIMULATED_OBSTACLE',summary=label+' coincide con un obstáculo simulado.',
                            next_step='Retira ese obstáculo o marca otro punto. No se mueve el punto automáticamente a una celda libre.',cell=config[key])
            return dict(kind='POINT_NOT_TRAVERSABLE',summary=label+' no es transitable con el terreno y la movilidad configurados.',
                        next_step='Consulta ese punto y revisa obstáculos cercanos, huella y pendiente. Prueba otra posición; no se garantiza que toda celda del cuadro sea transitable.',cell=config[key])
    # Effective rates/capacities already come from mission_decisions, including
    # scenario factors and current balances. No rate or history adaptation here.
    effective=item.get('effective_profile')
    if reason=='SEARCH_EXHAUSTED' and effective:
        profile=bridge.profile(dict(config,profile=effective))
        terrain,frame=bridge.terrain(config)
        planner=ResourceMissionPlanner.from_profile(terrain.snapshot,profile)
        xy=lambda k:frame.waypoint(tuple(config[k]))
        if item['mode']=='return':
            distance=math.dist(xy('current'),xy('base'));activity=0.
        else:
            distance=math.dist(xy('current'),xy('goal'))+math.dist(xy('goal'),xy('base'))
            activity=config['activity_min'] if config['activity_status']=='pending' else 0.
        minimum=(planner.consumption.traveling(distance,0.,0.) if distance>0 else Usage())+planner.activity_consumption.stationary(activity)
        quantities=_resources(profile,minimum)
        deficits=[dict(resource=k,name=NAMES[k],unit=v['unit'],minimum_consumption=v['consumed'],
                       available_above_reserve=v['capacity']-v['reserve'],minimum_shortfall=-v['margin_above_reserve'])
                  for k,v in quantities.items() if v['status']=='modeled' and v['margin_above_reserve'] < -1e-9]
        if deficits:
            return dict(kind='RESOURCE_LOWER_BOUND_EXCEEDED',summary='Los recursos no alcanzan para el recorrido completo, la actividad y las reservas, incluso sin desvíos.',
                        next_step='Acerca el destino o reduce la actividad pendiente. Si los saldos reales son otros, edítalos en Recursos y reservas; no se aumentan automáticamente.',
                        minimum_future_distance_m=distance,resources=deficits,
                        scope='Mínimo optimista con las funciones de consumo del motor: distancia directa, sin ascensos, rugosidad ni obstáculos. No es una ruta calculada; los desvíos pueden consumir más.')
    return dict(kind='NO_ADMISSIBLE_PLAN',summary='No se encontró un recorrido completo que respete movilidad, recursos y reservas.',
                next_step='Hay '+str(len(config['obstacles']))+' obstáculos simulados. Puedes retirarlos y recalcular para comparar, acercar el destino o revisar recursos. El motor no identifica una causa única en este caso.')
