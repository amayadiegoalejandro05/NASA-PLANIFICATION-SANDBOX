"""Reproduce bounded missions over the existing public CTX prior, without the pilot.

Run with the optional NumPy environment. All budgets/rates/targets are simulated,
fixed before running, and independent of the held-out HiRISE reference.
"""
from dataclasses import replace
from pathlib import Path
import argparse
import csv
import io
import json
import platform

from jezero_adapter import CropWindow, load_ctx_crop
from mars_mission_resources import AgentProfile, Mobility, MotionModel, ResourceAllocation
from mission_api import MissionRequest, plan_mission

ROOT = Path(__file__).resolve().parents[2]
DEMO_WINDOW = CropWindow(60, 60, 7, 7)
BASE = (4, 2)
GOAL = (2, 4)
ACTIVITY_MIN = 2.
MAX_LABELS = 5000


def demo_profile(kind):
    if kind not in ("rover", "astronaut"):
        raise ValueError("Expected rover or astronaut")
    resources = dict(time=ResourceAllocation(60., 5., 1., 1.),
                     battery=ResourceAllocation(100., 10., 2., 4.))
    if kind == "astronaut":
        resources.update(oxygen=ResourceAllocation(20., 2., .25, .3),
                         water=ResourceAllocation(2., .2, .01, .02),
                         nutrition=ResourceAllocation(200., 20., 4., 5.))
    mobility = Mobility(agent_radius_m=.6 if kind == "rover" else .35,
                        safety_margin_m=.2 if kind == "rover" else .15,
                        max_slope_deg=18. if kind == "rover" else 15.,
                        near_obstacle_m=0., risk_weight=0., roughness_weight=0.,
                        proximity_weight=0.)
    return AgentProfile(kind, "sim-jezero-ctx-"+kind, "4.0", "simulated",
                        "Stage 4 fixed arithmetic demonstration configuration; not fitted to measurements or run outcomes",
                        "Uncalibrated mobility, capacities and consumption; no physical or EVA certification; oxygen in simulated_u",
                        mobility, MotionModel(4., roughness_speed_penalty=0., climb_battery_wh_per_m=.5),
                        resources)


def scenarios(adapted):
    def request(kind):
        return MissionRequest("3.0", "jezero-ctx-"+kind, adapted.terrain, adapted.frame,
                              BASE, BASE, GOAL, ACTIVITY_MIN, demo_profile(kind), MAX_LABELS)
    rover = request("rover")
    # Usable battery 5 Wh < stationary science alone 2 min * 4 Wh/min = 8 Wh.
    # This proves infeasibility independently of the chosen route or elevation.
    low = replace(rover.profile, profile_id=rover.profile.profile_id+"-insufficient",
                  resources=dict(rover.profile.resources,
                                 battery=replace(rover.profile.resources["battery"], capacity=6., reserve=1.)))
    return dict(rover_success=rover, astronaut_success=request("astronaut"),
                insufficient_budget=replace(rover, request_id="jezero-ctx-insufficient", profile=low),
                label_limit=replace(rover, request_id="jezero-ctx-label-limit", max_labels=1),
                invalid_request=replace(rover, request_id="jezero-ctx-invalid", goal=(7, 4)))


def run_scenarios(adapted):
    import numpy as np
    records = {}
    for name, request in scenarios(adapted).items():
        result = plan_mission(request).to_dict()
        waypoints = []
        if result["plan"]:
            for i, cell in enumerate(result["plan"]["path"]):
                cell = tuple(cell)
                waypoints.append(dict(index=i, crop_cell=list(cell),
                                      product_cell=list(adapted.mapping.to_product_cell(cell)),
                                      planner_xy_m=list(adapted.mapping.cell_planner(cell)),
                                      jezero_xy_m=list(adapted.mapping.cell_jezero(cell)),
                                      ctx_elevation_m=adapted.terrain.snapshot.heights_m[cell[0]][cell[1]]))
        records[name] = dict(evidence_schema="stage04-jezero-mission-1",
                             runtime=dict(python=platform.python_version(), numpy=np.__version__),
                             provenance=adapted.provenance,
                             request=dict(schema_version=request.schema_version, request_id=request.request_id,
                                          terrain=result["terrain"], frame=result["frame"], profile=result["profile"],
                                          base=list(request.base), start=list(request.start), goal=list(request.goal),
                                          activity_min=request.activity_min, max_labels=request.max_labels),
                             result=result, jezero_waypoints=waypoints,
                             selection="Fixed crop [60:67,60:67], base (4,2), goal (2,4); demonstration locations, not detected science sites")
    return records


