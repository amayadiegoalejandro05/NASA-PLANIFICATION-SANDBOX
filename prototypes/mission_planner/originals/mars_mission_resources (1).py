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


class ResourceMissionPlanner:
    MOVES = RiskAwareAStar.MOVES

    def __init__(self, terrain: Terrain, terrain_config: PlannerConfig,
                 consumption: Consumption, budget: Budget):
        self.nav = RiskAwareAStar(terrain, terrain_config)
        self.consumption = consumption
        self.budget = budget

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

    def plan(self, start: Cell, goal: Cell, activity_min: float = 0.0,
             max_labels: int = 120_000) -> MissionPlan:
        if not math.isfinite(activity_min) or activity_min < 0:
            raise ValueError('activity_min debe ser finito y >= 0')
        if not self.nav.traversable(start) or not self.nav.traversable(goal):
            raise NoFeasibleMissionError('Base u objetivo no transitables')
        if start == goal:
            raise ValueError('La base y el objetivo deben ser diferentes en esta V1')
        if max_labels <= 0:
            raise ValueError('max_labels debe ser positivo')

        labels = [_Label(start, False, Usage(), 0.0, None)]
        frontier: dict[tuple[Cell, bool], list[int]] = {(start, False): [0]}
        sequence = itertools.count()
        heap = [(0.0, next(sequence), 0)]
        while heap:
            _, _, i = heapq.heappop(heap)
            curr = labels[i]
            if not curr.active:
                continue
            if curr.cell == start and curr.visited_goal:
                path_rev: list[Cell] = []
                index: Optional[int] = i
                while index is not None:
                    path_rev.append(labels[index].cell)
                    index = labels[index].previous
                path = tuple(reversed(path_rev))
                return MissionPlan(path, path.index(goal), curr.used,
                                   curr.cost, len(labels))

            r, c = curr.cell
            for dr, dc in self.MOVES:
                nb = (r + dr, c + dc)
                edge = self.nav._edge(curr.cell, nb)
                if edge is None:
                    continue
                edge_cost, distance, _ = edge
                za = self.nav.t.heights_m[r][c]
                zb = self.nav.t.heights_m[nb[0]][nb[1]]
                assert za is not None and zb is not None
                roughness = (self.nav.t.roughness[r][c] +
                             self.nav.t.roughness[nb[0]][nb[1]]) / 2
                movement = self.consumption.traveling(distance, zb - za, roughness)
                visits = curr.visited_goal or nb == goal
                service = (self.consumption.stationary(activity_min)
                           if nb == goal and not curr.visited_goal else Usage())
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
                if len(labels) >= max_labels:
                    raise NoFeasibleMissionError(
                        'Busqueda demasiado grande; reducir mapa o limites')
        raise NoFeasibleMissionError(
            'No existe mision completa con ida, actividad, regreso y reservas')


def astronaut_demo() -> MissionPlan:
    # Terreno y cifras SINTETICOS. Oxigeno u = unidades simuladas sin conversion
    # a presion, volumen ni masa de un sistema real de soporte vital.
    t = synthetic_terrain()
    t.resolution_m = 20.0  # 20 metros/celda; escenario ilustrativo de 600 m
    planner = ResourceMissionPlanner(
        t, PlannerConfig(max_slope_deg=18.0, rover_radius_m=0.4,
                         safety_margin_m=0.3, near_obstacle_m=25.0),
        Consumption(speed_m_per_min=30.0, oxygen_u_per_min=0.25,
                    water_l_per_min=0.004, battery_wh_per_min=0.7,
                    nutrition_kcal_per_min=4.0),
        Budget(time_min=120, time_reserve_min=20, oxygen_u=30,
               oxygen_reserve_u=6, water_l=1.2, water_reserve_l=0.2,
               battery_wh=120, battery_reserve_wh=25,
               nutrition_kcal=420, nutrition_reserve_kcal=40))
    return planner.plan((8, 2), (8, 27), activity_min=12)


def rover_demo() -> MissionPlan:
    t = synthetic_terrain()
    planner = ResourceMissionPlanner(
        t, PlannerConfig(),
        Consumption(speed_m_per_min=0.15, battery_wh_per_min=0.9,
                    climb_battery_wh_per_m=0.5),
        Budget(time_min=180, time_reserve_min=20,
               battery_wh=180, battery_reserve_wh=25))
    return planner.plan((8, 2), (8, 27), activity_min=5)


def main() -> None:
    for label, factory in [('ASTRONAUTA', astronaut_demo), ('ROVER', rover_demo)]:
        try:
            p = factory()
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
