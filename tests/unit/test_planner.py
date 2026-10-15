"""Offline invariants for the advisory AI asset task planner."""
import json
import tempfile
import unittest
from pathlib import Path

from asset_pipeline.planner import build_plan, check_plan
from asset_pipeline.plan_cli import main

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "templates" / "ai-plan-request.example.json"


def example():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


class AssetPlannerTests(unittest.TestCase):
    def test_all_55_tasks_and_four_unverified_gates(self):
        request = example()
        plan = build_plan(request["specification"], request["planning_options"])
        self.assertTrue(check_plan(plan))
        tasks = [t for t in plan["tasks"] if t["kind"] == "task"]
        gates = [t for t in plan["tasks"] if t["kind"] == "gate"]
        self.assertEqual(len(tasks), 55)
        self.assertEqual(len(gates), 4)
        self.assertEqual(tasks[0]["stage"], "brief-reference")
        self.assertEqual(tasks[-1]["stage"], "in-engine-validation")
        self.assertTrue(all(t["status"] == "unverified" for t in gates))
        self.assertTrue(plan["advisory_only"])
        self.assertFalse(any(t["status"] in ("approved", "PASS", "completed") for t in plan["tasks"]))

    def test_review_gates_precede_protected_actions(self):
        p = build_plan(example()["specification"])
        indexed = {t["id"]: i for i, t in enumerate(p["tasks"])}
        self.assertLess(indexed["G:design-lock"], indexed["T06"])
        self.assertLess(indexed["G:blockout-review"], indexed["T12"])
        self.assertLess(indexed["G:core-shape"], indexed["T21"])
        self.assertLess(indexed["T55"], indexed["G:final"])
        self.assertEqual(p["tasks"][indexed["T21"]]["depends_on"], ["G:core-shape"])

    def test_skips_are_explicit_and_dependencies_never_point_to_skips(self):
        p = build_plan(example()["specification"])
        tasks = {t["id"]: t for t in p["tasks"]}
        self.assertFalse(tasks["T24"]["enabled"])
        self.assertFalse(tasks["T43"]["enabled"])
        self.assertFalse(tasks["T45"]["enabled"])
        self.assertFalse(tasks["T49"]["enabled"])
        self.assertEqual(tasks["T43"]["status"], "skipped-by-plan")
        self.assertTrue(tasks["T44"]["enabled"])
        self.assertTrue(tasks["T53"]["enabled"])
        skipped = {t["id"] for t in p["tasks"] if not t["enabled"]}
        self.assertTrue(all(not skipped.intersection(t["depends_on"]) for t in p["tasks"]))
        self.assertTrue(check_plan(p))

    def test_rigid_rig_and_bake_features_can_be_enabled(self):
        request = example()
        p = build_plan(request["specification"],
                       {"rig_mode": "rigid", "uv_mode": "unwrap", "bake": True})
        tasks = {t["id"]: t for t in p["tasks"]}
        self.assertTrue(tasks["T43"]["enabled"])
        self.assertTrue(tasks["T45"]["enabled"])
        self.assertTrue(tasks["T49"]["enabled"])
        self.assertTrue(check_plan(p))

    def test_reject_invalid_option_combinations(self):
        spec = example()["specification"]
        with self.assertRaisesRegex(ValueError, "Unknown planning option"):
            build_plan(spec, {"unknown": True})
        with self.assertRaisesRegex(ValueError, "Baking requires UV"):
            spec2 = dict(spec, features=dict(spec["features"], textured=False))
            build_plan(spec2, {"bake": True})
        with self.assertRaisesRegex(ValueError, "Textured assets require"):
            build_plan(spec, {"uv_mode": "none"})
        with self.assertRaisesRegex(ValueError, "rig_mode"):
            build_plan(spec, {"rig_mode": "motor"})
        with self.assertRaisesRegex(ValueError, "Deforming assets require"):
            spec2 = dict(spec, features=dict(spec["features"], deforming=True))
            build_plan(spec2, {"rig_mode": "none"})

    def test_not_a_pass_when_artwork_is_unverified(self):
        p = build_plan(example()["specification"])
        self.assertEqual(p["tasks"][0]["status"], "not-executed")
        self.assertFalse(any(node.get("status") == "PASS" for node in p["tasks"]))
        p["tasks"][0]["status"] = "approved"
        # The plan validator specifically prevents passing off gate approval.
        gate = next(t for t in p["tasks"] if t["kind"] == "gate")
        gate["status"] = "approved"
        with self.assertRaisesRegex(ValueError, "cannot declare gate approved"):
            check_plan(p)

    def test_cli_writes_new_file_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            self.assertEqual(main([str(EXAMPLE), "--output", str(path)]), 0)
            self.assertTrue(check_plan(json.loads(path.read_text(encoding="utf-8"))))
            self.assertEqual(main([str(EXAMPLE), "--output", str(path)]), 2)

    def test_sample_run_is_not_modified(self):
        request = example()
        before = json.dumps(request, sort_keys=True)
        build_plan(request["specification"], request["planning_options"])
        self.assertEqual(before, json.dumps(request, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
