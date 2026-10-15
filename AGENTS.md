# Agent entry point

Reason in English; explain outcomes in Korean. This repository implements evidence
contracts and a bounded Blender adapter, not general image-to-3D. Read only the
route relevant to the current task; do not scan experiments by default.

| Task | Read first | Entry point |
|---|---|---|
| Start/adapt an asset | README.md, docs/workflows/modeling.md | templates/asset-run.example.json; python -m asset_pipeline RUN.json |
| QA, approval, revision, stage failure | docs/contracts/game-asset-v1.md | asset_pipeline/workflow.py, asset_pipeline/qa.py, asset_pipeline/revision.py |
| Blockout → detail / surface mismatch | docs/contracts/surface-gate.md | asset_pipeline/surface.py |
| Blender edit / snapshot | Surface Gate and executor contracts | asset_pipeline/adapters/blender/ |
| Profile requirements / exceptions | game asset QA section | profiles/assets.json |
| Existing detail-entry/final config | Surface Gate contract | templates/legacy/, asset_pipeline/legacy.py |
| Variant C application | examples/minor-on-air/README.md | named config only |
| Code changes / verification | docs/testing.md | tests/unit/, tests/integration/, tests/fixtures/ |
| Explicit experiment reproduction | experiments/README.md | optional scripts with external inputs |

## Boundaries

- The user's current scope and actual asset project's instructions take precedence.
- Preserve approved design, originals, baseline and previous candidates. Edit only
  approved parts in a new candidate; verify actual hashes and reopened geometry.
- Distinguish adopted baseline, unadopted candidate and synthetic fixture. Never
  infer adoption/approval from filenames, timestamps or a hash calculation.
- Analyze references per part. Group only verified identical parts and verify all
  placements/exceptions; separate observed geometry from inferred depth.
- Blockout is a replaceable proxy. Before detail, verify all six surface aspects,
  aligned before/after renders, actual geometry changes and exact-bundle human
  core-shape approval. Require the selected validator's allowed flag immediately
  before execution. Direct DCC commands do not bypass approval requirements.
- Design/source, core-shape and final approvals are separate. Never invent
  approval, convert UNKNOWN to PASS or change a profile to avoid QA.
- No automatic subagent delegation. A repository task does not authorize modeling
  or replay on the user's external assets.
- Report only executed tests/integrations and measured KPIs. Trusted in-process
  adapters are not an OS sandbox; approval identity is not authenticated.

## Placement

Production imports stay inside asset_pipeline/. Root pipeline.py, surface_gate.py,
blender_surface_snapshot.py and package blender_adapter.py are compatibility
facades; put no new implementation there. Tests/fixtures belong in tests/, optional
research in experiments/, reusable specs in templates/, named cases in examples/,
and live outputs in ignored runs/. Update links/commands after moves and test them.
See [repository map](docs/repository-map.md) for ownership and removal rationale.
