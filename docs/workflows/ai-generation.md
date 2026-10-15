# General AI Game-Asset Generation Pipeline (planning layer v1)

This guide is **asset-agnostic**. It defines the construction order of an AI-assisted
Blender pipeline and an executable **read-only task-plan compiler**. It is not
a general image-to-3D generator. The existing [game-asset v1 contract](../contracts/game-asset-v1.md),
[Surface Gate](../contracts/surface-gate.md), and [modeling workflow](modeling.md)
remain the authoritative approval and QA requirements.

## Current implementation vs intended architecture

| Component | Current status | Next implementation criterion |
|---|---|---|
| Run-level spec, frozen revision, profile, budget, evidence | **Existing** `asset_pipeline/specification.py`, `evidence.py` | Maintain immutable evidence/asset hashes |
| 55-task planning compiler | **Implemented** `asset_pipeline/planner.py` | Emit tasks/skip reasons/ordered gate dependencies |
| Planning-only CLI | **Implemented** `asset_pipeline/plan_cli.py` | JSON output; no Blender edits or approval |
| Part graph & geometric constraints | **Not implemented** | Stable part IDs, transforms, anchors, inferred vs observed geometry |
| Safe parametric operation registry | **Not implemented** | Closed typed commands, declared target-part IDs and deterministic outputs |
| MCP bridge | **Not implemented** | Transport typed commands; no arbitrary Python from untrusted text |
| Geometry/UV/material/bone measurement adapters | **Partial** (existing Blender snapshots / bounded vertex edits) | Repeatable numeric verification and artifact hashes |
| Multi-view visual critique | **Partial** (evidence contract, not automated vision) | Identical cameras, renders, observations and explicit uncertainty |
| Candidate staging/rollback | **Partial** (copy-on-write candidate; no OS sandbox) | Isolated worker, scoped diff, cancel/rollback and timeout reconciliation |
| Engine import/runtime | **Contract only** | Separate Unity/Unreal runner with real import and budget measurements |

No component here may write a human approval, mark a visual score as PASS on
the AI's authority alone, or turn a skipped task into QA evidence.

## User/AI execution sequence

1. **Intake**: gather text brief, reference views, units, target engine, asset
   profile, polygon/material/texture budget, approved revision, and uncertainties.
   Missing values are recorded as unknown, not guessed.
2. **Preflight**: produce a part graph: stable part IDs, relationships,
   visible geometry vs hidden inferred depth, attachment anchors, constraints.
   Validate scope, budgets and source hashes. Obtain the actual design-lock
   before any protected Blender edit.
3. **Plan**: compile the 55-task schedule using `python -m asset_pipeline.plan_cli`.
   Entries identify stage, responsible actor, suggested runtime, verification
   type, explicit feature-based skips and predecessor dependencies.
4. **Blockout**: choose primitives, numerically position parts, capture aligned
   front/side/back/perspective views. Human decides whether the silhouette
   is usable; proxy is not the approved primary shape.
5. **Primary geometry**: select a *bounded* operation (parameterized solid,
   bevel, mirror, extrusion, reusable module), create a fresh candidate,
   record changed object IDs and hashes, then run numeric checks. Repeat only
   on failed operations, never overwrite baseline.
6. **Core-shape gate**: validate faces/curvature/depth/contact/edge shape
   in the established Surface Re-evaluation Gate. Human approval is
   tied to the **exact evidence bundle**; no detail work before the gate.
7. **Detail**: apply repetitive/procedural features from approved parameters.
   Restrict part IDs, re-evaluate adjacent part contacts, preserve unedited objects.
8. **Game-ready**: clean normals/degenerates; check triangle count,
   transforms, pivots; optionally UV, texture, baking, rig and deformation.
   Prefer type-specific recipes; optional tasks are skipped, never auto-passed.
9. **Deliverable**: export fresh FBX/glTF candidate and textures; verify files
   exist, then **re-import in target engine** with actual test scene,
   animation/collision and triangle/material/texture/frame-time measurements.
10. **Review and adoption**: compare with source, collect review artifacts,
    run the existing QA/evidence validation and final human approval.
    Only the approved candidate becomes adopted; preserve previous revisions.

