"""Acceptance tests and an independent complete bounded tiny-grid oracle."""
from dataclasses import replace
import json
import math
import unittest
from unittest.mock import patch

from mars_route_planner import Terrain
from mars_mission_resources import ExcludedResource, ResourceAllocation
from mission_api import (LocalFrame, MissionRequest, MissionStatus as S, TerrainReference,
                         plan_mission)
from demo_stage03 import example_request, scenarios


class StageThree(unittest.TestCase):
    def test_five_scenarios_and_strict_json(self):
        expected = [S.SUCCESS, S.SUCCESS, S.INFEASIBLE, S.SEARCH_LIMIT_REACHED, S.INVALID_INPUT]
        for (name, request), status in zip(scenarios().items(), expected):
            with self.subTest(name=name):
                result = plan_mission(request)
                self.assertEqual(result.status, status)
                encoded = result.to_json()
                data = json.loads(encoded, parse_constant=lambda x: self.fail(x))
                self.assertEqual(data, result.to_dict())
                self.assertEqual(data["request_id"], request.request_id)
                self.assertEqual(data["schema_version"], "3.0")
                self.assertEqual(data["terrain"]["revision_sha256"], request.terrain.revision_sha256)
                self.assertEqual(data["profile"]["parameter_nature"], "simulated")
                if status != S.SUCCESS:
                    self.assertIsNone(data["plan"])

    def test_request_validation(self):
        q = example_request()
        changes = [dict(schema_version="2.0"), dict(request_id=""), dict(terrain=None),
                   dict(frame=None), dict(profile=None), dict(start=(0, 1)), dict(goal=q.base),
                   dict(frame=replace(q.frame, resolution_m=2))]
        for field in ("base", "start", "goal"):
            for cell in ((True, 1), (0, False), (0., 1), (0, 1.2), (0,), [0, 1],
                         (0, -1), (1, 0), (0, 3), None):
                changes.append({field: cell})
        for v in (-1, float("nan"), float("inf"), -float("inf"), True, "2", None):
            changes.append(dict(activity_min=v))
        for v in (0, -1, True, 1.2, None):
            changes.append(dict(max_labels=v))
        for change in changes:
            with self.subTest(change=change), patch("mission_api.ResourceMissionPlanner.from_profile") as factory:
                result = plan_mission(replace(q, **change))
                self.assertEqual(result.status, S.INVALID_INPUT)
                factory.assert_not_called()
        self.assertEqual(plan_mission({}).status, S.INVALID_INPUT)
        with self.assertRaises(TypeError):
            MissionRequest()
        for change in (dict(frame_id=""), dict(coordinate_unit="km"), dict(time_unit="s"),
                       dict(height_unit="km"), dict(y_axis="north"), dict(cell_order="column,row"),
                       dict(origin_location="center"), dict(origin_xy_m=(0, float("nan"))),
                       dict(resolution_m=0)):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(q.frame, **change)
        with self.assertRaises(ValueError):
            TerrainReference.capture(q.terrain.snapshot, "")

    def test_breakdown_accounting_and_reserves(self):
        for kind in ("astronaut", "rover"):
            request = example_request(kind)
            plan = plan_mission(request).plan
            self.assertEqual(plan["path"], [[0,0], [0,1], [0,2], [0,1], [0,0]])
            self.assertEqual(plan["path"][plan["goal_index"]], plan["goal_cell"])
            self.assertEqual(plan["path"][-1], list(request.base))
            events = plan["events"]
            self.assertEqual([e["phase"] for e in events], ["outbound", "outbound", "activity", "inbound", "inbound"])
            science = [e for e in events if e["kind"] == "science"]
            self.assertEqual(len(science), 1)
            self.assertEqual(science[0]["start_cell"], plan["goal_cell"])
            self.assertEqual(science[0]["end_cell"], plan["goal_cell"])
            self.assertEqual(science[0]["distance_m"], 0)
            self.assertEqual(science[0]["incremental"]["battery"], 10)
            self.assertEqual(plan["total"]["duration_min"], 6)
            self.assertEqual(plan["total"]["distance_m"], 4)
            expected = dict(time=6, battery=18, oxygen=10, water=1.2, nutrition=28)
            for name, total in plan["total"]["resources"].items():
                if total["status"] != "modeled":
                    self.assertEqual(total["status"], "not_applicable")
                    for key in ("consumed", "capacity", "remaining", "reserve", "margin_above_reserve"):
                        self.assertIsNone(total[key])
                    for e in events:
                        self.assertIsNone(e["incremental"][name])
                        self.assertIsNone(e["cumulative"][name])
                        self.assertIsNone(e["resources"][name]["remaining"])
                    continue
                self.assertAlmostEqual(total["consumed"], expected[name])
                self.assertAlmostEqual(sum(e["incremental"][name] for e in events), total["consumed"])
                self.assertAlmostEqual(sum(p["consumed"][name] for p in plan["phases"].values()), total["consumed"])
                cumulative = 0
                for e in events:
                    cumulative += e["incremental"][name]
                    self.assertAlmostEqual(e["cumulative"][name], cumulative)
                    resource = e["resources"][name]
                    self.assertAlmostEqual(resource["remaining"], resource["capacity"] - cumulative)
                    self.assertGreaterEqual(resource["remaining"] + 1e-9, resource["reserve"])
                    self.assertAlmostEqual(resource["margin_above_reserve"], resource["remaining"]-resource["reserve"])
            for key in ("duration_min", "distance_m"):
                self.assertAlmostEqual(sum(e[key] for e in events), plan["total"][key])
                self.assertAlmostEqual(sum(p[key] for p in plan["phases"].values()), plan["total"][key])

    def test_zero_activity_and_exact_reserves(self):
        q = example_request()
        zero = plan_mission(replace(q, activity_min=0)).plan
        self.assertEqual(zero["total"]["duration_min"], 4)
        self.assertEqual(zero["phases"]["activity"]["consumed"]["battery"], 0)
        self.assertEqual(sum(e["kind"] == "science" for e in zero["events"]), 1)
        quantities = dict(time=6, battery=18, oxygen=10, water=1.2, nutrition=28)
        p = replace(q.profile, resources={k: replace(v, capacity=quantities[k]+v.reserve)
                                         for k,v in q.profile.resources.items()})
        result = plan_mission(replace(q, profile=p))
        self.assertEqual(result.status, S.SUCCESS)
        for v in result.plan["total"]["resources"].values():
            self.assertAlmostEqual(v["remaining"], v["reserve"])

    def test_explicit_exclusion(self):
        q = example_request()
        p = replace(q.profile, resources=dict(q.profile.resources, oxygen=ExcludedResource("Experimento sin O2")))
        result = plan_mission(replace(q, profile=p)).to_dict()
        self.assertEqual(result["exclusions"]["oxygen"], "Experimento sin O2")
        for record in [result["plan"]["total"]] + result["plan"]["events"]:
            resource = record["resources"]["oxygen"]
            self.assertEqual(resource["status"], "excluded")
            self.assertIsNone(resource["consumed"])
            self.assertIsNone(resource["remaining"])
        self.assertIsNone(result["plan"]["phases"]["activity"]["consumed"]["oxygen"])

    def test_blocked_vs_invalid_and_explanations(self):
        q = example_request("rover")
        t = Terrain([[0.]*3], [[True, False, False]], [[0.]*3], [[0.]*3], 1.)
        blocked = plan_mission(replace(q, terrain=TerrainReference.capture(t, "blocked")))
        self.assertEqual(blocked.status, S.INFEASIBLE)
        self.assertEqual(blocked.reason_code, "ENDPOINT_NOT_TRAVERSABLE")
        self.assertIsNone(blocked.search_metrics["generated_labels"])
        exhausted = plan_mission(scenarios()["insufficient_budget"])
        self.assertEqual(exhausted.reason_code, "SEARCH_EXHAUSTED")
        self.assertIn("no se identifica una causa unica", exhausted.message)
        for word in ("oxigeno", "bateria", "agua"):
            self.assertNotIn(word, exhausted.message)
        limited = plan_mission(replace(q, max_labels=1))
        self.assertEqual(limited.status, S.SEARCH_LIMIT_REACHED)
        self.assertEqual(limited.search_metrics["generated_labels"], 1)
        self.assertIn("desconocida", limited.message)
        self.assertEqual(plan_mission(q).status, S.SUCCESS)
        self.assertEqual(plan_mission(replace(q, goal=(0, 3))).status, S.INVALID_INPUT)

    def test_snapshot_identity_and_local_coordinates(self):
        t = Terrain([[0., .1], [.1, .2]], [[False]*2 for _ in range(2)],
                    [[0.]*2 for _ in range(2)], [[0.]*2 for _ in range(2)], 2.)
        reference = TerrainReference.capture(t, "local")
        self.assertEqual(reference.revision_sha256, TerrainReference.capture(t, "other-id").revision_sha256)
        q = replace(example_request("rover"), terrain=reference, goal=(1, 1),
                    frame=LocalFrame("LOCAL_TEST", 2., (10., -20.)))
        q = replace(q, profile=replace(q.profile, resources={k: replace(v, capacity=100)
                                                           for k, v in q.profile.resources.items()}))
        before = plan_mission(q).to_dict()
        self.assertEqual(before["plan"]["waypoints_xy_m"], [[11., -19.], [13., -17.], [11., -19.]])
        self.assertEqual(before["frame"]["y_axis"], "increasing_row")
        # Independent uphill/downhill arithmetic: diagonal 2*sqrt(2), rise .2.
        self.assertAlmostEqual(before["plan"]["events"][0]["duration_min"], 2*math.sqrt(2)+.4)
        self.assertAlmostEqual(before["plan"]["events"][-1]["duration_min"], 2*math.sqrt(2))
        t.heights_m[0][0] = 10; t.obstacles[1][1] = True; t.resolution_m = 3
        self.assertEqual(plan_mission(q).to_dict(), before)
        self.assertNotEqual(TerrainReference.capture(t, "local").revision_sha256, reference.revision_sha256)
        p = replace(q.profile, motion=replace(q.profile.motion, battery_cost_weight=.2))
        self.assertNotEqual(plan_mission(replace(q, profile=p)).profile["revision_sha256"], before["profile"]["revision_sha256"])

    def test_unexpected_engine_errors_propagate(self):
        with patch("mission_api.ResourceMissionPlanner.plan", side_effect=RuntimeError("implementation failure")):
            with self.assertRaisesRegex(RuntimeError, "implementation failure"):
                plan_mission(example_request())

    def test_independent_tiny_reference(self):
        # Fully enumerated 2x2 flat unobstructed 8-connected grid. Each move >=1 min,
        # activity=1 min, capacity 8 minus reserve 1 -> at most 6 movements.
        # No admissible route can exceed that bound. No engine calls in oracle.
        risk = [[0., .7], [.1, .2]]
        t = Terrain([[0.]*2 for _ in range(2)], [[False]*2 for _ in range(2)],
                    risk, [[0.]*2 for _ in range(2)], 1.)
        q = example_request("rover")
        p = replace(q.profile, resources=dict(time=ResourceAllocation(8, 1, 1, 1),
                                              battery=ResourceAllocation(30, 2, 2, 5)))
        q = replace(q, profile=p, terrain=TerrainReference.capture(t, "tiny-oracle"),
                    goal=(1,1), activity_min=1, max_labels=1000)

        def oracle(battery_capacity):
            costs = []
            def walk(cell, visited, minutes, battery, cost, moves):
                if minutes > 7+1e-9 or battery > battery_capacity-2+1e-9:
                    return
                if cell == (0,0) and visited:
                    costs.append(cost)
                    # All edge costs/resources positive; continuing cannot improve.
                    return
                if moves == 6:
                    return
                for nb in ((0,0),(0,1),(1,0),(1,1)):
                    if nb == cell:
                        continue
                    distance = math.hypot(nb[0]-cell[0], nb[1]-cell[1])
                    science = 1 if nb == (1,1) and not visited else 0
                    wh = 2*distance+5*science
                    hazard = p.mobility.risk_weight*(risk[cell[0]][cell[1]]+risk[nb[0]][nb[1]])/2
                    step_cost = distance*(1+p.motion.hazard_cost_weight*hazard)+science+p.motion.battery_cost_weight*wh
                    walk(nb, visited or nb == (1,1), minutes+distance+science,
                         battery+wh, cost+step_cost, moves+1)
            walk((0,0), False, 0., 0., 0., 0)
            return min(costs) if costs else None

        for capacity in (30, 10):
            profile = replace(p, resources=dict(p.resources, battery=replace(p.resources["battery"], capacity=capacity)))
            reference_cost = oracle(capacity)
            result = plan_mission(replace(q, profile=profile))
            self.assertEqual(result.status == S.SUCCESS, reference_cost is not None)
            if reference_cost is not None:
                self.assertAlmostEqual(result.plan["cost"], reference_cost, places=9)
            else:
                self.assertEqual(result.status, S.INFEASIBLE)


if __name__ == "__main__":
    unittest.main()
