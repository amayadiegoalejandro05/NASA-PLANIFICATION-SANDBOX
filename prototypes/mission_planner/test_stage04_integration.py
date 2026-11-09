"""Mandatory integration with the existing real orbital CTX product.

Skips explicitly when the optional environment or source files are absent; a
skipped integration run is NOT sufficient to close stage 4.
"""
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from demo_stage04 import (BASE, GOAL, DEMO_WINDOW, MAX_LABELS, ROOT,
                           run_scenarios, scenarios, write_evidence)
from jezero_adapter import digest, load_ctx_crop, strict_json
from mission_api import plan_mission


class RealJezeroIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if importlib.util.find_spec("numpy") is None:
            raise unittest.SkipTest("Real Jezero integration requires optional NumPy (requirements-jezero.txt)")
        cls.folder = ROOT/"data/jezero"
        if not all((cls.folder/n).is_file() for n in ("terrain.npz", "metadata.json")):
            raise unittest.SkipTest("Existing real Jezero terrain.npz/metadata.json missing; no synthetic fallback")
        cls.adapted = load_ctx_crop(cls.folder, DEMO_WINDOW)
        cls.records = run_scenarios(cls.adapted)

    def test_existing_product_integrity_shape_crop_and_absolute_heights(self):
        import numpy as np
        a, p = self.adapted, self.adapted.provenance
        self.assertEqual(p["terrain_file_sha256"], "18d20b39a680d93addc3c3151bb3f19a5f41fc8f9a170396d4094694bbd76d6b")
        self.assertEqual(digest((self.folder/"terrain.npz").read_bytes()), p["terrain_file_sha256"])
        self.assertEqual(p["metadata_file_sha256"], digest((self.folder/"metadata.json").read_bytes()))
        self.assertEqual([p["inventory"][k]["shape"] for k in ("prior", "reference", "valid")], [[128, 128]]*3)
        self.assertEqual(p["parent_known_cells"], 16384)
        self.assertEqual(p["parent_unknown_cells"], 0)
        self.assertEqual(p["crop_unknown_cells"], 0)
        self.assertEqual(a.terrain.snapshot.resolution_m, 4.)
        self.assertEqual((a.terrain.snapshot.rows, a.terrain.snapshot.cols), (7, 7))
        with np.load(self.folder/"terrain.npz", allow_pickle=False) as data:
            expected = data["prior"][60:67, 60:67].tolist()
        self.assertEqual([list(row) for row in a.terrain.snapshot.heights_m], expected)
        self.assertEqual(a.terrain.snapshot.heights_m[4][2], -2571.708984375)
        self.assertEqual(a.mapping.cell_jezero(BASE), (-6., -2.))
        self.assertEqual(a.mapping.cell_jezero(GOAL), (2., 6.))
        self.assertEqual(p["coordinates"]["height_offset_applied_m"], 0.)
        self.assertEqual(p["source"]["native_post_spacing_m"], 20)

    def test_ctx_only_payload_and_no_raster_access_from_search(self):
        import numpy as np
        accessed = []
        original = np.lib.npyio.NpzFile.__getitem__
        def guarded(product, key):
            accessed.append(key)
            self.assertEqual(key, "prior")
            return original(product, key)
        with patch.object(np.lib.npyio.NpzFile, "__getitem__", guarded):
            adapted = load_ctx_crop(self.folder, DEMO_WINDOW)
        self.assertEqual(accessed, ["prior"])
        # Once adapted, CORE needs no filesystem/NPZ access whatsoever.
        with patch("numpy.load", side_effect=AssertionError("Search attempted raster access")), \
             patch.object(Path, "read_bytes", side_effect=AssertionError("Search attempted file access")):
            result = plan_mission(scenarios(adapted)["rover_success"])
        self.assertEqual(result.status.value, "SUCCESS")
        p = adapted.provenance
        self.assertEqual(p["input_layer"], "prior")
        for layer in ("reference", "valid"):
            self.assertFalse(p["inventory"][layer]["decoded"])
        for layer in ("risk", "roughness"):
            self.assertIn("Unavailable", p["layers"][layer])
            self.assertTrue(all(v == 0. for row in getattr(adapted.terrain.snapshot, layer) for v in row))
        self.assertIn("not physical absence", p["layers"]["obstacles"])
        self.assertFalse(any(v for row in adapted.terrain.snapshot.obstacles for v in row))

    def test_rover_and_astronaut_success_phases_resources_reserves(self):
        for name in ("rover_success", "astronaut_success"):
            with self.subTest(name=name):
                record = self.records[name]
                result, request = record["result"], record["request"]
                self.assertEqual(result["status"], "SUCCESS")
                self.assertEqual(request["profile"]["parameter_nature"], "simulated")
                self.assertEqual(request["profile"]["version"], "4.0")
                self.assertEqual(request["max_labels"], MAX_LABELS)
                self.assertLessEqual(result["search_metrics"]["generated_labels"], MAX_LABELS)
                plan = result["plan"]
                self.assertEqual(plan["path"][0], list(BASE))
                self.assertEqual(plan["path"][-1], list(BASE))
                self.assertEqual(plan["path"][plan["goal_index"]], list(GOAL))
                self.assertEqual(set(plan["phases"]), {"outbound", "activity", "inbound"})
                self.assertGreater(plan["phases"]["outbound"]["distance_m"], 0.)
                self.assertGreater(plan["phases"]["inbound"]["distance_m"], 0.)
                science = [e for e in plan["events"] if e["kind"] == "science"]
                self.assertEqual(len(science), 1)
                self.assertEqual(science[0]["duration_min"], 2.)
                self.assertEqual(science[0]["incremental"]["battery"], 8.)
                self.assertEqual(science[0]["start_cell"], list(GOAL))
                for key in ("duration_min", "distance_m"):
                    self.assertAlmostEqual(sum(e[key] for e in plan["events"]), plan["total"][key], delta=1e-9)
                    self.assertAlmostEqual(sum(p[key] for p in plan["phases"].values()), plan["total"][key], delta=1e-9)
                for key, total in plan["total"]["resources"].items():
                    if total["status"] == "not_applicable":
                        self.assertEqual(name, "rover_success")
                        self.assertIsNone(total["consumed"])
                        self.assertIsNone(total["remaining"])
                        continue
                    consumed = total["consumed"]
                    self.assertAlmostEqual(sum(e["incremental"][key] for e in plan["events"]), consumed, delta=1e-9)
                    self.assertAlmostEqual(sum(p["consumed"][key] for p in plan["phases"].values()), consumed, delta=1e-9)
                    self.assertAlmostEqual(total["remaining"], total["capacity"]-consumed, delta=1e-9)
                    cumulative = 0.
                    for event in plan["events"]:
                        cumulative += event["incremental"][key]
                        self.assertAlmostEqual(event["cumulative"][key], cumulative, delta=1e-9)
                        r = event["resources"][key]
                        self.assertAlmostEqual(r["remaining"], r["capacity"]-cumulative, delta=1e-9)
                        self.assertGreaterEqual(r["remaining"]+1e-9, r["reserve"])
                        self.assertAlmostEqual(r["margin_above_reserve"], r["remaining"]-r["reserve"], delta=1e-9)

    def test_insufficient_budget_limit_and_invalid_distinct_same_terrain(self):
        expected = dict(insufficient_budget=("INFEASIBLE", "SEARCH_EXHAUSTED"),
                        label_limit=("SEARCH_LIMIT_REACHED", "LABEL_LIMIT_REACHED"),
                        invalid_request=("INVALID_INPUT", "REQUEST_VALIDATION_FAILED"))
        for name, (status, code) in expected.items():
            record = self.records[name]
            self.assertEqual(record["result"]["status"], status)
            self.assertEqual(record["result"]["reason_code"], code)
            self.assertIsNone(record["result"]["plan"])
            self.assertEqual(record["result"]["terrain"], self.records["rover_success"]["result"]["terrain"])
        low = self.records["insufficient_budget"]["request"]
        b = low["profile"]["resources"]["battery"]
        self.assertLess(b["capacity"]-b["reserve"], low["activity_min"]*b["activity_rate"])
        self.assertIsNone(self.records["insufficient_budget"]["result"]["search_metrics"]["generated_labels"])
        limit = self.records["label_limit"]
        self.assertEqual(limit["result"]["search_metrics"]["generated_labels"], 1)
        self.assertEqual(limit["result"]["search_metrics"]["max_labels"], 1)
        sufficient = replace(scenarios(self.adapted)["label_limit"], max_labels=MAX_LABELS)
        self.assertEqual(plan_mission(sufficient).status.value, "SUCCESS")

    def test_strict_json_provenance_waypoints_and_reproducible_exports(self):
        self.assertEqual(self.records, run_scenarios(self.adapted))
        with tempfile.TemporaryDirectory() as tmp:
            write_evidence(self.records, tmp)
            for name, record in self.records.items():
                raw = (Path(tmp)/(name+".json")).read_text(encoding="utf-8")
                data = json.loads(raw, parse_constant=lambda v: self.fail(v))
                self.assertEqual(data, record)
                self.assertEqual(data["request"]["terrain"], data["provenance"]["snapshot"])
                self.assertEqual(data["request"]["frame"], data["provenance"]["coordinates"]["planner_frame"])
                p = dict(data["provenance"])
                identity = p.pop("adaptation_sha256")
                self.assertEqual(identity, digest(strict_json(p).encode("utf-8")))
                for w in data["jezero_waypoints"]:
                    cell = tuple(w["crop_cell"])
                    self.assertEqual(self.adapted.mapping.jezero_to_cell(w["jezero_xy_m"]), cell)
                    self.assertEqual(self.adapted.mapping.planner_to_cell(w["planner_xy_m"]), cell)
                    self.assertEqual(w["product_cell"], list(self.adapted.mapping.to_product_cell(cell)))
                    self.assertEqual(data["result"]["plan"]["waypoints_xy_m"][w["index"]], w["planner_xy_m"])
                if data["result"]["status"] == "SUCCESS":
                    csv = (Path(tmp)/(name+"-waypoints.csv")).read_text(encoding="utf-8")
                    self.assertIn("planner_Y_south_m,jezero_E_m,jezero_N_m,CTX_absolute_elevation_m", csv)


if __name__ == "__main__":
    unittest.main()
