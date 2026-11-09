"""MARS GOD'S EYE - Prototipo de planificador A* con riesgo y pendiente.

Esta es una DEMOSTRACION SINTETICA. No controla motores, no carga un DEM real,
no modela toda la geometria de un rover rocker-bogie y NO es un sistema de
seguridad certificado. Python 3.10+, sin dependencias externas.

Ejecutar: python mars_route_planner.py
"""
from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
from typing import Optional

Cell = tuple[int, int]  # (fila, columna)


@dataclass
class Terrain:
    heights_m: list[list[Optional[float]]]
    obstacles: list[list[bool]]
    risk: list[list[float]]
    roughness: list[list[float]]
    resolution_m: float

    def __post_init__(self) -> None:
        if not self.heights_m or not self.heights_m[0]:
            raise ValueError("El terreno no puede estar vacio")
        rows, cols = len(self.heights_m), len(self.heights_m[0])
        if not math.isfinite(self.resolution_m) or self.resolution_m <= 0:
            raise ValueError("resolution_m debe ser positivo")
        for name, arr in (("heights_m", self.heights_m),
                          ("obstacles", self.obstacles),
                          ("risk", self.risk),
                          ("roughness", self.roughness)):
            if len(arr) != rows or any(len(row) != cols for row in arr):
                raise ValueError(f"{name} no coincide con la cuadricula")
        for r in range(rows):
            for c in range(cols):
                h = self.heights_m[r][c]
                if h is not None and not math.isfinite(h):
                    raise ValueError("Altura no finita; use None para desconocido")
                for name, arr in (("risk", self.risk), ("roughness", self.roughness)):
                    value = arr[r][c]
                    if not math.isfinite(value) or not (0 <= value <= 1):
                        raise ValueError(f"{name} debe estar entre 0 y 1")

    @property
    def rows(self) -> int:
        return len(self.heights_m)

    @property
    def cols(self) -> int:
        return len(self.heights_m[0])


@dataclass(frozen=True)
class PlannerConfig:
    # Todos estos valores son ILUSTRATIVOS: calibrar para el rover real.
    max_slope_deg: float = 18.0
    rover_radius_m: float = 0.12
    safety_margin_m: float = 0.08
    near_obstacle_m: float = 0.60
    slope_weight: float = 3.0
    risk_weight: float = 2.0
    roughness_weight: float = 1.5
    proximity_weight: float = 0.8

    def __post_init__(self) -> None:
        if not (0 < self.max_slope_deg < 90):
            raise ValueError("max_slope_deg debe estar en (0,90)")
        other = (self.rover_radius_m, self.safety_margin_m,
                 self.near_obstacle_m, self.slope_weight, self.risk_weight,
                 self.roughness_weight, self.proximity_weight)
        if any(not math.isfinite(x) or x < 0 for x in other):
            raise ValueError("Radios y pesos deben ser no negativos y finitos")


@dataclass
class Route:
    cells: list[Cell]
    waypoints_xy_m: list[tuple[float, float]]
    distance_m: float
    total_cost: float
    max_slope_deg: float


class NoSafeRouteError(Exception):
    """No hay ruta bajo las restricciones fisicas seleccionadas."""


