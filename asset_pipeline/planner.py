"""Read-only, deterministic AI asset production planner.

This module emits a dependency-ordered checklist; it NEVER edits Blender,
runs an MCP tool, grants approval, or claims that a QA check passed.
The existing evidence/approval workflow remains authoritative.
"""
from .specification import STAGES, validate_spec

# Phase | workflow stage | microtasks (the 55 human production operations).
# Code uses stable numerical IDs so execution reports never depend on labels.
PHASES = (
    ("preparation", "reference-decomposition", (
        "define_asset_requirements", "collect_references", "analyze_shapes",
        "choose_modeling_method", "configure_workspace")),
    ("blockout", "proxy-blockout", (
        "create_primitives", "set_dimensions", "place_primary_volumes",
        "adjust_proportions", "review_silhouette", "approve_blockout")),
    ("base_mesh", "geometry-reconstruction", (
        "select_target", "edit_vertices_edges_faces", "extrude_faces",
        "insert_cuts", "inset_faces", "bevel_edges", "mirror_geometry",
        "join_or_separate_parts", "review_base_mesh")),
    ("detail", "detail-procedural", (
        "locate_detail_areas", "add_detail_parts", "cut_holes",
        "distribute_repeated_parts", "refine_shapes", "review_detail")),
    ("cleanup", "game-ready-optimization", (
        "merge_duplicate_vertices", "check_face_normals", "check_topology",
        "optimize_polygon_budget", "configure_shading", "set_pivots_and_transforms")),
    ("uv", "game-ready-optimization", (
        "choose_uv_strategy", "mark_uv_seams", "unwrap_uv",
        "measure_uv_distortion", "arrange_uv_islands", "pack_uv_islands")),
    ("materials", "game-ready-optimization", (
        "create_materials", "assign_base_colors", "set_pbr_parameters",
        "connect_textures", "bake_mesh_maps", "review_materials")),
    ("rig", "game-ready-optimization", (
        "define_joint_structure", "create_armature", "parent_bones",
        "bind_mesh_or_weights", "test_joint_motion")),
    ("export", "game-ready-optimization", (
        "organize_objects", "configure_export", "export_candidate")),
    ("engine", "in-engine-validation", (
        "import_in_engine", "run_runtime_tests", "repair_and_finalize")),
)

