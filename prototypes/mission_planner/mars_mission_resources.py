"""MARS GOD'S EYE: planificador experimental de mision con recursos.

Complementa mars_route_planner.py (A* con DEM, riesgos y obstaculos).
Calcula IDA -> actividad cientifica -> REGRESO a base en una sola
busqueda con restricciones duras por recurso y reservas.

Todos los perfiles son HIPOTETICOS. No usar para planificacion EVA real.
Python 3.10+, sin dependencias externas.

Ejecutar: python mars_mission_resources.py
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping
import heapq
import itertools
import math
from typing import Optional

from mars_route_planner import (
    Cell, NoSafeRouteError, PlannerConfig, RiskAwareAStar, Terrain, synthetic_terrain
)


@dataclass(frozen=True)
class Usage:
    """Acumulado de recursos consumidos. O2 en UNIDADES SIMULADAS."""
    minutes: float = 0.0
    oxygen_u: float = 0.0
    water_l: float = 0.0
    battery_wh: float = 0.0
    nutrition_kcal: float = 0.0
    distance_m: float = 0.0

    def __add__(self, other: 'Usage') -> 'Usage':
        return Usage(*(a + b for a, b in zip(self.values(), other.values())))

    def values(self) -> tuple[float, ...]:
        return (self.minutes, self.oxygen_u, self.water_l,
                self.battery_wh, self.nutrition_kcal, self.distance_m)


@dataclass(frozen=True)
class Budget:
    """Disponibilidad total; cada reserva se debe conservar al terminar.

    None significa que ese recurso NO SE MODELA (no significa infinito real).
    Nutrition se refiere a demanda metabolica estimada, no a una necesidad
    fisiologica de ingerir toda la energia durante una EVA corta.
    """
    time_min: float
    time_reserve_min: float
    oxygen_u: Optional[float] = None
    oxygen_reserve_u: float = 0.0
    water_l: Optional[float] = None
    water_reserve_l: float = 0.0
    battery_wh: Optional[float] = None
    battery_reserve_wh: float = 0.0
    nutrition_kcal: Optional[float] = None
    nutrition_reserve_kcal: float = 0.0

    def __post_init__(self) -> None:
        pairs = [(self.time_min, self.time_reserve_min),
                 (self.oxygen_u, self.oxygen_reserve_u),
                 (self.water_l, self.water_reserve_l),
                 (self.battery_wh, self.battery_reserve_wh),
                 (self.nutrition_kcal, self.nutrition_reserve_kcal)]
        for capacity, reserve in pairs:
            if not math.isfinite(reserve) or reserve < 0:
                raise ValueError('Reserva invalida')
            if capacity is not None and (not math.isfinite(capacity) or
                                          capacity < reserve):
                raise ValueError('La capacidad debe alcanzar la reserva')

    def fits(self, used: Usage) -> bool:
        return (used.minutes <= self.time_min - self.time_reserve_min + 1e-9
                and all(cap is None or qty <= cap - reserve + 1e-9
                        for cap, reserve, qty in (
                            (self.oxygen_u, self.oxygen_reserve_u, used.oxygen_u),
                            (self.water_l, self.water_reserve_l, used.water_l),
                            (self.battery_wh, self.battery_reserve_wh, used.battery_wh),
                            (self.nutrition_kcal, self.nutrition_reserve_kcal,
                             used.nutrition_kcal))))


@dataclass(frozen=True)
class Consumption:
    """Modelo parametrico simplificado; NO esta calibrado para Marte ni EVA."""
    speed_m_per_min: float
    oxygen_u_per_min: float = 0.0
    water_l_per_min: float = 0.0
    battery_wh_per_min: float = 0.0
    nutrition_kcal_per_min: float = 0.0
    # Penalizaciones no negativas; pendiente ascendente y rugosidad reducen velocidad
    uphill_speed_penalty: float = 2.0
    roughness_speed_penalty: float = 0.5
    uphill_effort_penalty: float = 2.0
    climb_battery_wh_per_m: float = 0.0
    hazard_cost_weight: float = 2.0
    battery_cost_weight: float = 0.01

    def __post_init__(self) -> None:
        if not math.isfinite(self.speed_m_per_min) or self.speed_m_per_min <= 0:
            raise ValueError('La velocidad debe ser positiva')
        for value in (self.oxygen_u_per_min, self.water_l_per_min,
                      self.battery_wh_per_min, self.nutrition_kcal_per_min,
                      self.uphill_speed_penalty, self.roughness_speed_penalty,
                      self.uphill_effort_penalty, self.climb_battery_wh_per_m,
                      self.hazard_cost_weight, self.battery_cost_weight):
            if not math.isfinite(value) or value < 0:
                raise ValueError('Los coeficientes deben ser finitos y >= 0')

    def stationary(self, minutes: float) -> Usage:
        if not math.isfinite(minutes) or minutes < 0:
            raise ValueError('Duracion de actividad invalida')
        return Usage(minutes, self.oxygen_u_per_min * minutes,
                     self.water_l_per_min * minutes,
                     self.battery_wh_per_min * minutes,
                     self.nutrition_kcal_per_min * minutes, 0.0)

    def traveling(self, distance_m: float, rise_m: float,
                  roughness: float) -> Usage:
        uphill_grade = max(0.0, rise_m) / distance_m
        minutes = (distance_m / self.speed_m_per_min *
                   (1.0 + self.uphill_speed_penalty * uphill_grade +
                    self.roughness_speed_penalty * roughness))
        effort = 1.0 + self.uphill_effort_penalty * uphill_grade
        return Usage(minutes, minutes * self.oxygen_u_per_min * effort,
                     minutes * self.water_l_per_min * effort,
                     minutes * self.battery_wh_per_min +
                     max(0.0, rise_m) * self.climb_battery_wh_per_m,
                     minutes * self.nutrition_kcal_per_min * effort,
                     distance_m)


RESOURCE_UNITS = MappingProxyType(dict(time="min", battery="Wh", oxygen="simulated_u",
                                      water="L", nutrition="kcal"))
HUMAN_RESOURCES = frozenset(("oxygen", "water", "nutrition"))


def _text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} debe ser texto no vacio")


@dataclass(frozen=True)
class ResourceAllocation:
    """Capacity/reserve in RESOURCE_UNITS; rates in those units per minute.

    Time rates must both be 1. Zero rates still describe a modeled resource.
    """
    capacity: float
    reserve: float
    movement_rate: float
    activity_rate: float

    def __post_init__(self):
        for value in (self.capacity, self.reserve, self.movement_rate, self.activity_rate):
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError("Capacidad, reserva y tasas deben ser finitas y >= 0")
        if self.reserve > self.capacity:
            raise ValueError("La reserva supera la capacidad")


@dataclass(frozen=True)
class ExcludedResource:
    """Applicable human resource explicitly omitted from an experiment.

    No capacity, reserve or rates can accompany this variant.
    """
    reason: str

    def __post_init__(self):
        _text(self.reason, "reason")


@dataclass(frozen=True)
class Mobility:
    agent_radius_m: float = .12
    safety_margin_m: float = .08
    max_slope_deg: float = 18.
    near_obstacle_m: float = .60
    slope_weight: float = 3.
    risk_weight: float = 2.
    roughness_weight: float = 1.5
    proximity_weight: float = .8

    def __post_init__(self):
        self.to_config()  # Same geometry and validation as stage 1.

    def to_config(self):
        return PlannerConfig(self.max_slope_deg, self.agent_radius_m,
                             self.safety_margin_m, self.near_obstacle_m,
                             self.slope_weight, self.risk_weight,
                             self.roughness_weight, self.proximity_weight)


@dataclass(frozen=True)
class MotionModel:
    speed_m_per_min: float
    uphill_speed_penalty: float = 2.
    roughness_speed_penalty: float = .5
    uphill_effort_penalty: float = 2.
    climb_battery_wh_per_m: float = 0.
    hazard_cost_weight: float = 2.
    battery_cost_weight: float = .01

    def __post_init__(self):
        Consumption(**vars(self))


@dataclass(frozen=True)
class AgentProfile:
    """Closed discriminated contract: astronaut or rover, no plugin hierarchy.

    All parameters require provenance/nature/limitations metadata. Human resources
    are absent (not applicable) for rover, never silently interpreted as zero.
    """
    agent_type: str
    profile_id: str
    version: str
    parameter_nature: str
    provenance: str
    limitations: str
    mobility: Mobility
    motion: MotionModel
    resources: Mapping[str, ResourceAllocation | ExcludedResource]

    def __post_init__(self):
        if self.agent_type not in ("astronaut", "rover"):
            raise ValueError("agent_type debe ser astronaut o rover")
        for name in ("profile_id", "version", "parameter_nature", "provenance", "limitations"):
            _text(getattr(self, name), name)
        if type(self.mobility) is not Mobility or type(self.motion) is not MotionModel:
            raise ValueError("mobility y motion requieren sus contratos tipados")
        resources = dict(self.resources)
        required = {"time", "battery"} | (HUMAN_RESOURCES if self.agent_type == "astronaut" else set())
        if set(resources) != required:
            raise ValueError(f"Recursos obligatorios/exclusivos para {self.agent_type}: {sorted(required)}")
        for name, allocation in resources.items():
            if type(allocation) is ExcludedResource and name in HUMAN_RESOURCES:
                continue
            if type(allocation) is not ResourceAllocation:
                raise ValueError(f"{name} requiere presupuesto; solo recursos humanos admiten exclusion")
            if name == "time" and (allocation.movement_rate != 1 or allocation.activity_rate != 1):
                raise ValueError("El tiempo transcurre a tasa 1 en ambas fases")
        object.__setattr__(self, "resources", MappingProxyType(resources))

    def resource_status(self, name: str) -> str:
        if name not in RESOURCE_UNITS:
            raise ValueError("Recurso desconocido")
        if name not in self.resources:
            return "not_applicable"
        return "excluded" if isinstance(self.resources[name], ExcludedResource) else "modeled"

    def _engine_inputs(self):
        def allocation(name):
            item = self.resources.get(name)
            return item if isinstance(item, ResourceAllocation) else None
        names = dict(time=("time_min", "time_reserve_min"),
                     battery=("battery_wh", "battery_reserve_wh"),
                     oxygen=("oxygen_u", "oxygen_reserve_u"),
                     water=("water_l", "water_reserve_l"),
                     nutrition=("nutrition_kcal", "nutrition_reserve_kcal"))
        budget = {}
        rates = [{}, {}]
        rate_names = dict(battery="battery_wh_per_min", oxygen="oxygen_u_per_min",
                          water="water_l_per_min", nutrition="nutrition_kcal_per_min")
        for name, (cap, reserve) in names.items():
            item = allocation(name)
            if item:
                budget.update({cap: item.capacity, reserve: item.reserve})
                if name != "time":
                    rates[0][rate_names[name]] = item.movement_rate
                    rates[1][rate_names[name]] = item.activity_rate
        return (self.mobility.to_config(), Consumption(**vars(self.motion), **rates[0]),
                Budget(**budget), Consumption(speed_m_per_min=1, **rates[1]))


@dataclass
class _Label:
    cell: Cell
    visited_goal: bool
    used: Usage
    cost: float
    previous: Optional[int]
    active: bool = True


@dataclass(frozen=True)
class MissionPlan:
    path: tuple[Cell, ...]
    goal_index: int
    total: Usage
    cost: float
    explored_labels: int

    @property
    def outbound(self) -> tuple[Cell, ...]:
        return self.path[:self.goal_index + 1]

    @property
    def inbound(self) -> tuple[Cell, ...]:
        return self.path[self.goal_index:]


class NoFeasibleMissionError(NoSafeRouteError):
    """No se puede completar ida, actividad y regreso respetando reservas."""


class SearchLimitReachedError(Exception):
    """Search interrupted; feasibility is undetermined."""
    def __init__(self, limit: int, generated_labels: int):
        self.limit = limit
        self.generated_labels = generated_labels
        super().__init__(f'max_labels={limit}; etiquetas generadas={generated_labels}; '
                         'busqueda interrumpida; factibilidad no determinada')


class ResourceMissionPlanner:
    MOVES = RiskAwareAStar.MOVES

    def __init__(self, terrain: Terrain, terrain_config: PlannerConfig,
                 consumption: Consumption, budget: Budget):
        self.nav = RiskAwareAStar(terrain, terrain_config)
        self.consumption = consumption
        self.budget = budget
        self.activity_consumption = consumption
        self.profile = None

    @classmethod
    def from_profile(cls, terrain: Terrain, profile: AgentProfile):
        if type(profile) is not AgentProfile:
            raise ValueError("Se requiere AgentProfile validado")
        config, movement, budget, activity = profile._engine_inputs()
        planner = cls(terrain, config, movement, budget)
        planner.activity_consumption = activity
        planner.profile = profile
        return planner

    @staticmethod
    def _dominates(a: _Label, b: _Label) -> bool:
        # Etiquetas con igual posicion/estado; comparar costo y TODOS los recursos
        # que representan restricciones (la distancia no es una restriccion dura).
        ua, ub = a.used, b.used
        return (a.cost <= b.cost + 1e-9 and
                ua.minutes <= ub.minutes + 1e-9 and
                ua.oxygen_u <= ub.oxygen_u + 1e-9 and
                ua.water_l <= ub.water_l + 1e-9 and
                ua.battery_wh <= ub.battery_wh + 1e-9 and
                ua.nutrition_kcal <= ub.nutrition_kcal + 1e-9)

    def movement_usage(self, a: Cell, b: Cell, distance: float) -> Usage:
        """Consumption on an admitted edge, from this planner's snapshot only."""
        za = self.nav.t.heights_m[a[0]][a[1]]
        zb = self.nav.t.heights_m[b[0]][b[1]]
        assert za is not None and zb is not None
        roughness = (self.nav.t.roughness[a[0]][a[1]] +
                     self.nav.t.roughness[b[0]][b[1]]) / 2
        return self.consumption.traveling(distance, zb - za, roughness)

    def plan(self, start: Cell, goal: Cell, activity_min: float = 0.0,
             max_labels: int = 120_000, *, base: Cell | None = None,
             return_only: bool = False, activity_completed: bool = False) -> MissionPlan:
        # Stage 5: same label search, explicit terminal base and initial service.
        # Omitting base preserves the legacy round-trip contract (including its
        # start == goal rejection). return_only ignores the science destination.
        legacy = base is None
        base = start if legacy else base
        if type(return_only) is not bool or type(activity_completed) is not bool:
            raise ValueError('Los modos deben ser bool')
        # Cap on stored/generated labels, including initial and inactive labels.
        # Exactly N labels may be processed; interrupt before inserting N+1.
        if type(max_labels) is not int or max_labels <= 0:
            raise ValueError('max_labels debe ser un entero positivo')
        if not math.isfinite(activity_min) or activity_min < 0:
            raise ValueError('activity_min debe ser finito y >= 0')
        if (not self.nav.traversable(start) or not self.nav.traversable(base)
                or (not return_only and not self.nav.traversable(goal))):
            raise NoFeasibleMissionError('Base u objetivo no transitables')
        if legacy and start == goal:
            raise ValueError('La base y el objetivo deben ser diferentes en esta V1')

        visited = return_only or start == goal
        initial = (self.activity_consumption.stationary(activity_min)
                   if visited and not return_only and not activity_completed else Usage())
        if not self.budget.fits(initial):
            raise NoFeasibleMissionError('Recursos iniciales insuficientes con reservas')
        initial_cost = initial.minutes + self.consumption.battery_cost_weight * initial.battery_wh
        labels = [_Label(start, visited, initial, initial_cost, None)]
        frontier: dict[tuple[Cell, bool], list[int]] = {(start, visited): [0]}
        sequence = itertools.count()
        heap = [(initial_cost, next(sequence), 0)]
        while heap:
            _, _, i = heapq.heappop(heap)
            curr = labels[i]
            if not curr.active:
                continue
            if curr.cell == base and curr.visited_goal:
                path_rev: list[Cell] = []
                index: Optional[int] = i
                while index is not None:
                    path_rev.append(labels[index].cell)
                    index = labels[index].previous
                path = tuple(reversed(path_rev))
                return MissionPlan(path, 0 if return_only else path.index(goal), curr.used,
                                   curr.cost, len(labels))

            r, c = curr.cell
            for dr, dc in self.MOVES:
                nb = (r + dr, c + dc)
                edge = self.nav._edge(curr.cell, nb)
                if edge is None:
                    continue
                edge_cost, distance, _ = edge
                movement = self.movement_usage(curr.cell, nb, distance)
                visits = curr.visited_goal or nb == goal
                service = (self.activity_consumption.stationary(activity_min)
                           if nb == goal and not curr.visited_goal and not activity_completed else Usage())
                new_usage = curr.used + movement + service
                if not self.budget.fits(new_usage):
                    continue
                hazard_factor = max(0.0, edge_cost / distance - 1.0)
                new_cost = (curr.cost + movement.minutes *
                            (1 + self.consumption.hazard_cost_weight * hazard_factor) +
                            service.minutes +
                            self.consumption.battery_cost_weight *
                            (movement.battery_wh + service.battery_wh))
                new = _Label(nb, visits, new_usage, new_cost, i)
                key = (nb, visits)
                active_here = frontier.get(key, [])
                if any(self._dominates(labels[j], new) for j in active_here):
                    continue
                if len(labels) == max_labels:
                    raise SearchLimitReachedError(max_labels, len(labels))
                survivors = []
                for j in active_here:
                    if self._dominates(new, labels[j]):
                        labels[j].active = False
                    else:
                        survivors.append(j)
                new_idx = len(labels)
                labels.append(new)
                survivors.append(new_idx)
                frontier[key] = survivors
                heapq.heappush(heap, (new_cost, next(sequence), new_idx))
        raise NoFeasibleMissionError(
            'No existe mision completa con ida, actividad, regreso y reservas')


