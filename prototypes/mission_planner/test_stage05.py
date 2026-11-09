"""Small independent arithmetic/oracle and stage 5 acceptance, no GIS imports."""
from dataclasses import replace
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from demo_stage03 import example_request
from demo_stage05 import make_request, flat_terrain, synthetic_cases, updated_request
from mars_mission_resources import ExcludedResource, small_example_profile
from mission_api import TerrainReference, plan_mission, MissionStatus as S
from mission_decisions import (
    PersonalCharacteristics, RateProvenance, RateScenario, MissionState,
    declared_provenance, nominal_scenario, plan_future, compare_alternatives, evaluate_options,
)


class StageFive(unittest.TestCase):
    def test_personal_validation_and_no_effect(self):
        q = make_request()
        reference = plan_future(replace(q, personal=None)).plan
        for personal in (PersonalCharacteristics(), PersonalCharacteristics(55., 1.5),
                         PersonalCharacteristics(95., 1.9)):
            r = plan_future(replace(q, personal=personal))
            self.assertEqual(r.status, S.SUCCESS)
            self.assertEqual(r.plan, reference)
            self.assertEqual(r.to_dict()["request"]["personal"], vars(personal))
        for key in ("body_mass_kg", "height_m"):
            for v in (-1, 0, True, float("nan"), float("inf"), "1"):
                with self.subTest(key=key, value=v), self.assertRaises(ValueError):
                    PersonalCharacteristics(**{key: v})
        for key in ("age", "biological_sex", "gender_identity"):
            with self.assertRaises(TypeError):
                PersonalCharacteristics(**{key: 30})
        rover = make_request(profile=small_example_profile("rover"))
        self.assertEqual(plan_future(replace(rover, personal=PersonalCharacteristics(70, 1.7))).status, S.INVALID_INPUT)

    def test_provenance_and_conservative_scenario(self):
        q = make_request()
        rates = dict(q.rate_provenance)
        rates["water"] = RateProvenance("measured", "Fictitious instrument fixture", "Synthetic test only, not an actual measurement")
        rates["oxygen"] = RateProvenance("estimated", "Fictitious estimate fixture", "simulated_u, no physiology")
        factors = {k: 1. if k == "time" else 1.1 for k in q.scenario.factors}
        scenario = RateScenario("conservative", factors, "Fictitious sensitivity +10%; no percentile")
        r = plan_future(replace(q, rate_provenance=rates, scenario=scenario)).to_dict()
        self.assertEqual(r["status"], "SUCCESS")
        self.assertEqual(r["request"]["rate_provenance"]["water"]["nature"], "measured")
        self.assertEqual(r["request"]["rate_provenance"]["oxygen"]["nature"], "estimated")
        self.assertEqual(r["request"]["scenario"]["factors"], factors)
        self.assertAlmostEqual(r["plan"]["total"]["resources"]["battery"]["consumed"], 16*1.1)
        self.assertEqual(r["plan"]["total"]["duration_min"], 5)
        factors["battery"] = 99
        rates.clear()
        self.assertEqual(scenario.factors["battery"], 1.1)
        for kw in (dict(name="nominal", factors={"battery": 1.1}),
                   dict(name="conservative", factors={"time": 2}),
                   dict(name="conservative", factors={"battery": .9})):
            with self.assertRaises(ValueError):
                RateScenario(**kw, rationale="test")
        with self.assertRaises(ValueError):
            RateProvenance("guessed", "test", "test")

    def test_state_validation_and_identity(self):
        q = make_request()
        s = q.state
        for changes in (dict(remaining=dict(s.remaining, battery=float("nan"))),
                        dict(remaining=dict(s.remaining, battery=-1)),
                        dict(reserves=dict(s.reserves, water=True)),
                        dict(historical_consumption={"time": float("inf")}),
                        dict(current=(0., 1)), dict(current=(False, 1)), dict(current=[0, 1]),
                        dict(activity_status="completed"), dict(activity_status="unknown")):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(s, **changes)
        for changes in (dict(current=(0, 3)), dict(profile_id="other"), dict(profile_version="other"),
                        dict(profile_revision_sha256="0"*64), dict(terrain_id="other"),
                        dict(terrain_revision_sha256="0"*64), dict(remaining={"time": 8}),
                        dict(remaining=dict(s.remaining, battery=100)),
                        dict(reserves=dict(s.reserves, battery=.1)),
                        dict(historical_consumption={"unknown": 1})):
            with self.subTest(changes=changes):
                r = plan_future(replace(q, state=replace(s, **changes)))
                self.assertEqual(r.status, S.INVALID_INPUT)
                json.loads(r.to_json())
        for changes in (dict(rate_provenance={}), dict(scenario=RateScenario("nominal", {}, "empty")),
                        dict(max_labels=0), dict(max_labels=True), dict(max_labels=float("nan")),
                        dict(max_labels=float("inf")), dict(request_id=float("nan")),
                        dict(schema_version="3.0"), dict(frame=None)):
            r = plan_future(replace(q, **changes))
            self.assertEqual(r.status, S.INVALID_INPUT)
            json.loads(r.to_json(), parse_constant=lambda x: self.fail(x))

    def test_continuation_independent_expected_accounts(self):
        r = plan_future(make_request())
        self.assertEqual(r.status, S.SUCCESS)
        self.assertEqual(r.plan["path"], [[0, 1], [0, 2], [0, 1], [0, 0]])
        # Three 1m moves, 2 minutes science, separate activity rates.
        expected = dict(time=5, battery=16, oxygen=9, water=1.1, nutrition=24)
        for k, value in expected.items():
            self.assertAlmostEqual(r.plan["total"]["resources"][k]["consumed"], value)
        self.assertEqual(r.plan["total"]["distance_m"], 3)

    def test_direct_return_and_base_zero(self):
        q = make_request()
        r = plan_future(q, "return")
        self.assertEqual(r.status, S.SUCCESS)
        self.assertEqual(r.plan["path"], [[0, 1], [0, 0]])
        self.assertIsNone(r.plan["goal_index"])
        self.assertIsNone(r.plan["goal_cell"])
        self.assertEqual([e["phase"] for e in r.plan["events"]], ["inbound"])
        self.assertEqual(r.plan["total"]["resources"]["battery"]["consumed"], 2)
        zero = plan_future(replace(q, state=replace(q.state, current=q.state.original_base)), "return")
        self.assertEqual(zero.status, S.SUCCESS)
        self.assertEqual(zero.plan["path"], [[0, 0]])
        self.assertEqual(zero.plan["cost"], 0)
        self.assertEqual(zero.plan["events"], [])
        self.assertEqual(zero.plan["total"]["duration_min"], 0)
        self.assertTrue(all(r["consumed"] == 0 for r in zero.plan["total"]["resources"].values()))

    def test_completed_and_initial_goal_science_once(self):
        q = make_request()
        complete = replace(q, state=replace(q.state, activity_status="completed", pending_activity_min=0))
        r = plan_future(complete)
        self.assertEqual(r.plan["total"]["resources"]["battery"]["consumed"], 6)
        self.assertFalse(any(e["kind"] == "science" for e in r.plan["events"]))
        initial_goal = plan_future(replace(q, state=replace(q.state, current=q.state.goal)))
        self.assertEqual(initial_goal.plan["goal_index"], 0)
        self.assertEqual(initial_goal.plan["events"][0]["kind"], "science")
        self.assertEqual(initial_goal.plan["total"]["resources"]["battery"]["consumed"], 14)
        self.assertEqual(sum(e["kind"] == "science" for e in initial_goal.plan["events"]), 1)
        zero = plan_future(replace(q, state=replace(q.state, pending_activity_min=0)))
        self.assertEqual(sum(e["kind"] == "science" for e in zero.plan["events"]), 1)

    def test_history_not_debited_reserves_absolute(self):
        q = make_request()
        # Exact balances for continuation + ORIGINAL absolute reserves.
        remaining = dict(time=6, battery=17, oxygen=10, water=1.3, nutrition=25)
        state = replace(q.state, remaining=remaining, historical_consumption={"battery": 2., "time": 1.})
        r = plan_future(replace(q, state=state))
        self.assertEqual(r.status, S.SUCCESS)
        for k, total in r.plan["total"]["resources"].items():
            self.assertAlmostEqual(total["remaining"], q.profile.resources[k].reserve)
            self.assertEqual(total["reserve"], q.profile.resources[k].reserve)
            self.assertEqual(total["capacity"], remaining[k])
        no_history = plan_future(replace(q, state=replace(state, historical_consumption=None)))
        self.assertEqual(r.plan, no_history.plan)
        too_low = replace(state, remaining=dict(remaining, battery=.5))
        self.assertEqual(plan_future(replace(q, state=too_low), "return").to_dict()["reason_code"], "BALANCE_BELOW_RESERVE")
        remaining["battery"] = 999
        self.assertEqual(state.remaining["battery"], 17)

    def test_comparison_common_constraints_and_coincidence(self):
        q = make_request()
        result = compare_alternatives(q).to_dict()
        self.assertEqual(len(result["alternatives"]), 3)
        self.assertEqual(result["recommendation"], "balanced")
        self.assertEqual(result["distinct_successful_routes"], 1)
        self.assertEqual(result["coincident_routes"], [["balanced", "minimum_time", "terrain_caution"]])
        self.assertIn("Solo alternativas calculadas", result["rule"])
        self.assertEqual([a["policy_weights"]["motion"]["hazard_cost_weight"] for a in result["alternatives"]], [2, 0, 4])
        for a in result["alternatives"]:
            self.assertEqual(a["request"], json.loads(json.dumps(q.to_dict(), allow_nan=False)))
            self.assertEqual(sum(e["kind"] == "science" for e in a["plan"]["events"]), 1)
        limited = compare_alternatives(replace(q, max_labels=1)).to_dict()
        self.assertIsNone(limited["recommendation"])
        self.assertTrue(all(a["status"] == "SEARCH_LIMIT_REACHED" for a in limited["alternatives"]))

    def test_preferences_use_computed_metrics(self):
        q, _ = synthetic_cases()["grid_penalty"]
        comparison = compare_alternatives(q).to_dict()
        self.assertGreater(comparison["distinct_successful_routes"], 1)
        chosen = next(a for a in comparison["alternatives"] if a["policy"] == comparison["recommendation"])
        self.assertEqual(chosen["plan"]["total"]["duration_min"],
                         min(a["plan"]["total"]["duration_min"] for a in comparison["alternatives"]))

    def test_new_snapshots_detour_wall_unknown_elevation(self):
        cases = synthetic_cases()
        q = cases["grid_original"][0]
        original = plan_future(q)
        old_hash = q.terrain.revision_sha256
        detour = plan_future(cases["grid_detour"][0])
        self.assertEqual(detour.status, S.SUCCESS)
        self.assertNotIn([3, 3], detour.plan["path"])
        self.assertGreater(detour.plan["total"]["distance_m"], original.plan["total"]["distance_m"])
        for name in ("grid_detour", "grid_wall", "grid_elevation"):
            self.assertNotEqual(cases[name][0].terrain.revision_sha256, old_hash)
        elevated = plan_future(cases["grid_elevation"][0])
        self.assertEqual(elevated.status, S.SUCCESS)
        self.assertNotIn([3, 3], elevated.plan["path"])
        wall = evaluate_options(cases["grid_wall"][0]).to_dict()
        self.assertEqual(wall["decision"], "RETURN")
        self.assertEqual(wall["continuation"]["status"], "INFEASIBLE")
        self.assertEqual(wall["returning"]["status"], "SUCCESS")
        self.assertEqual(q.terrain.revision_sha256, old_hash)
        self.assertEqual(plan_future(q).plan, original.plan)
        stale = replace(q, terrain=cases["grid_detour"][0].terrain)
        self.assertEqual(plan_future(stale).status, S.INVALID_INPUT)

    def test_position_blocked_unknown_no_relocation(self):
        q = make_request()
        for new, code in ((updated_request(q, obstacles=[q.state.current]), "CURRENT_NOT_TRAVERSABLE"),
                          (updated_request(q, unknown=[q.state.current]), "CURRENT_UNKNOWN")):
            for mode in ("continue", "return"):
                r = plan_future(new, mode).to_dict()
                self.assertEqual(r["reason_code"], code)
                self.assertIsNone(r["plan"])
                self.assertEqual(r["request"]["state"]["current"], [0, 1])
        goal_blocked = updated_request(q, obstacles=[q.state.goal])
        self.assertEqual(plan_future(goal_blocked, "return").status, S.SUCCESS)

    def test_decision_infeasible_interrupted_and_no_confirmed_return(self):
        q = make_request()
        self.assertEqual(evaluate_options(q).to_dict()["decision"], "CONTINUE")
        low = replace(q, state=replace(q.state, remaining=dict(q.state.remaining, battery=4)))
        self.assertEqual(evaluate_options(low).to_dict()["decision"], "RETURN")
        limited = replace(q, max_labels=1)
        uncertain = evaluate_options(limited, return_max_labels=5000).to_dict()
        self.assertEqual(uncertain["decision"], "REVIEW_CONTINUATION_UNKNOWN")
        self.assertEqual(uncertain["continuation"]["status"], "SEARCH_LIMIT_REACHED")
        self.assertEqual(uncertain["returning"]["status"], "SUCCESS")
        self.assertEqual(evaluate_options(limited).to_dict()["decision"], "REVIEW_RETURN_UNCONFIRMED")
        no_return = replace(q, state=replace(q.state, remaining=dict(q.state.remaining, battery=1)))
        result = evaluate_options(no_return).to_dict()
        self.assertEqual(result["decision"], "REVIEW_RETURN_UNCONFIRMED")
        self.assertEqual(result["returning"]["status"], "INFEASIBLE")
        self.assertIn("no es un controlador", result["message"])

    def test_events_phases_and_strict_json(self):
        for q, action in synthetic_cases().values():
            for mode in ("continue", "return"):
                r = plan_future(q, mode)
                data = json.loads(r.to_json(), parse_constant=lambda x: self.fail(x))
                self.assertEqual(data["schema_version"], "5.0")
                if r.status != S.SUCCESS:
                    self.assertIsNone(r.plan)
                    continue
                plan = r.plan
                for field in ("duration_min", "distance_m"):
                    self.assertAlmostEqual(sum(e[field] for e in plan["events"]), plan["total"][field])
                    self.assertAlmostEqual(sum(p[field] for p in plan["phases"].values()), plan["total"][field])
                for k, total in plan["total"]["resources"].items():
                    if total["status"] != "modeled":
                        self.assertIsNone(total["consumed"])
                        continue
                    self.assertAlmostEqual(sum(e["incremental"][k] for e in plan["events"]), total["consumed"])
                    self.assertAlmostEqual(sum(p["consumed"][k] for p in plan["phases"].values()), total["consumed"])
                    accum = 0
                    for e in plan["events"]:
                        accum += e["incremental"][k]
                        self.assertAlmostEqual(e["cumulative"][k], accum)
                        self.assertAlmostEqual(e["resources"][k]["remaining"], q.state.remaining[k]-accum)
                        self.assertGreaterEqual(e["resources"][k]["margin_above_reserve"], -1e-9)

    def test_excluded_and_v3_compatibility(self):
        p = small_example_profile("astronaut")
        p = replace(p, resources=dict(p.resources, oxygen=ExcludedResource("Unmodeled fixture")))
        q = make_request(profile=p)
        r = plan_future(q).to_dict()
        self.assertEqual(r["plan"]["total"]["resources"]["oxygen"]["status"], "excluded")
        self.assertIsNone(r["plan"]["total"]["resources"]["oxygen"]["consumed"])
        legacy = example_request()
        self.assertEqual(plan_mission(legacy).schema_version, "3.0")
        self.assertEqual(plan_mission(replace(legacy, start=(0, 1))).status, S.INVALID_INPUT)
        self.assertEqual(plan_future(replace(make_request(), schema_version="3.0")).status, S.INVALID_INPUT)
        with patch("mission_decisions.ResourceMissionPlanner.plan", side_effect=RuntimeError("unexpected")):
            with self.assertRaises(RuntimeError):
                plan_future(make_request())

    def test_independent_small_reference_continue_return(self):
        # Complete graph of four flat cells with 8-neighbor movement. No geometry
        # ambiguity. Enumerate SIMPLE paths separately before/after goal: positive
        # costs/resources mean a cycle within either phase can only worsen a plan.
        cells = ((0, 0), (0, 1), (1, 0), (1, 1))
        risks = {cell: value for cell, value in zip(cells, (0., .6, .2, .1))}
        t = flat_terrain(2, 2)
        t.risk = [[0., .6], [.2, .1]]
        profile = small_example_profile("rover")
        profile = replace(profile, resources={k: replace(v, capacity=30., reserve=1.) for k, v in profile.resources.items()})
        q = make_request(TerrainReference.capture(t, "independent"), profile,
                         base=(0, 0), current=(0, 1), goal=(1, 1), activity=1.)

        def paths(a, b, visited=()):
            if a == b:
                yield (a,)
                return
            for nb in cells:
                if nb != a and nb not in visited:
                    for tail in paths(nb, b, visited+(a,)):
                        yield (a,)+tail

        def oracle(mode, capacity):
            candidates = []
            if mode == "return":
                walks = paths(q.state.current, q.state.original_base)
            else:
                walks = (a+b[1:] for a in paths(q.state.current, q.state.goal)
                         for b in paths(q.state.goal, q.state.original_base))
            for path in walks:
                science = 1 if mode == "continue" else 0
                minutes, battery, cost = science, 5*science, science+profile.motion.battery_cost_weight*5*science
                for a, b in zip(path, path[1:]):
                    d = math.dist(a, b)
                    hazard = profile.mobility.risk_weight*(risks[a]+risks[b])/2
                    minutes += d
                    battery += 2*d
                    cost += d*(1+profile.motion.hazard_cost_weight*hazard)+profile.motion.battery_cost_weight*2*d
                if minutes <= 29+1e-9 and battery <= capacity-1+1e-9:
                    candidates.append(cost)
            return min(candidates) if candidates else None

        for mode in ("continue", "return"):
            for capacity in (30., 4., 1.):
                with self.subTest(mode=mode, capacity=capacity):
                    expected = oracle(mode, capacity)
                    r = plan_future(replace(q, state=replace(q.state, remaining=dict(q.state.remaining, battery=capacity))), mode)
                    self.assertEqual(r.status == S.SUCCESS, expected is not None)
                    if expected is not None:
                        self.assertAlmostEqual(r.plan["cost"], expected, places=9)

    def test_core_without_optional_dependencies(self):
        script = '''
import builtins, sys
original = builtins.__import__
def guarded(name, *args, **kw):
    if name.split('.')[0] in ('numpy','rasterio','pyproj','scipy','matplotlib'):
        raise AssertionError('Optional dependency imported: '+name)
    return original(name, *args, **kw)
builtins.__import__ = guarded
from demo_stage05 import make_request
from mission_decisions import evaluate_options, compare_alternatives
assert evaluate_options(make_request()).to_dict()['decision'] == 'CONTINUE'
assert compare_alternatives(make_request()).to_dict()['distinct_successful_routes'] == 1
print('Stage 5 CORE verified without optional dependencies')
'''
        completed = subprocess.run([sys.executable, "-S", "-c", script],
                                   cwd=Path(__file__).parent, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