# These actions are AI-assisted or must be judged by a human; they are not
# unconditional success events just because a command returned without error.
HUMAN = frozenset({4, 10, 11, 21, 26, 34, 44, 45, 54, 55})
ASSISTED = frozenset({
    1, 2, 3, 9, 13, 14, 15, 16, 19, 20, 22, 23, 25, 29, 30, 32,
    33, 35, 37, 42, 43, 46, 48, 49, 53,
})
# Earlier workflow's verdicts are decision support, not empirical benchmarks.
CONDITIONS = {
    24: "repeated", 34: "uv", 35: "uv", 36: "uv",
    37: "uv", 38: "uv", 42: "textures", 43: "bake",
    45: "rig", 46: "rig", 47: "rig", 48: "rig", 49: "rig",
}
REVIEW_TASKS = frozenset({10, 11, 20, 26, 29, 36, 44, 49, 54, 55})
GATES = (
    ("design-lock", 5, "human", "Existing design-lock evidence approval"),
    ("blockout-review", 11, "human", "Review the proxy; does not approve final shape"),
    ("core-shape", 20, "human", "Existing Surface Re-evaluation Gate and core-shape approval"),
    ("final", 55, "human", "Engine evidence and existing final human approval"),
)


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
    """Produce read-only tasks, explicit skips and non-forgeable-by-planner gates.

    "ready" is deliberately NOT reported: the real executor validates approvals
    against the exact, revision-bound evidence bundle separately.
    """
    validate_spec(spec)
    options = _options(spec, {} if options is None else options)
    enabled = {
        "repeated": spec["features"]["repeated"],
        "uv": options["uv_mode"] == "unwrap",
        "textures": spec["features"]["textured"],
        "bake": options["bake"],
        "rig": options["rig_mode"] != "none",
    }
    gates_at = {after: (name, role, criterion) for name, after, role, criterion in GATES}
    nodes = []
    predecessor = None
    step_id = 0
    for phase, stage, actions in PHASES:
        for action in actions:
            step_id += 1
            task_stage = STAGES[0] if phase == "preparation" and step_id <= 2 else stage
            condition = CONDITIONS.get(step_id)
            active = condition is None or enabled[condition]
            identifier = f"T{step_id:02d}"
            responsibility = ("human" if step_id in HUMAN else
                              "ai-assisted" if step_id in ASSISTED else "deterministic-tool")
            runtime = ("human-review" if responsibility == "human" else
                       "engine-adapter" if phase == "engine" else "blender-adapter"
                       if phase not in ("preparation",) else "planner")
            entry = {
                "id": identifier, "kind": "task", "name": action,
                "phase": phase, "stage": task_stage, "actor": responsibility,
                "suggested_runtime": runtime, "enabled": active,
                "depends_on": [predecessor] if active and predecessor else [],
                "skip_reason": ("Not required by selected feature/options: " + condition)
                               if not active else None,
                "verification": ("human-review-required" if step_id in HUMAN else
                                 "compare-observation-to-asset-spec" if step_id in REVIEW_TASKS else
                                 "record-artifact-and-check-invariants"),
                "status": "not-executed" if active else "skipped-by-plan",
            }
            nodes.append(entry)
            if active:
                predecessor = identifier
            if step_id in gates_at:
                name, role, criterion = gates_at[step_id]
                gate_id = "G:" + name
                nodes.append({
                    "id": gate_id, "kind": "gate", "name": name,
                    "phase": phase, "stage": (STAGES[4] if name == "core-shape" else stage),
                    "actor": role,
                    "suggested_runtime": "evidence-workflow",
                    "enabled": True, "depends_on": [predecessor],
                    "skip_reason": None, "verification": criterion,
                    "status": "unverified",
                })
                predecessor = gate_id
    if step_id != 55:
        raise AssertionError("Unexpected catalog size")
    return {
        "plan_version": "1.0", "asset_id": spec["asset_id"],
        "design_revision": spec["design_revision"],
        "profile": spec["profile"], "target_engine": spec["target_engine"],
        "scope": list(spec["scope"]), "features": dict(spec["features"]),
        "options": options, "core_stages": list(STAGES),
        "advisory_only": True,
        "notes": [
            "Plan generation does not execute Blender/MCP/engine, validate image quality, or grant approval.",
            "Existing run-level evidence, approval, Surface Gate and protected candidate rules remain authoritative.",
            "Skipped task means not applicable, never QA PASS; all actual results start unverified.",
            "Repair failures by making a new candidate and rechecking evidence; never silently mutate the approved baseline.",
        ],
        "tasks": nodes,
    }


def check_plan(plan):
    """Check ordering and gate dependencies without assuming work happened."""
    nodes = plan["tasks"]
    ids = [n["id"] for n in nodes]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate plan nodes")
    previous = set()
    for node in nodes:
        if node["enabled"] and (not node["depends_on"] or node["depends_on"][-1] not in previous):
            if node["id"] != "T01":
                raise ValueError("Broken task dependency: " + node["id"])
        if not set(node["depends_on"]) <= previous:
            raise ValueError("Forward dependency: " + node["id"])
        if node["kind"] == "gate" and node["status"] != "unverified":
            raise ValueError("Plan cannot declare gate approved")
        previous.add(node["id"])
    if [n["id"] for n in nodes if n["kind"] == "task"] != [f"T{i:02d}" for i in range(1, 56)]:
        raise ValueError("Missing task")
    if [n["id"] for n in nodes if n["kind"] == "gate"] != ["G:" + name for name, *_ in GATES]:
        raise ValueError("Missing gate")
    return True
