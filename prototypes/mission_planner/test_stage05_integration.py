"""New stage 5 modes over the actual CTX crop; no synthetic fallback."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from demo_stage05 import ROOT, real_cases
from mission_decisions import compare_alternatives, evaluate_options, plan_future


class StageFiveRealCTX(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if importlib.util.find_spec("numpy") is None:
            raise unittest.SkipTest("Real stage 5 CTX integration requires optional NumPy; skip cannot satisfy acceptance")
        # Missing product is an error in this explicit integration, never synthetic.
        cls.cases, cls.provenance = real_cases(ROOT/"data/jezero")

    def test_real_continue_return_comparison_and_accounting(self):
        q, _ = self.cases["ctx_nominal"]
        self.assertNotEqual(q.state.current, q.state.original_base)
        with patch("numpy.load", side_effect=AssertionError("Unexpected raster read during search")), \
             patch.object(Path, "read_bytes", side_effect=AssertionError("Unexpected filesystem read")):
            comparison = compare_alternatives(q).to_dict()
            options = evaluate_options(q).to_dict()
        self.assertEqual(options["decision"], "CONTINUE")
        self.assertEqual(self.provenance["terrain_file_sha256"], "18d20b39a680d93addc3c3151bb3f19a5f41fc8f9a170396d4094694bbd76d6b")
        self.assertEqual(self.provenance["input_layer"], "prior")
        for r in comparison["alternatives"]+[options["returning"]]:
            self.assertEqual(r["status"], "SUCCESS")
            self.assertEqual(r["request"]["terrain"]["rows"], 7)
            self.assertEqual(r["request"]["terrain"]["resolution_m"], 4.)
            self.assertEqual(r["plan"]["path"][0], [3, 3])
            self.assertEqual(r["plan"]["path"][-1], [4, 2])
            self.assertEqual(r["request"]["rate_provenance"]["oxygen"]["nature"], "simulated")
            self.assertEqual(r["request"]["terrain"]["revision_sha256"], q.state.terrain_revision_sha256)
            for key, resource in r["plan"]["total"]["resources"].items():
                self.assertAlmostEqual(sum(e["incremental"][key] for e in r["plan"]["events"]), resource["consumed"])
                self.assertGreaterEqual(resource["margin_above_reserve"], -1e-9)
        returning = options["returning"]["plan"]
        self.assertFalse(any(e["kind"] == "science" for e in returning["events"]))
        self.assertEqual(returning["phases"]["outbound"]["duration_min"], 0)

    def test_real_simulated_perturbations_limit_and_traceability(self):
        original = self.cases["ctx_nominal"][0]
        baseline = plan_future(original).to_dict()
        blocked = evaluate_options(self.cases["ctx_obstacle"][0]).to_dict()
        self.assertEqual(blocked["decision"], "RETURN")
        self.assertEqual(blocked["continuation"]["reason_code"], "GOAL_NOT_TRAVERSABLE")
        unknown = evaluate_options(self.cases["ctx_unknown"][0]).to_dict()
        self.assertEqual(unknown["decision"], "REVIEW_RETURN_UNCONFIRMED")
        self.assertEqual(unknown["returning"]["reason_code"], "CURRENT_UNKNOWN")
        limited = evaluate_options(self.cases["ctx_limit"][0]).to_dict()
        self.assertEqual(limited["continuation"]["status"], "SEARCH_LIMIT_REACHED")
        self.assertEqual(limited["returning"]["status"], "SEARCH_LIMIT_REACHED")
        self.assertEqual(limited["continuation"]["search_metrics"]["generated_labels"], 1)
        self.assertNotEqual(original.terrain.revision_sha256, self.cases["ctx_obstacle"][0].terrain.revision_sha256)
        self.assertEqual(plan_future(original).to_dict(), baseline)
        for data in (baseline, blocked, unknown, limited):
            json.loads(json.dumps(data, allow_nan=False), parse_constant=lambda x: self.fail(x))


if __name__ == "__main__":
    unittest.main()
