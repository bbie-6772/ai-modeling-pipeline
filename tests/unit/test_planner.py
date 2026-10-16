"""Offline invariants for the advisory stage checklist."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from asset_pipeline.planner import CONDITIONS, OPERATIONS, build_plan, main
from asset_pipeline.profiles import policy
from asset_pipeline.specification import STAGES

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "templates" / "ai-plan-request.example.json"


def example():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def run_cli(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = main([str(a) for a in argv])
    return code, out.getvalue()


class AssetPlannerTests(unittest.TestCase):
    def test_stages_follow_contract_and_never_carry_results(self):
        plan = build_plan(example()["specification"])
        self.assertEqual([s["stage"] for s in plan["stages"]], list(STAGES))
        self.assertTrue(plan["advisory_only"])
        for stage in plan["stages"]:
            self.assertEqual(set(stage), {"stage", "operations", "skipped", "approvals", "qa_due"})

    def test_qa_due_and_not_applicable_come_from_profile_policy(self):
        spec = example()["specification"]
        plan = build_plan(spec)
        required, exceptions = policy(spec)
        due = [c for s in plan["stages"] for c in s["qa_due"]]
        self.assertEqual(sorted(due), sorted(required))
        self.assertEqual(plan["not_applicable"], exceptions)
        by_stage = {s["stage"]: s for s in plan["stages"]}
        self.assertIn("F01", by_stage["visual-critique-revision"]["qa_due"])
        self.assertEqual(by_stage["game-ready-optimization"]["qa_due"], ["V04"])
        self.assertIn("R03", by_stage["in-engine-validation"]["qa_due"])  # collision enabled

    def test_approvals_match_executor_requirements(self):
        by_stage = {s["stage"]: s["approvals"] for s in build_plan(example()["specification"])["stages"]}
        self.assertEqual(by_stage["brief-reference"], ["design-lock"])
        self.assertEqual(by_stage["visual-critique-revision"], ["design-lock"])
        self.assertEqual(by_stage["detail-procedural"], ["design-lock", "core-shape"])
        self.assertEqual(by_stage["in-engine-validation"], ["design-lock", "core-shape", "final"])

    def test_feature_skips_are_explicit(self):
        self.assertLessEqual(set(CONDITIONS), {op for ops in OPERATIONS.values() for op in ops})
        spec = example()["specification"]
        ready = build_plan(spec)["stages"][6]
        self.assertIn("build_collision", ready["operations"])
        self.assertEqual(ready["skipped"]["build_lods"], "lod")
        self.assertEqual(ready["skipped"]["bake_mesh_maps"], "bake")
        self.assertEqual(ready["skipped"]["create_armature"], "rig")
        rigged = build_plan(spec, {"rig_mode": "rigid", "uv_mode": "unwrap", "bake": True})["stages"][6]
        self.assertIn("create_armature", rigged["operations"])
        self.assertIn("bake_mesh_maps", rigged["operations"])

    def test_reject_invalid_option_combinations(self):
        spec = example()["specification"]
        with self.assertRaisesRegex(ValueError, "Unknown planning option"):
            build_plan(spec, {"unknown": True})
        with self.assertRaisesRegex(ValueError, "Baking requires UV"):
            build_plan(dict(spec, features=dict(spec["features"], textured=False)), {"bake": True})
        with self.assertRaisesRegex(ValueError, "Textured assets require"):
            build_plan(spec, {"uv_mode": "none"})
        with self.assertRaisesRegex(ValueError, "rig_mode"):
            build_plan(spec, {"rig_mode": "motor"})
        with self.assertRaisesRegex(ValueError, "Deforming assets require"):
            build_plan(dict(spec, features=dict(spec["features"], deforming=True)), {"rig_mode": "none"})

    def test_cli_defaults_to_run_stage_and_blocks_bad_input(self):
        code, out = run_cli(EXAMPLE)
        self.assertEqual((code, len(json.loads(out)["stages"])), (0, 8))
        code, out = run_cli(EXAMPLE, "--stage", "detail-procedural")
        self.assertEqual([s["stage"] for s in json.loads(out)["stages"]], ["detail-procedural"])
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run.json"
            run.write_text(json.dumps(dict(example(), stage="proxy-blockout")), encoding="utf-8")
            code, out = run_cli(run)
            self.assertEqual([s["stage"] for s in json.loads(out)["stages"]], ["proxy-blockout"])
            run.write_text(json.dumps(dict(example(), stage="unknown")), encoding="utf-8")
            self.assertEqual(run_cli(run)[0], 2)
            run.write_text("[]", encoding="utf-8")
            self.assertEqual(run_cli(run)[0], 2)

    def test_request_is_not_modified(self):
        request = example()
        before = json.dumps(request, sort_keys=True)
        build_plan(request["specification"], request["planning_options"])
        self.assertEqual(before, json.dumps(request, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
