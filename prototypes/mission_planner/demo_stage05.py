"""Finite, predeclared stage 5 evaluation. No tuning loop or limit increases.

Synthetic line 1x3 (1 m) and 7x7 (1 m); real CTX crop 7x7 (4 m).
Limits: 5000 per search, explicit interruption case 1. One measured run/case.
tracemalloc measures Python allocations, NOT all process/native memory.
"""
from dataclasses import replace
from pathlib import Path
import argparse
import json
import platform
import time
import tracemalloc

from mars_route_planner import Terrain
from mars_mission_resources import small_example_profile
from mission_api import LocalFrame, TerrainReference
from mission_decisions import (
    DecisionRequest, MissionState, PersonalCharacteristics, RateScenario,
    declared_provenance, nominal_scenario, compare_alternatives, evaluate_options,
)

MAX_LABELS = 5000
ROOT = Path(__file__).resolve().parents[2]


def flat_terrain(rows, cols):
    return Terrain([[0.]*cols for _ in range(rows)], [[False]*cols for _ in range(rows)],
                   [[0.]*cols for _ in range(rows)], [[0.]*cols for _ in range(rows)], 1.)


def make_request(terrain=None, profile=None, *, base=(0, 0), current=(0, 1), goal=(0, 2),
                 activity=2., frame=None):
    terrain = terrain or TerrainReference.capture(flat_terrain(1, 3), "synthetic-line")
    profile = profile or small_example_profile("astronaut")
    frame = frame or LocalFrame("SYNTHETIC_LOCAL", terrain.snapshot.resolution_m, (0., 0.))
    return DecisionRequest("5.0", "stage05-"+terrain.terrain_id, terrain, frame, profile,
                           MissionState.capture("fictitious-01", terrain, profile, base, current, goal, activity),
                           declared_provenance(profile, "simulated"), nominal_scenario(profile), MAX_LABELS,
                           PersonalCharacteristics(72., 1.75) if profile.agent_type == "astronaut" else None)


def updated_request(request, *, obstacles=(), unknown=(), elevations=()):
    """New immutable snapshot, same grid/frame. Simulated perturbations only.

    Old request/snapshot retained. Updating the revision is an explicit caller
    action; no in-flight mutation or claim that these changes were observed.
    """
    t = request.terrain.snapshot
    data = {k: [list(row) for row in getattr(t, k)]
            for k in ("heights_m", "obstacles", "risk", "roughness")}
    for r, c in obstacles:
        data["obstacles"][r][c] = True
    for r, c in unknown:
        data["heights_m"][r][c] = None
    for r, c, h in elevations:
        data["heights_m"][r][c] = h
    terrain = TerrainReference.capture(Terrain(**data, resolution_m=t.resolution_m), request.terrain.terrain_id)
    return replace(request, terrain=terrain, state=replace(request.state, terrain_revision_sha256=terrain.revision_sha256))


def synthetic_cases():
    line = make_request()
    low = replace(line, state=replace(line.state, remaining=dict(line.state.remaining, battery=4.)))
    complete = replace(line, state=replace(line.state, activity_status="completed", pending_activity_min=0.))
    at_goal = replace(line, state=replace(line.state, current=line.state.goal))
    at_base = replace(line, state=replace(line.state, current=line.state.original_base))
    p = small_example_profile("rover")
    p = replace(p, resources={k: replace(v, capacity=100., reserve=1.) for k, v in p.resources.items()})
    grid = make_request(TerrainReference.capture(flat_terrain(7, 7), "synthetic-grid"), p,
                        base=(3, 0), current=(3, 1), goal=(3, 5), activity=1.)
    # Synthetic penalty available only here; no such layer is invented for CTX.
    t = flat_terrain(7, 7)
    for c in (2, 3, 4):
        t.risk[3][c] = 1.
    penalty = make_request(TerrainReference.capture(t, "synthetic-penalty"), p,
                           base=(3, 0), current=(3, 1), goal=(3, 5), activity=1.)
    conservative = replace(line, scenario=RateScenario("conservative",
                           {k: 1. if k == "time" else 1.2 for k in line.scenario.factors},
                           "Sensibilidad ficticia +20% en tasas de recursos salvo tiempo"))
    return dict(line_nominal=(line, "evaluate"), line_conservative=(conservative, "evaluate"),
                line_completed=(complete, "evaluate"), line_at_goal=(at_goal, "evaluate"),
                line_at_base=(at_base, "evaluate"), line_low=(low, "evaluate"),
                line_limit=(replace(line, max_labels=1), "evaluate"),
                line_unknown=(updated_request(line, unknown=[(0, 1)]), "evaluate"),
                grid_original=(grid, "compare"), grid_detour=(updated_request(grid, obstacles=[(3, 3)]), "compare"),
                grid_wall=(updated_request(grid, obstacles=[(r, 3) for r in range(7)]), "evaluate"),
                grid_elevation=(updated_request(grid, elevations=[(3, 3, 10.)]), "compare"),
                grid_penalty=(penalty, "compare"))