class RiskAwareAStar:
    MOVES = tuple((dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                  if dr != 0 or dc != 0)

    def __init__(self, terrain: Terrain, config: PlannerConfig = PlannerConfig()):
        self.t = terrain
        self.cfg = config
        self._obstacles = [(r, c) for r in range(terrain.rows)
                           for c in range(terrain.cols)
                           if terrain.obstacles[r][c] or terrain.heights_m[r][c] is None]
        self._slopes = [[self._terrain_slope(r, c) for c in range(terrain.cols)]
                        for r in range(terrain.rows)]
        self._clearances = [[self._clearance(r, c) for c in range(terrain.cols)]
                            for r in range(terrain.rows)]

    def _height(self, r: int, c: int) -> Optional[float]:
        if 0 <= r < self.t.rows and 0 <= c < self.t.cols:
            return self.t.heights_m[r][c]
        return None

    def _terrain_slope(self, r: int, c: int) -> float:
        h = self._height(r, c)
        if h is None:
            return math.inf
        res = self.t.resolution_m
        def grad(dr: int, dc: int) -> float:
            before, after = self._height(r - dr, c - dc), self._height(r + dr, c + dc)
            if before is not None and after is not None:
                return (after - before) / (2 * res)
            if after is not None:
                return (after - h) / res
            if before is not None:
                return (h - before) / res
            return 0.0
        return math.degrees(math.atan(math.hypot(grad(0, 1), grad(1, 0))))

    def _clearance(self, r: int, c: int) -> float:
        res = self.t.resolution_m
        # Margen desde el CENTRO de celda a los bordes de la maqueta.
        border = min(r + 0.5, c + 0.5,
                     self.t.rows - r - 0.5, self.t.cols - c - 0.5) * res
        if not self._obstacles:
            return border
        # Modelo discreto sencillo: distancia a centros ocupados.
        obs_dist = min(math.hypot(r - rr, c - cc) * res
                       for rr, cc in self._obstacles)
        return min(border, obs_dist)

    def traversable(self, cell: Cell) -> bool:
        r, c = cell
        if not (0 <= r < self.t.rows and 0 <= c < self.t.cols):
            return False
        if self.t.heights_m[r][c] is None or self.t.obstacles[r][c]:
            return False
        if self._slopes[r][c] > self.cfg.max_slope_deg:
            return False
        return self._clearances[r][c] >= self.cfg.rover_radius_m + self.cfg.safety_margin_m

    def _edge(self, a: Cell, b: Cell) -> tuple[float, float, float] | None:
        if not self.traversable(b):
            return None
        ar, ac = a
        br, bc = b
        dr, dc = br - ar, bc - ac
        if abs(dr) > 1 or abs(dc) > 1 or (dr == 0 and dc == 0):
            return None
        # No cortar esquinas entre dos celdas prohibidas.
        if dr != 0 and dc != 0:
            if not self.traversable((ar, bc)) or not self.traversable((br, ac)):
                return None
        distance = math.hypot(dr, dc) * self.t.resolution_m
        za, zb = self.t.heights_m[ar][ac], self.t.heights_m[br][bc]
        assert za is not None and zb is not None
        edge_slope = math.degrees(math.atan(abs(zb - za) / distance))
        slope = max(edge_slope, self._slopes[ar][ac], self._slopes[br][bc])
        if slope > self.cfg.max_slope_deg:
            return None
        risk = (self.t.risk[ar][ac] + self.t.risk[br][bc]) / 2
        rough = (self.t.roughness[ar][ac] + self.t.roughness[br][bc]) / 2
        clearance = min(self._clearances[ar][ac], self._clearances[br][bc])
        near = (max(0.0, (self.cfg.near_obstacle_m - clearance) /
                    self.cfg.near_obstacle_m) if self.cfg.near_obstacle_m > 0 else 0.0)
        multiplier = (1 + self.cfg.slope_weight * (slope / self.cfg.max_slope_deg)**2
                      + self.cfg.risk_weight * risk
                      + self.cfg.roughness_weight * rough
                      + self.cfg.proximity_weight * near)
        return distance * multiplier, distance, slope

    def plan(self, start: Cell, goal: Cell) -> Route:
        if not self.traversable(start):
            raise NoSafeRouteError("El inicio esta bloqueado o fuera de limites")
        if not self.traversable(goal):
            raise NoSafeRouteError("La meta esta bloqueada o fuera de limites")
        def heuristic(p: Cell) -> float:
            return math.hypot(p[0] - goal[0], p[1] - goal[1]) * self.t.resolution_m
        g_score: dict[Cell, float] = {start: 0.0}
        came_from: dict[Cell, Cell] = {}
        queue = [(heuristic(start), 0.0, start)]
        while queue:
            _, best_g, here = heapq.heappop(queue)
            if best_g > g_score.get(here, math.inf) + 1e-10:
                continue
            if here == goal:
                cells = [goal]
                while cells[-1] != start:
                    cells.append(came_from[cells[-1]])
                cells.reverse()
                total_distance, max_slope = 0.0, 0.0
                for a, b in zip(cells, cells[1:]):
                    result = self._edge(a, b)
                    assert result is not None
                    _, dist, slope = result
                    total_distance += dist
                    max_slope = max(max_slope, slope)
                res = self.t.resolution_m
                waypoints = [((c + 0.5) * res, (r + 0.5) * res)
                             for r, c in cells]
                return Route(cells, waypoints, total_distance, best_g, max_slope)
            hr, hc = here
            for dr, dc in self.MOVES:
                nb = (hr + dr, hc + dc)
                edge = self._edge(here, nb)
                if edge is None:
                    continue
                new_g = best_g + edge[0]
                if new_g + 1e-10 < g_score.get(nb, math.inf):
                    came_from[nb] = here
                    g_score[nb] = new_g
                    heapq.heappush(queue, (new_g + heuristic(nb), new_g, nb))
        raise NoSafeRouteError("No existe ruta segura con los limites configurados")


def synthetic_terrain() -> Terrain:
    """Terreno inventado para demo. NO representa datos de Marte ni mediciones reales."""
    rows, cols, res = 17, 30, 0.20
    heights = [[0.02 * math.sin(c / 6) for c in range(cols)] for _ in range(rows)]
    obstacles = [[False for _ in range(cols)] for _ in range(rows)]
    risk = [[0.0 for _ in range(cols)] for _ in range(rows)]
    rough = [[0.0 for _ in range(cols)] for _ in range(rows)]
    # Crater circular central y zona de riesgo; artificiales.
    for r in range(rows):
        for c in range(cols):
            dist = math.hypot(r - 8, c - 14)
            if dist < 3.1:
                obstacles[r][c] = True
            if 3.1 <= dist < 6.4:
                risk[r][c] = 0.85
                rough[r][c] = 0.60
    # Obstaculos adicionales.
    for r, c in ((4, 21), (5, 21), (12, 21), (13, 22)):
        obstacles[r][c] = True
    return Terrain(heights, obstacles, risk, rough, res)


def demo() -> None:
    terrain = synthetic_terrain()
    planner = RiskAwareAStar(terrain)
    start, goal = (8, 2), (8, 27)
    route = planner.plan(start, goal)
    chars = [["#" if terrain.obstacles[r][c] else
              "x" if not planner.traversable((r, c)) else
              ":" if terrain.risk[r][c] > 0.5 else "."
              for c in range(terrain.cols)] for r in range(terrain.rows)]
    for r, c in route.cells:
        chars[r][c] = "o"
    chars[start[0]][start[1]] = "S"
    chars[goal[0]][goal[1]] = "G"
    print("Mapa sintetico: S=inicio, G=meta, o=ruta, #=obstaculo, x=no transitable, :=riesgo")
    for row in chars:
        print("".join(row))
    print(f"Ruta: {len(route.cells)} celdas | Distancia: {route.distance_m:.2f} m | "
          f"Costo: {route.total_cost:.2f} | Pendiente maxima: {route.max_slope_deg:.1f} grados")
    print("Waypoints XY en metros:", route.waypoints_xy_m)


if __name__ == "__main__":
    demo()
