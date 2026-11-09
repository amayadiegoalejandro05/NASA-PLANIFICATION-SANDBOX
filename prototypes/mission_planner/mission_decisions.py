"""Stage 5 experimental decisions. Standard library only; no physiological model.

Construction errors raise ValueError. Semantically invalid requests return
INVALID_INPUT; unexpected engine errors propagate. Version 3.0 stays unchanged.
"""
from dataclasses import asdict, dataclass, replace
import json
from types import MappingProxyType, SimpleNamespace
from typing import Mapping
from numeric_domain import finite_result, NumericDomainError

from mars_mission_resources import (
    AgentProfile, ResourceAllocation, ResourceMissionPlanner,
    NoFeasibleMissionError, SearchLimitReachedError,
)
from mission_api import (
    LocalFrame, TerrainReference, MissionStatus as S, _finite, _text,
    _profile_data, _breakdown,
)

SCHEMA_VERSION = "5.0"


@dataclass(frozen=True)
class PersonalCharacteristics:
    """Optional descriptive metadata. Neither field changes consumption/mobility.

    Age and biological sex are deliberately absent: no implemented model needs
    them. Gender identity is never a physiological coefficient.
    """
    body_mass_kg: float | None = None
    height_m: float | None = None

    def __post_init__(self):
        for key, value in asdict(self).items():
            if value is not None and (not _finite(value) or value <= 0):
                raise ValueError(f"{key}: numero finito positivo o None requerido")


@dataclass(frozen=True)
class RateProvenance:
    nature: str  # measured / estimated / simulated
    source: str
    scope: str

    def __post_init__(self):
        if self.nature not in ("measured", "estimated", "simulated"):
            raise ValueError("Naturaleza de tasa desconocida")
        _text(self.source, "source")
        _text(self.scope, "scope")


@dataclass(frozen=True)
class RateScenario:
    """Explicit sensitivity factors on movement/activity rates, not probabilities.

    Time remains elapsed time at rate 1; factors do not change speed or climb
    battery coefficient. Conservative means non-decreasing rate assumptions only.
    """
    name: str
    factors: Mapping[str, float]
    rationale: str

    def __post_init__(self):
        if self.name not in ("nominal", "conservative"):
            raise ValueError("Escenario nominal o conservative requerido")
        _text(self.rationale, "rationale")
        factors = dict(self.factors)
        for key, value in factors.items():
            if not _finite(value) or value < 1 or (self.name == "nominal" and value != 1):
                raise ValueError("Factores nominales =1; conservadores >=1")
            if key == "time" and value != 1:
                raise ValueError("El tiempo no se escala como tasa de consumo")
        object.__setattr__(self, "factors", MappingProxyType(factors))

    def to_dict(self):
        return dict(name=self.name, factors=dict(self.factors), rationale=self.rationale,
                    interpretation="Sensibilidad determinista; sin probabilidad calibrada")


def modeled_keys(profile):
    return {k for k, v in profile.resources.items() if type(v) is ResourceAllocation}


def nominal_scenario(profile):
    return RateScenario("nominal", {k: 1. for k in modeled_keys(profile)}, "Tasas individuales declaradas")


def declared_provenance(profile, nature):
    """Caller explicitly labels origin; no automatic claim of measurement."""
    return {k: RateProvenance(nature, profile.provenance,
                             "Movimiento y actividad; " + profile.limitations)
            for k in modeled_keys(profile)}


