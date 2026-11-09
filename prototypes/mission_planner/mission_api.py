"""Stage 3 local mission contract. Standard library, Python 3.10+.

MissionRequest has required fields but defers semantic validation to plan_mission.
Missing constructor arguments raise TypeError outside that facade. TerrainReference,
LocalFrame and AgentProfile construction errors likewise precede its boundary.
Only request validation errors become INVALID_INPUT; implementation errors propagate.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import json
import math
from numeric_domain import finite_number, finite_result, NumericDomainError

from mars_route_planner import Cell, TerrainSnapshot
from mars_mission_resources import (
    AgentProfile, ExcludedResource, RESOURCE_UNITS, ResourceMissionPlanner,
    NoFeasibleMissionError, SearchLimitReachedError, Usage,
)

SCHEMA_VERSION = "3.0"
TOLERANCE = 1e-9
USAGE_FIELDS = dict(time="minutes", battery="battery_wh", oxygen="oxygen_u",
                    water="water_l", nutrition="nutrition_kcal")


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: se requiere texto no vacio")


def _finite(value):
    return finite_number(value)


def _digest(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TerrainReference:
    """Immutable captured terrain. Revision is SHA-256 of canonical snapshot data.

    Numeric grids/resolution normalize to floats; obstacles remain bool and unknown
    heights null. The digest covers all four grids, resolution and hash format.
    """
    terrain_id: str
    snapshot: TerrainSnapshot

    def __post_init__(self):
        _text(self.terrain_id, "terrain_id")
        object.__setattr__(self, "snapshot", TerrainSnapshot.capture(self.snapshot))

    @classmethod
    def capture(cls, terrain, terrain_id):
        return cls(terrain_id, TerrainSnapshot.capture(terrain))

    @property
    def revision_sha256(self):
        t = self.snapshot
        data = {name: [[None if v is None else float(v) for v in row]
                       for row in getattr(t, name)]
                for name in ("heights_m", "risk", "roughness")}
        data.update(obstacles=t.obstacles, resolution_m=float(t.resolution_m),
                    hash_format="terrain-snapshot-v1")
        return _digest(data)

    def identity(self):
        return dict(terrain_id=self.terrain_id, revision_sha256=self.revision_sha256,
                    hash_format="terrain-snapshot-v1", rows=self.snapshot.rows,
                    columns=self.snapshot.cols, resolution_m=self.snapshot.resolution_m)


@dataclass(frozen=True)
class LocalFrame:
    """XY in meters: origin is the outer corner preceding cell (0,0).

    x increases with column, y increases with row (no Y sign reversal).
    Cell center = origin + ((column+.5)*resolution, (row+.5)*resolution).
    This local convention has no geographic east/north or planetary datum claim.
    """
    frame_id: str
    resolution_m: float
    origin_xy_m: tuple[float, float]
    coordinate_unit: str = "m"
    height_unit: str = "m"
    time_unit: str = "min"
    cell_order: str = "row,column"
    x_axis: str = "increasing_column"
    y_axis: str = "increasing_row"
    origin_location: str = "outer_corner_row0_col0"

    def __post_init__(self):
        _text(self.frame_id, "frame_id")
        if not _finite(self.resolution_m) or self.resolution_m <= 0:
            raise ValueError("resolution_m debe ser finita y positiva")
        if (type(self.origin_xy_m) is not tuple or len(self.origin_xy_m) != 2
                or not all(_finite(v) for v in self.origin_xy_m)):
            raise ValueError("origin_xy_m requiere dos numeros finitos en una tupla")
        expected = dict(coordinate_unit="m", height_unit="m", time_unit="min",
                        cell_order="row,column", x_axis="increasing_column",
                        y_axis="increasing_row", origin_location="outer_corner_row0_col0")
        if any(getattr(self, k) != v for k, v in expected.items()):
            raise ValueError("Unidades o convencion de marco local incompatibles")

    def waypoint(self, cell):
        r, c = cell
        return [self.origin_xy_m[0] + (c + .5) * self.resolution_m,
                self.origin_xy_m[1] + (r + .5) * self.resolution_m]


class RequestValidationError(ValueError):
    pass


@dataclass(frozen=True)
class MissionRequest:
    schema_version: str
    request_id: str
    terrain: TerrainReference
    frame: LocalFrame
    base: Cell
    start: Cell
    goal: Cell
    activity_min: float
    profile: AgentProfile
    max_labels: int

    def validate(self):
        def require(condition, message):
            if not condition:
                raise RequestValidationError(message)
        require(self.schema_version == SCHEMA_VERSION, "Version de solicitud incompatible")
        require(isinstance(self.request_id, str) and bool(self.request_id.strip()),
                "request_id obligatorio y no vacio")
        require(type(self.terrain) is TerrainReference, "Se requiere TerrainReference capturado")
        require(type(self.frame) is LocalFrame, "Se requiere LocalFrame validado")
        require(type(self.profile) is AgentProfile, "Se requiere AgentProfile validado")
        t = self.terrain.snapshot
        require(self.frame.resolution_m == t.resolution_m, "Resolucion del marco y snapshot diferente")
        for name in ("base", "start", "goal"):
            cell = getattr(self, name)
            require(type(cell) is tuple and len(cell) == 2 and all(type(v) is int for v in cell),
                    f"{name}: coordenadas (fila,columna) enteras, sin bool")
            require(0 <= cell[0] < t.rows and 0 <= cell[1] < t.cols,
                    f"{name}: coordenadas fuera del mapa")
        require(self.base == self.start, "Inicio y base deben coincidir")
        require(self.base != self.goal, "Base y objetivo deben ser diferentes")
        require(_finite(self.activity_min) and self.activity_min >= 0,
                "Duracion de ciencia finita y no negativa requerida")
        require(type(self.max_labels) is int and self.max_labels > 0,
                "max_labels debe ser entero positivo, sin bool")
        # Ensure the promised XY representation is finite even for huge origins.
        require(all(math.isfinite(v) for cell in ((0, 0), (t.rows-1, t.cols-1))
                    for v in self.frame.waypoint(cell)), "Waypoints locales no finitos")


class MissionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    INFEASIBLE = "INFEASIBLE"
    SEARCH_LIMIT_REACHED = "SEARCH_LIMIT_REACHED"
    INVALID_INPUT = "INVALID_INPUT"


@dataclass(frozen=True)
class MissionResult:
    schema_version: str
    request_id: str | None
    status: MissionStatus
    reason_code: str
    message: str
    terrain: dict | None
    profile: dict | None
    frame: dict | None
    assumptions: tuple[str, ...]
    exclusions: dict
    search_metrics: dict
    plan: dict | None = None

    def to_dict(self):
        """Detached JSON-compatible data; nonfinite implementation errors fail loudly."""
        return json.loads(json.dumps(asdict(self), allow_nan=False, ensure_ascii=False))

    def to_json(self, *, indent=2):
        return json.dumps(self.to_dict(), allow_nan=False, ensure_ascii=False, indent=indent)


def _profile_data(profile):
    data = {name: getattr(profile, name) for name in
            ("agent_type", "profile_id", "version", "parameter_nature", "provenance", "limitations")}
    data.update(mobility=asdict(profile.mobility), motion=asdict(profile.motion),
                resources={k: dict(status=profile.resource_status(k), unit=unit,
                                   **(asdict(profile.resources[k]) if k in profile.resources else {}))
                           for k, unit in RESOURCE_UNITS.items()})
    data["revision_sha256"] = _digest(data)
    return data


def _quantities(profile, usage):
    return {name: (getattr(usage, field) if profile.resource_status(name) == "modeled" else None)
            for name, field in USAGE_FIELDS.items()}


def _resources(profile, usage):
    used = _quantities(profile, usage)
    result = {}
    for name, unit in RESOURCE_UNITS.items():
        status = profile.resource_status(name)
        item = profile.resources.get(name)
        result[name] = dict(status=status, unit=unit, consumed=used[name], capacity=None,
                            reserve=None, remaining=None, margin_above_reserve=None)
        if status == "modeled":
            remaining = item.capacity - used[name]
            result[name].update(capacity=item.capacity, reserve=item.reserve,
                                remaining=finite_result(remaining, 'remaining'),
                                margin_above_reserve=finite_result(remaining-item.reserve, 'margin'))
        elif isinstance(item, ExcludedResource):
            result[name]["reason"] = item.reason
    return result


def _breakdown(request, planner, plan, *, include_activity=True, return_only=False):
    cumulative = Usage()
    phases = {name: Usage() for name in ("outbound", "activity", "inbound")}
    events = []

    def append(phase, kind, a, b, increment):
        nonlocal cumulative
        cumulative = cumulative + increment
        phases[phase] = phases[phase] + increment
        events.append(dict(index=len(events), phase=phase, kind=kind,
                           start_cell=list(a), end_cell=list(b),
                           duration_min=increment.minutes, distance_m=increment.distance_m,
                           incremental=_quantities(request.profile, increment),
                           cumulative=_quantities(request.profile, cumulative),
                           resources=_resources(request.profile, cumulative)))

    if include_activity and plan.goal_index == 0:
        append("activity", "science", plan.path[0], plan.path[0],
               planner.activity_consumption.stationary(request.activity_min))
    for i, (a, b) in enumerate(zip(plan.path, plan.path[1:]), start=1):
        edge = planner.nav._edge(a, b)
        if edge is None:
            raise RuntimeError("Arista del plan no admisible en su snapshot")
        append("outbound" if i <= plan.goal_index else "inbound", "movement", a, b,
               planner.movement_usage(a, b, edge[1]))
        if include_activity and i == plan.goal_index:
            append("activity", "science", b, b,
                   planner.activity_consumption.stationary(request.activity_min))
    finite_result(plan.cost, 'plan_cost')
    if any(not _finite(a) or not _finite(b) or abs(a-b) > TOLERANCE
           for a, b in zip(cumulative.values(), plan.total.values())):
        raise RuntimeError("Desglose y total del motor no coinciden")
    return dict(path=[list(cell) for cell in plan.path],
                goal_cell=None if return_only else list(request.goal),
                goal_index=None if return_only else plan.goal_index, base_cell=list(request.base),
                waypoints_xy_m=[request.frame.waypoint(cell) for cell in plan.path],
                events=events, phases={name: dict(duration_min=u.minutes, distance_m=u.distance_m,
                                                consumed=_quantities(request.profile, u))
                                       for name, u in phases.items()},
                total=dict(duration_min=plan.total.minutes, distance_m=plan.total.distance_m,
                           resources=_resources(request.profile, plan.total)),
                cost=plan.cost, cost_objective="sum(move_minutes*(1+hazard_cost_weight*"
                "max(0,edge_cost/distance-1))+activity_minutes+battery_cost_weight*"
                "(move_Wh+activity_Wh))", consistency_tolerance_absolute=TOLERANCE)


def plan_mission(request: MissionRequest) -> MissionResult:
    """Single search using from_profile. Does not catch unexpected engine errors.

    Semantic errors in a MissionRequest (or a wrong top-level type) yield
    INVALID_INPUT. Failed construction of nested contracts/missing Python arguments
    must be handled by their caller and cannot be converted retroactively here.
    """
    valid_type = type(request) is MissionRequest
    terrain = request.terrain if valid_type and type(request.terrain) is TerrainReference else None
    profile = request.profile if valid_type and type(request.profile) is AgentProfile else None
    frame = request.frame if valid_type and type(request.frame) is LocalFrame else None
    request_id = request.request_id if valid_type and isinstance(request.request_id, str) else None

    def result(status, code, message, metrics=None, plan=None):
        return MissionResult(SCHEMA_VERSION, request_id, status, code, message,
                             terrain.identity() if terrain else None,
                             _profile_data(profile) if profile else None,
                             asdict(frame) if frame else None,
                             ("Modelo determinista local; geometria conservadora y snapshot inmutable.",
                              "Consumos parametrizados; sin certificacion fisica/EVA.",
                              profile.limitations if profile else "Perfil no validado."),
                             {k: v.reason for k, v in profile.resources.items()
                              if isinstance(v, ExcludedResource)} if profile else {},
                             metrics or dict(generated_labels=None,
                                             meaning="Etiquetas generadas, no expansiones"), plan)
    try:
        if not valid_type:
            raise RequestValidationError("Se requiere MissionRequest")
        request.validate()
    except RequestValidationError as error:
        return result(MissionStatus.INVALID_INPUT, "REQUEST_VALIDATION_FAILED", str(error))
    try:
        planner = ResourceMissionPlanner.from_profile(terrain.snapshot, profile)
        if not planner.nav.traversable(request.base) or not planner.nav.traversable(request.goal):
            return result(MissionStatus.INFEASIBLE, "ENDPOINT_NOT_TRAVERSABLE",
                          "Base u objetivo dentro del mapa pero no transitable bajo la geometria y movilidad configuradas.")
        try:
            plan = planner.plan(request.start, request.goal, request.activity_min, request.max_labels)
        except SearchLimitReachedError as error:
            return result(MissionStatus.SEARCH_LIMIT_REACHED, "LABEL_LIMIT_REACHED",
                          "Busqueda interrumpida por limite de etiquetas; factibilidad desconocida.",
                          dict(generated_labels=error.generated_labels, max_labels=error.limit,
                               meaning="Etiquetas generadas, no expansiones"))
        except NoFeasibleMissionError:
            return result(MissionStatus.INFEASIBLE, "SEARCH_EXHAUSTED",
                          "Busqueda agotada sin mision admisible con ida, ciencia, regreso y reservas; no se identifica una causa unica.")
        return result(MissionStatus.SUCCESS, "MISSION_FOUND",
                      "Mision admisible bajo el perfil y snapshot indicados: ida, ciencia y regreso; restricciones de movilidad y presupuestos con reservas verificados (tolerancia 1e-9). El costo combina tiempo ponderado por peligro y bateria; no certifica la ruta mas segura ni optimalidad operacional global.",
                      dict(generated_labels=plan.explored_labels,
                           meaning="explored_labels del motor cuenta etiquetas generadas, no expansiones"),
                      _breakdown(request, planner, plan))

    except NumericDomainError as error:
        return result(MissionStatus.INVALID_INPUT, "NUMERIC_DOMAIN_EXCEEDED", str(error))