def astronaut_demo() -> MissionPlan:
    # Terreno y cifras SINTETICOS. Oxigeno u = unidades simuladas sin conversion
    # a presion, volumen ni masa de un sistema real de soporte vital.
    t = synthetic_terrain()
    t.resolution_m = 20.0  # 20 metros/celda; escenario ilustrativo de 600 m
    profile = AgentProfile("astronaut", "sim-astronaut-large", "2.0", "simulated",
        "Supuestos configurables heredados del prototipo; sin calibracion",
        "No valida fisiologia ni seguridad EVA", Mobility(.4, .3, 18., 25.),
        MotionModel(30.), dict(time=ResourceAllocation(120, 20, 1, 1),
        oxygen=ResourceAllocation(30, 6, .25, .25),
        water=ResourceAllocation(1.2, .2, .004, .004),
        battery=ResourceAllocation(120, 25, .7, .7),
        nutrition=ResourceAllocation(420, 40, 4, 4)))
    planner = ResourceMissionPlanner.from_profile(t, profile)
    return planner.plan((8, 2), (8, 27), activity_min=12)


def rover_demo() -> MissionPlan:
    t = synthetic_terrain()
    profile = AgentProfile("rover", "sim-rover-large", "2.0", "simulated",
        "Supuestos configurables heredados del prototipo; sin calibracion",
        "No valida mecanica ni autonomia real", Mobility(),
        MotionModel(.15, climb_battery_wh_per_m=.5),
        dict(time=ResourceAllocation(180, 20, 1, 1),
             battery=ResourceAllocation(180, 25, .9, .9)))
    planner = ResourceMissionPlanner.from_profile(t, profile)
    return planner.plan((8, 2), (8, 27), activity_min=5)