def real_cases(data_folder):
    from demo_stage04 import DEMO_WINDOW, demo_profile
    from jezero_adapter import load_ctx_crop
    adapted = load_ctx_crop(data_folder, DEMO_WINDOW)
    q = make_request(adapted.terrain, demo_profile("astronaut"), base=(4, 2), current=(3, 3),
                     goal=(2, 4), activity=2., frame=adapted.frame)
    return (dict(ctx_nominal=(q, "compare"),
                 ctx_obstacle=(updated_request(q, obstacles=[(2, 4)]), "evaluate"),
                 ctx_unknown=(updated_request(q, unknown=[(3, 3)]), "evaluate"),
                 ctx_limit=(replace(q, max_labels=1), "evaluate")), adapted.provenance)


def individual_results(payload):
    return payload.get("alternatives", [payload["continuation"], payload["returning"]]
                       if "continuation" in payload else [])


def run_evaluation(data_folder):
    # All cases/sizes/limits declared before the first search, including CTX.
    real, provenance = real_cases(data_folder)
    cases = dict(synthetic_cases(), **real)
    records = {}
    for name, (q, action) in cases.items():
        tracemalloc.start()
        start = time.perf_counter()
        payload = (compare_alternatives(q) if action == "compare" else evaluate_options(q)).to_dict()
        elapsed = time.perf_counter()-start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        records[name] = dict(request=q.to_dict(), result=payload,
                             runtime_seconds=elapsed, peak_python_allocations_bytes=peak,
                             metrics_scope="Whole compare/evaluate call including validation, snapshot hashes and JSON copies; no CTX load",
                             source_provenance=provenance if name.startswith("ctx_") else None,
                             perturbation="SIMULATED scenario change, not a scientific observation"
                             if any(x in name for x in ("obstacle", "unknown", "detour", "wall", "elevation")) else None,
                             search_runs=[dict(mode=r["mode"], policy=r["policy"], status=r["status"],
                                               **r["search_metrics"]) for r in individual_results(payload)])
    return dict(evidence_schema="stage05-evaluation-1", python=platform.python_version(),
                platform=platform.platform(), repetitions=1, cases=records,
                memory_scope="tracemalloc: Python allocations only, not total process/native memory",
                fixed_limits="5000 per search; interruption fixtures 1; no automatic retries or tuning")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT/"data/jezero")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = run_evaluation(args.data)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/"evaluation.json").write_text(json.dumps(records, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    lines = ["Stage 5 fixed evaluation; one run/case; Python allocations only."]
    for name, record in records["cases"].items():
        states = ", ".join(r["policy"]+"/"+r["mode"]+":"+r["status"] for r in record["search_runs"])
        lines.append(f"{name}: {record['runtime_seconds']:.6f} s; {record['peak_python_allocations_bytes']} bytes; {states}")
    summary = "\n".join(lines)+"\n"
    (args.output/"summary.txt").write_text(summary, encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