@dataclass(frozen=True)
class MissionState:
    mission_id: str
    original_base: tuple[int, int]
    current: tuple[int, int]
    goal: tuple[int, int]
    activity_status: str  # pending / completed
    pending_activity_min: float
    remaining: Mapping[str, float]
    reserves: Mapping[str, float]
    profile_id: str
    profile_version: str
    profile_revision_sha256: str
    terrain_id: str
    terrain_revision_sha256: str
    historical_consumption: Mapping[str, float] | None = None

    def __post_init__(self):
        for key in ("mission_id", "profile_id", "profile_version", "profile_revision_sha256",
                    "terrain_id", "terrain_revision_sha256"):
            _text(getattr(self, key), key)
        for key in ("original_base", "current", "goal"):
            cell = getattr(self, key)
            if type(cell) is not tuple or len(cell) != 2 or any(type(x) is not int for x in cell):
                raise ValueError(f"{key}: centros de celda (fila,columna) enteros requeridos")
        if self.activity_status not in ("pending", "completed"):
            raise ValueError("Estado de actividad desconocido")
        if not _finite(self.pending_activity_min) or self.pending_activity_min < 0:
            raise ValueError("Actividad pendiente finita no negativa requerida")
        if self.activity_status == "completed" and self.pending_activity_min != 0:
            raise ValueError("Actividad completada no puede tener minutos pendientes")
        for key in ("remaining", "reserves", "historical_consumption"):
            value = getattr(self, key)
            if value is None and key == "historical_consumption":
                continue
            copy = dict(value)
            if any(not _finite(v) or v < 0 for v in copy.values()):
                raise ValueError(f"{key}: recursos finitos no negativos requeridos")
            object.__setattr__(self, key, MappingProxyType(copy))

    @classmethod
    def capture(cls, mission_id, terrain, profile, base, current, goal,
                pending_activity_min, *, completed=False, remaining=None, historical_consumption=None):
        return cls(mission_id, base, current, goal, "completed" if completed else "pending",
                   pending_activity_min,
                   {k: v.capacity for k, v in profile.resources.items() if type(v) is ResourceAllocation}
                   if remaining is None else remaining,
                   {k: v.reserve for k, v in profile.resources.items() if type(v) is ResourceAllocation},
                   profile.profile_id, profile.version, _profile_data(profile)["revision_sha256"],
                   terrain.terrain_id, terrain.revision_sha256, historical_consumption)

    def to_dict(self):
        return {key: (dict(value) if isinstance(value, Mapping) else value)
                for key, value in vars(self).items()}


@dataclass(frozen=True)
class DecisionRequest:
    schema_version: str
    request_id: str
    terrain: TerrainReference
    frame: LocalFrame
    profile: AgentProfile  # original capacities/reserves, not the remaining budget
    state: MissionState
    rate_provenance: Mapping[str, RateProvenance]
    scenario: RateScenario
    max_labels: int
    personal: PersonalCharacteristics | None = None

    def __post_init__(self):
        object.__setattr__(self, "rate_provenance", MappingProxyType(dict(self.rate_provenance)))

    def validate(self):
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("Version requerida 5.0; no reinterpretar solicitudes 3.0")
        _text(self.request_id, "request_id")
        if (type(self.terrain) is not TerrainReference or type(self.frame) is not LocalFrame
                or type(self.profile) is not AgentProfile or type(self.state) is not MissionState
                or type(self.scenario) is not RateScenario):
            raise ValueError("Contratos tipados requeridos")
        if self.personal is not None and (type(self.personal) is not PersonalCharacteristics
                                         or self.profile.agent_type != "astronaut"):
            raise ValueError("Caracteristicas personales solo para astronauta")
        if type(self.max_labels) is not int or self.max_labels <= 0:
            raise ValueError("max_labels entero positivo requerido")
        t, s, p = self.terrain.snapshot, self.state, self.profile
        if self.frame.resolution_m != t.resolution_m:
            raise ValueError("Marco y snapshot incompatibles")
        if any(not _finite(x) for cell in ((0, 0), (t.rows-1, t.cols-1)) for x in self.frame.waypoint(cell)):
            raise ValueError("Waypoints no finitos")
        for cell in (s.original_base, s.current, s.goal):
            if not (0 <= cell[0] < t.rows and 0 <= cell[1] < t.cols):
                raise ValueError("Posicion fuera del snapshot")
        if s.original_base == s.goal:
            raise ValueError("Objetivo cientifico debe diferir de base")
        if (s.terrain_id != self.terrain.terrain_id or s.terrain_revision_sha256 != self.terrain.revision_sha256):
            raise ValueError("Revision/identidad del terreno del estado no coincide con snapshot")
        if (s.profile_id != p.profile_id or s.profile_version != p.version
                or s.profile_revision_sha256 != _profile_data(p)["revision_sha256"]):
            raise ValueError("Identidad/revision del perfil incoherente")
        keys = modeled_keys(p)
        if any(set(m) != keys for m in (s.remaining, s.reserves, self.rate_provenance, self.scenario.factors)):
            raise ValueError("Recursos, reservas, procedencias y factores deben cubrir exactamente recursos modelados")
        if any(type(v) is not RateProvenance for v in self.rate_provenance.values()):
            raise ValueError("RateProvenance requerida por recurso")
        if s.historical_consumption is not None and not set(s.historical_consumption) <= keys:
            raise ValueError("Historico contiene recursos no modelados")
        for k in keys:
            if s.reserves[k] != p.resources[k].reserve:
                raise ValueError("Conservar reservas absolutas originales del perfil")
            if s.remaining[k] > p.resources[k].capacity:
                raise ValueError("Saldo supera capacidad original del perfil")

    def to_dict(self):
        self.validate()
        return dict(schema_version=self.schema_version, request_id=self.request_id,
                    terrain=dict(**self.terrain.identity(), snapshot=asdict(self.terrain.snapshot)),
                    frame=asdict(self.frame), profile=_profile_data(self.profile), state=self.state.to_dict(),
                    rate_provenance={k: asdict(v) for k, v in self.rate_provenance.items()},
                    scenario=self.scenario.to_dict(), max_labels=self.max_labels,
                    personal=asdict(self.personal) if self.personal else None,
                    personal_effect="Metadatos sin efecto en consumo o movilidad")