def small_example_profile(agent_type: str) -> AgentProfile:
    """Entire parameter set is hypothetical and configurable, not calibrated."""
    resources = dict(time=ResourceAllocation(8, 1, 1, 1),
                     battery=ResourceAllocation(19, 1, 2, 5))
    if agent_type == "astronaut":
        resources.update(oxygen=ResourceAllocation(11, 1, 1, 3),
                         water=ResourceAllocation(2, .2, .1, .4),
                         nutrition=ResourceAllocation(29, 1, 4, 6))
    return AgentProfile(agent_type, f"sim-{agent_type}-small", "2.0", "simulated",
                        "Conjunto hipotetico configurable para pruebas aritmeticas",
                        "Sin calibracion fisiologica/mecanica; no certifica EVA",
                        Mobility(0, 0, near_obstacle_m=0, proximity_weight=0),
                        MotionModel(1), resources)


def small_demo(agent_type: str) -> MissionPlan:
    terrain = Terrain([[0., 0., 0.]], [[False] * 3], [[0.] * 3], [[0.] * 3], 1.)
    return ResourceMissionPlanner.from_profile(terrain, small_example_profile(agent_type)).plan(
        (0, 0), (0, 2), activity_min=2)


def main() -> None:
    for label, factory in [('ASTRONAUTA', astronaut_demo), ('ROVER', rover_demo),
                           ('ASTRONAUTA PEQUENO', lambda: small_demo('astronaut')),
                           ('ROVER PEQUENO', lambda: small_demo('rover'))]:
        try:
            p = factory()
        except SearchLimitReachedError as e:
            print(f'{label}: BUSQUEDA INTERRUMPIDA; FACTIBILIDAD NO DETERMINADA: {e}')
            continue
        except NoFeasibleMissionError as e:
            print(f'{label}: MISION RECHAZADA: {e}')
            continue
        print(f'\n{label}: MISION FACTIBLE (escenario sintetico)')
        print(f'  Distancia ida + regreso: {p.total.distance_m:.1f} m')
        print(f'  Tiempo total con actividad: {p.total.minutes:.1f} min')
        print(f'  O2 simulado: {p.total.oxygen_u:.2f} u')
        print(f'  Agua estimada: {p.total.water_l:.3f} L')
        print(f'  Bateria estimada: {p.total.battery_wh:.1f} Wh')
        print(f'  Demanda calorica estimada: {p.total.nutrition_kcal:.0f} kcal')
        print(f'  Tramos: ida {len(p.outbound)} celdas, '
              f'regreso {len(p.inbound)} celdas')
        print(f'  Etiquetas exploradas: {p.explored_labels}')


if __name__ == '__main__':
    main()