def summary(records):
    coordinates = next(iter(records.values()))["provenance"]["coordinates"]
    left, _, _, top, _, _ = coordinates["crop_affine_gdal"]
    lines = ["ETAPA 4 — Jezero CTX / Mission Planner", "",
             "Terreno orbital real MRO/CTX: informacion nativa 20 m sobre reticula de 4 m.",
             "Prior experimental con conocimiento local incompleto; no certifica el detalle de 4 m.",
             "Objetivos y perfiles SIMULADOS; sin validacion fisica/EVA ni informacion local de obstaculos.",
             "No se leyeron alturas HiRISE, mascara conjunta ni origin_z_m para planificar.",
             "Ventana fija filas [60,67), columnas [60,67): 7x7, 28x28 m; sin remuestreo.",
             "Base producto (64,62), objetivo (62,64). Ciencia estacionaria 2 min.",
             "Marcos: planner X este/Y sur, origen esquina NW del recorte; Jezero E este/N norte.",
             f"E={left:g}+X; N={top:g}-Y (m). Alturas CTX absolutas, desplazamiento vertical aplicado 0 m.",
             "Limite suficiente 5000 etiquetas; prueba de interrupcion 1; no mide expansiones.",
             "Bateria insuficiente: 5 Wh utilizables < 8 Wh de ciencia, antes de movimientos.", ""]
    for name, record in records.items():
        result = record["result"]
        lines.append(f"{name}: {result['status']} / {result['reason_code']}; etiquetas={result['search_metrics']['generated_labels']}")
        if result["plan"]:
            plan, total = result["plan"], result["plan"]["total"]
            lines.append(f"  {total['distance_m']:.9f} m; {total['duration_min']:.9f} min; costo {plan['cost']:.9f}")
            for phase, data in plan["phases"].items():
                lines.append(f"  {phase}: {data['distance_m']:.9f} m; {data['duration_min']:.9f} min")
            for resource, data in total["resources"].items():
                lines.append(f"  {resource}: consumo={data['consumed']}, restante={data['remaining']}, reserva={data['reserve']} {data['unit']} ({data['status']})")
        lines.append("  " + result["message"])
    return "\n".join(lines)+"\n"


def write_evidence(records, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name, record in records.items():
        (output/(name+".json")).write_text(json.dumps(record, ensure_ascii=True, indent=2,
                                                     allow_nan=False)+"\n", encoding="utf-8")
        if record["jezero_waypoints"]:
            stream = io.StringIO(newline="")
            writer = csv.writer(stream)
            writer.writerow(["index", "crop_row", "crop_column", "product_row", "product_column",
                             "planner_X_east_m", "planner_Y_south_m", "jezero_E_m", "jezero_N_m",
                             "CTX_absolute_elevation_m"])
            for w in record["jezero_waypoints"]:
                writer.writerow([w["index"], *w["crop_cell"], *w["product_cell"],
                                 *w["planner_xy_m"], *w["jezero_xy_m"], w["ctx_elevation_m"]])
            (output/(name+"-waypoints.csv")).write_text(stream.getvalue(), encoding="utf-8", newline="")
    (output/"summary.txt").write_text(summary(records), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT/"data/jezero")
    parser.add_argument("--output", type=Path, help="Write five reproducible JSON records, successful waypoint CSVs and summary")
    parser.add_argument("--json", action="store_true", help="Emit strict JSON instead of the readable summary")
    args = parser.parse_args()
    adapted = load_ctx_crop(args.data, DEMO_WINDOW)
    records = run_scenarios(adapted)
    if args.output:
        write_evidence(records, args.output)
    print(json.dumps(records, allow_nan=False, indent=2) if args.json else summary(records), end="\n")
    expected = ["SUCCESS", "SUCCESS", "INFEASIBLE", "SEARCH_LIMIT_REACHED", "INVALID_INPUT"]
    if [r["result"]["status"] for r in records.values()] != expected:
        raise SystemExit("Unexpected demonstration status; records retained, do not reinterpret failure")


if __name__ == "__main__":
    main()
