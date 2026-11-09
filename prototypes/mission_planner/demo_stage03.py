"""Five small SIMULATED scenarios. --json emits strict result JSON only."""
from dataclasses import replace
import argparse
import json

from mars_route_planner import Terrain
from mars_mission_resources import small_example_profile
from mission_api import MissionRequest, TerrainReference, LocalFrame, plan_mission


def example_request(kind="astronaut"):
    t = Terrain([[0., 0., 0.]], [[False]*3], [[0.]*3], [[0.]*3], 1.)
    return MissionRequest("3.0", "simulated-"+kind, TerrainReference.capture(t, "simulated-corridor"),
                          LocalFrame("LOCAL_GRID_SIMULATED", 1., (0., 0.)),
                          (0, 0), (0, 0), (0, 2), 2., small_example_profile(kind), 100)


def scenarios():
    astronaut = example_request()
    rover = example_request("rover")
    low_resources = dict(rover.profile.resources)
    low_resources["battery"] = replace(low_resources["battery"], capacity=10, reserve=1)
    return {
        "astronaut_success": astronaut,
        "rover_success": rover,
        "insufficient_budget": replace(rover, request_id="simulated-insufficient-budget",
                                       profile=replace(rover.profile, resources=low_resources)),
        "label_limit": replace(rover, request_id="simulated-label-limit", max_labels=1),
        "invalid_request": replace(rover, request_id="simulated-invalid", goal=(0, 3)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    results = {name: plan_mission(req) for name, req in scenarios().items()}
    if args.json:
        print(json.dumps({k: v.to_dict() for k, v in results.items()}, allow_nan=False, indent=2,
                         ensure_ascii=False))
        return
    print("ETAPA 3: escenarios y perfiles SIMULADOS, sin calibracion fisica")
    for name, result in results.items():
        print(f"{name}: {result.status.value} / {result.reason_code}")
        print(" ", result.message)
        print("  Etiquetas generadas:", result.search_metrics["generated_labels"])
        if result.plan:
            total = result.plan["total"]
            print(f"  {total['distance_m']:g} m; {total['duration_min']:g} min; costo {result.plan['cost']:g}")
            for phase, usage in result.plan["phases"].items():
                print(f"  {phase}: {usage['distance_m']:g} m; {usage['duration_min']:g} min")
            for resource, data in total["resources"].items():
                if data["status"] == "modeled":
                    print(f"  {resource}: consumo {data['consumed']:g}; restante {data['remaining']:g}; reserva {data['reserve']:g} {data['unit']}")
                else:
                    print(f"  {resource}: {data['status']}")


if __name__ == "__main__":
    main()
