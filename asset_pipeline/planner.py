"""Read-only stage checklist compiled from the existing contract.

python -m asset_pipeline.planner REQUEST_OR_RUN.json [--stage STAGE|all]

A run.json defaults to its current stage only. Planning never runs Blender, MCP or
an engine, records approval or claims a QA result; python -m asset_pipeline RUN.json
remains the only evidence gate.
"""
import argparse
import json
import sys
from pathlib import Path

from .profiles import policy
from .qa import REQUIRED_STAGE
from .revision import stage_approvals
from .specification import STAGES, validate_spec

# Suggested human/AI operations; none is executable by the bounded vertex adapter.
OPERATIONS = dict(zip(STAGES, (
    ('define_asset_requirements', 'collect_references'),
    ('analyze_shapes', 'choose_modeling_method', 'configure_workspace'),
    ('create_primitives', 'set_dimensions', 'place_primary_volumes', 'adjust_proportions',
     'review_silhouette'),
    ('select_target', 'edit_vertices_edges_faces', 'extrude_faces', 'insert_cuts', 'inset_faces',
     'bevel_edges', 'mirror_geometry', 'join_or_separate_parts', 'review_base_mesh'),
    ('compare_fixed_camera_renders', 'record_qa_verdicts', 'run_issue_loop', 'record_regression'),
    ('locate_detail_areas', 'add_detail_parts', 'cut_holes', 'distribute_repeated_parts',
     'refine_shapes', 'review_detail'),
    ('merge_duplicate_vertices', 'check_face_normals', 'check_topology', 'optimize_polygon_budget',
     'configure_shading', 'set_pivots_and_transforms', 'choose_uv_strategy', 'mark_uv_seams',
     'unwrap_uv', 'measure_uv_distortion', 'arrange_uv_islands', 'pack_uv_islands',
     'create_materials', 'assign_base_colors', 'set_pbr_parameters', 'connect_textures',
     'bake_mesh_maps', 'review_materials', 'define_joint_structure', 'create_armature',
     'parent_bones', 'bind_mesh_or_weights', 'test_joint_motion', 'build_collision',
     'build_lods', 'organize_objects', 'configure_export', 'export_candidate',
     'validate_export_file'),
    ('import_in_engine', 'run_runtime_tests', 'repair_and_finalize'),
)))
CONDITIONS = {
    'distribute_repeated_parts': 'repeated', 'connect_textures': 'textured', 'bake_mesh_maps': 'bake',
    'build_collision': 'collision', 'build_lods': 'lod',
    **dict.fromkeys(('mark_uv_seams', 'unwrap_uv', 'measure_uv_distortion', 'arrange_uv_islands',
                     'pack_uv_islands'), 'uv'),
    **dict.fromkeys(('define_joint_structure', 'create_armature', 'parent_bones',
                     'bind_mesh_or_weights', 'test_joint_motion'), 'rig'),
}


def _options(spec, options):
    if not isinstance(options, dict):
        raise ValueError("options must be an object")
    unknown = set(options) - {"rig_mode", "uv_mode", "bake"}
    if unknown:
        raise ValueError("Unknown planning option: " + ", ".join(sorted(unknown)))
    features = spec["features"]
    rig = options.get("rig_mode", "skinned" if features["deforming"] else "none")
    uv = options.get("uv_mode", "unwrap" if features["textured"] else "none")
    bake = options.get("bake", False)
    if rig not in ("none", "rigid", "skinned"):
        raise ValueError("rig_mode must be none/rigid/skinned")
    if uv not in ("none", "unwrap"):
        raise ValueError("uv_mode must be none/unwrap")
    if type(bake) is not bool:
        raise ValueError("bake must be boolean")
    if features["deforming"] and rig != "skinned":
        raise ValueError("Deforming assets require skinned rig_mode")
    if features["textured"] and uv != "unwrap":
        raise ValueError("Textured assets require uv_mode unwrap")
    if bake and uv == "none":
        raise ValueError("Baking requires UV unwrapping")
    return {"rig_mode": rig, "uv_mode": uv, "bake": bake}


def build_plan(spec, options=None):
    """Per stage: suggested operations, feature skips, approvals and QA that start blocking."""
    validate_spec(spec)
    options = _options(spec, {} if options is None else options)
    required, exceptions = policy(spec)
    enabled = dict(spec["features"], uv=options["uv_mode"] == "unwrap", bake=options["bake"],
                   rig=options["rig_mode"] != "none")
    stages = []
    for index, stage in enumerate(STAGES):
        operations = OPERATIONS[stage]
        stages.append({
            "stage": stage,
            "operations": [op for op in operations if enabled.get(CONDITIONS.get(op), True)],
            "skipped": {op: CONDITIONS[op] for op in operations if not enabled.get(CONDITIONS.get(op), True)},
            "approvals": stage_approvals(index),
            # UNKNOWN for these blocks transition from this stage on (qa.needs_review).
            "qa_due": [c for c in sorted(required) if REQUIRED_STAGE[c] == stage],
        })
    return {
        "plan_version": "2.0", "advisory_only": True,
        "asset_id": spec["asset_id"], "design_revision": spec["design_revision"],
        "profile": spec["profile"], "options": options,
        "not_applicable": exceptions,
        "operation_approvals": {"rebuild": "operation-medium", "destructive": "operation-high"},
        "stages": stages,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Advisory stage checklist; no Blender/MCP calls")
    parser.add_argument("request", type=Path, help="run.json or {specification, planning_options}")
    parser.add_argument("--stage", choices=STAGES + ("all",), help="Default: the input's stage, else all")
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        if not isinstance(request, dict) or not isinstance(request.get("specification"), dict):
            raise ValueError("Expected JSON object with specification")
        plan = build_plan(request["specification"], request.get("planning_options"))
        stage = args.stage or request.get("stage", "all")
        if stage != "all":
            plan["stages"] = [s for s in plan["stages"] if s["stage"] == stage]
            if not plan["stages"]:
                raise ValueError("Unknown stage: " + str(stage))
        print(json.dumps(plan, ensure_ascii=False, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