For every failed measurable operation: **detect → localize by part/region →
diagnose → new candidate edit → same-camera re-measure → regression →
human escalation if unresolved**. A tool returning success is *not* evidence
that the art or engine output is correct.

## Mapping to the existing 8-stage workflow

| Existing stage | Task-plan segments |
|---|---|
| `brief-reference` | T01–T02 |
| `reference-decomposition` | T03–T05 |
| `proxy-blockout` | T06–T11 |
| `geometry-reconstruction` | T12–T20 |
| `visual-critique-revision` | `G:core-shape` review checkpoint after T20; must use full Surface Gate contract |
| `detail-procedural` | T21–T26 **after** core-shape |
| `game-ready-optimization` | T27–T52 (cleanup, UV, material, rig, export) |
| `in-engine-validation` | T53–T55, then `G:final` |

The planner inserts `G:design-lock`, `G:blockout-review`,
`G:core-shape` and `G:final`. They are **unverified planning checkpoints**.
`G:blockout-review` is a recommended human review and does not replace the
existing workflow's separate design-lock/core-shape/final approvals.

## Input/output example

```console
python -m asset_pipeline.plan_cli templates/ai-plan-request.example.json --output /tmp/asset-plan.json
python -m unittest tests.unit.test_planner -v
```

The request JSON contains an existing `specification` object with valid
budgets plus optional `planning_options`:

```json
{
  "planning_options": {
    "rig_mode": "none",
    "uv_mode": "unwrap",
    "bake": false
  }
}
```

`rig_mode` is `none`, `rigid`, or `skinned`. Deforming profiles require
`skinned`; `uv_mode` is `none` or `unwrap`; textured profiles
require `unwrap`. Baking requires UV. Defaults derive from the existing
spec features. The tool explicitly skips T24 when no repeated parts,
T34–T38 when no UV, T42 when not textured, T43 without baking, T45–T49
without rig. T33 (strategy selection) remains present.

All emitted active tasks are **not-executed**, all gates **unverified**.
The planner validates inputs and topology of the task dependency chain only,
does not infer a validated design or provide an execution authorization.
Use `python -m asset_pipeline RUN.json` for evidence validation under the
existing approval contracts. No bridge automatically converts plan status
into run-level QA PASS.

## Sequential engineering build plan

| Increment | Deliverable | Acceptance tests |
|---|---|---|
| P0 (this branch) | Machine-readable 55-task plan, conditional tasks, dependency gates, docs, unit tests | Deterministic task count/order; no approvals forged; invalid options refused; no writes to assets |
| P1 | Part graph schema, stable IDs, anchor/constraint validator, source confidence | Schema fixtures; invalid graph and contradictory anchors fail |
| P2 | Typed parametric modeling primitives and Blender candidate worker | Golden shape tests, bounded part allowlist, unaffected object fingerprint equality |
| P3 | Mesh/UV/rig QA measurements + fixed camera captures | Degeneracy/UV distorsion/budget test cases; repeatable same-camera artifact hashes |
| P4 | Revision manager and selective rework loop | Fault injection, no baseline overwrite, stale-result/timeout reconciliation |
| P5 | Controlled MCP transport for those typed operations | Untrusted source cannot request arbitrary code; disconnected/timeout/scope tests |
| P6 | Blender-to-engine export/import with target-engine adapter | Real integration run with measured engine budget and re-import |
| P7 | Quality/latency benchmark harness | Compare human vs AI end-to-end time, repair count, approval rate; unknown costs remain unknown |

### Security and correctness boundaries

- Treat input references, AI model text and MCP replies as **untrusted**.
- Avoid free-form `bpy` execution in a production-facing AI bridge. Prefer
  allowlisted functions, time limits, isolated workers and filesystem boundaries.
- The present trusted adapter is **not** an operating-system sandbox.
- Never infer human approval from JSON fields generated by the LLM.
  Existing approval entries depend on exact bundle hashes, but do not
  authenticate identities.
- Distinguish offline unit tests from real Blender, MCP, or engine integration.
- The example request is synthetic planning data and is **not an approved asset**.