POLICIES = ("balanced", "minimum_time", "terrain_caution")


def policy_profile(profile, policy):
    if policy not in POLICIES:
        raise ValueError("Politica desconocida")
    motion = profile.motion
    if policy == "minimum_time":
        motion = replace(motion, hazard_cost_weight=0., battery_cost_weight=0.)
    elif policy == "terrain_caution":
        motion = replace(motion, hazard_cost_weight=finite_result(max(4., 2*motion.hazard_cost_weight), 'policy_weight'))
    return replace(profile, motion=motion)


@dataclass(frozen=True)
class DecisionResult:
    payload: dict

    def to_dict(self):
        return json.loads(self.to_json())

    def to_json(self, *, indent=2):
        return json.dumps(self.payload, ensure_ascii=False, allow_nan=False, indent=indent)

    @property
    def status(self):
        return S(self.payload["status"])

    @property
    def plan(self):
        return self.payload.get("plan")


def effective_future_profile(request, policy="balanced"):
    """Single adapter for scenario rates, remaining balances and absolute reserves."""
    p=policy_profile(request.profile,policy)
    resources=dict(p.resources)
    for k in modeled_keys(p):
        item,factor=resources[k],request.scenario.factors[k]
        resources[k]=replace(item,capacity=request.state.remaining[k],reserve=request.state.reserves[k],
                             movement_rate=finite_result(item.movement_rate*factor, 'scenario_movement_rate'),
                             activity_rate=finite_result(item.activity_rate*factor, 'scenario_activity_rate'))
    return replace(p,resources=resources)


def plan_future(request: DecisionRequest, mode="continue", policy="balanced") -> DecisionResult:
    """One future plan using remaining balances; history is never debited.

    Completed activity suppresses service, but continue still visits the goal.
    Return ignores the goal's traversability and has no science event.
    """
    request_id = getattr(request, "request_id", None)
    limit = getattr(request, "max_labels", None)
    data = dict(schema_version=SCHEMA_VERSION, request_id=request_id if isinstance(request_id, str) else None,
                mode=mode, policy=policy, status=None, reason_code=None, message=None,
                request=None, effective_profile=None, plan=None,
                search_metrics=dict(generated_labels=None, max_labels=limit if type(limit) is int and limit > 0 else None,
                                    meaning="Etiquetas generadas; no expansiones"))

    def result(status, code, message):
        data.update(status=status.value, reason_code=code, message=message)
        return DecisionResult(data)

    try:
        if type(request) is not DecisionRequest:
            raise ValueError("DecisionRequest requerida")
        request.validate()
        if mode not in ("continue", "return") or policy not in POLICIES:
            raise ValueError("Modo o politica desconocida")
    except ValueError as error:
        return result(S.INVALID_INPUT, "REQUEST_VALIDATION_FAILED", str(error))
    data["request"] = request.to_dict()
    s = request.state
    try:
        p = policy_profile(request.profile, policy)
        data["policy_weights"] = dict(mobility=asdict(p.mobility), motion=asdict(p.motion))
        # Validate position even if balance is already below reserve; do not relocate.
        nav = ResourceMissionPlanner.from_profile(request.terrain.snapshot, p).nav
        for name, cell in (("CURRENT", s.current), ("BASE", s.original_base), ("GOAL", s.goal)):
            if name == "GOAL" and mode == "return":
                continue
            if request.terrain.snapshot.heights_m[cell[0]][cell[1]] is None:
                return result(S.INFEASIBLE, name+"_UNKNOWN", "Celda desconocida; no se desplaza el agente.")
            if not nav.traversable(cell):
                return result(S.INFEASIBLE, name+"_NOT_TRAVERSABLE", "Celda no transitable con snapshot, huella y movilidad declarados.")
        if any(s.remaining[k] < s.reserves[k] for k in modeled_keys(p)):
            return result(S.INFEASIBLE, "BALANCE_BELOW_RESERVE", "Saldo menor que reserva absoluta; no se reduce la reserva.")
        effective = effective_future_profile(request,policy)
        data["effective_profile"] = _profile_data(effective)
        planner = ResourceMissionPlanner.from_profile(request.terrain.snapshot, effective)
        return_only = mode == "return"
        try:
            plan = planner.plan(s.current, s.goal, s.pending_activity_min, request.max_labels,
                                base=s.original_base, return_only=return_only,
                                activity_completed=s.activity_status == "completed")
        except SearchLimitReachedError as error:
            data["search_metrics"]["generated_labels"] = error.generated_labels
            return result(S.SEARCH_LIMIT_REACHED, "LABEL_LIMIT_REACHED", "Calculo interrumpido; factibilidad desconocida.")
        except NoFeasibleMissionError:
            return result(S.INFEASIBLE, "SEARCH_EXHAUSTED", "Busqueda agotada sin plan con saldo, restricciones y reservas declaradas.")
        proxy = SimpleNamespace(profile=effective, activity_min=s.pending_activity_min,
                                goal=s.goal, base=s.original_base, frame=request.frame)
        data["plan"] = _breakdown(proxy, planner, plan,
                                  include_activity=not return_only and s.activity_status == "pending",
                                  return_only=return_only)
        data["plan"]["budget_semantics"] = "capacity en eventos/total = saldo al solicitar; historico informativo no descontado"
        data["search_metrics"]["generated_labels"] = plan.explored_labels
        return result(S.SUCCESS, "FUTURE_PLAN_FOUND", "Plan futuro admisible en este modelo experimental; sin garantia EVA o evacuacion.")

    except NumericDomainError as error:
        data["plan"] = None
        return result(S.INVALID_INPUT, "NUMERIC_DOMAIN_EXCEEDED", str(error))


COMPARISON_RULE = ("Entre SUCCESS calculados: menor tiempo total, luego menor bateria total, "
                   "luego orden balanced/minimum_time/terrain_caution. No compara costos de pesos distintos. "
                   "Solo alternativas calculadas; sin optimalidad global. Interrupciones conservan factibilidad desconocida.")


def compare_alternatives(request: DecisionRequest) -> DecisionResult:
    alternatives = [plan_future(request, "continue", policy).to_dict() for policy in POLICIES]
    successful = [a for a in alternatives if a["status"] == S.SUCCESS.value]
    chosen = min(successful, key=lambda a: (a["plan"]["total"]["duration_min"],
                                           a["plan"]["total"]["resources"]["battery"]["consumed"],
                                           POLICIES.index(a["policy"]))) if successful else None
    groups = {}
    for a in successful:
        groups.setdefault(tuple(map(tuple, a["plan"]["path"])), []).append(a["policy"])
    return DecisionResult(dict(schema_version=SCHEMA_VERSION, alternatives=alternatives,
                               recommendation=chosen["policy"] if chosen else None,
                               rule=COMPARISON_RULE, coincident_routes=list(groups.values()),
                               distinct_successful_routes=len(groups)))


DECISION_RULE = ("Exigir regreso SUCCESS para recomendar continuar. Si ambos SUCCESS, continuar; "
                 "continuacion INFEASIBLE y regreso SUCCESS, regresar. Continuacion interrumpida: "
                 "factibilidad desconocida y revisar. Regreso sin SUCCESS: revisar sin evacuacion garantizada.")


def evaluate_options(request: DecisionRequest, policy="balanced", *, return_max_labels=None) -> DecisionResult:
    continuing = plan_future(request, "continue", policy)
    returning = plan_future(replace(request, max_labels=return_max_labels) if return_max_labels is not None
                            and type(request) is DecisionRequest else request, "return", policy)
    if continuing.status == S.INVALID_INPUT or returning.status == S.INVALID_INPUT:
        decision = "REVIEW_INVALID_INPUT"
    elif returning.status != S.SUCCESS:
        decision = "REVIEW_RETURN_UNCONFIRMED"
    elif continuing.status == S.SUCCESS:
        decision = "CONTINUE"
    elif continuing.status == S.INFEASIBLE:
        decision = "RETURN"
    else:
        decision = "REVIEW_CONTINUATION_UNKNOWN"
    return DecisionResult(dict(schema_version=SCHEMA_VERSION, decision=decision, rule=DECISION_RULE,
                               continuation=continuing.to_dict(), returning=returning.to_dict(),
                               message="Recomendacion experimental de planificacion; no es un controlador de emergencia ni garantiza evacuacion."))
