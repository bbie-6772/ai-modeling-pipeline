# Repository operating instructions

This is AI Modeling Pipeline, a project-neutral operating guide and evidence validator for AI-assisted 3D asset creation. Blender-specific examples do not imply other DCC integrations are implemented.

- Reason and perform technical analysis in English; explain outcomes to the user in Korean.
- Read `PIPELINE.md` before continuing modeling or applying this repository to another project. Start a run record from `templates/RUN.md`.
- Direct user instructions and the actual asset project's current scope/approvals take precedence. This repository does not authorize edits to an external asset.
- Distinguish adopted baseline, unadopted preview, and experimental fixture. Do not infer adoption from filename, timestamps, or historical notes.
- Freeze the design and original files. Change only the authorized object set in a new candidate. Preserve rejected/previous versions.
- Analyze each part's reference. Group only verified identical parts; check every member for placement and exceptions.
- Submit reference/40% overlay, assembly context, and representative close-up; expand views when required. Do not hide uncertainty through image warping or camera fitting.
- Source/point approval and final shape approval are separate. Record direct evidence and exact revisions; never invent approval or promote an unapproved candidate.
- Blockout meshes are replaceable proxies, never a shape freeze. Before details, follow docs/surface-reevaluation.md: compare all six surface aspects per scoped part against aligned originals, correct/rebuild existing surfaces, record geometry and renders, report uncertainty, and obtain exact-bundle human core-shape approval. Detail adapters must require pipeline.py exit 0 and detail_allowed=true immediately before execution.
- Reuse available audit/guard helpers after inspecting them. Verify protected objects, input hashes, and reopened candidate files before reporting success.
- `pipeline.py` checks evidence consistency only. Replay and synthetic scripts are experiments, not production modelers or general image-to-3D tools.
- Bind evidence approvals to the named project and design revision. Never reuse another project's approvals or experiment thresholds.
- Keep project-specific replay code under `examples/`. Keep concise experiment conclusions/limits in docs/verification.md; detailed historical runs remain recoverable in Git and are not required reading. Never present them as generic certification.
- Never claim Blender/MCP/Unity/FBX, tests, source accuracy, human-review savings, or token savings without actual evidence.
- No automatic subagent delegation. Low-cost extraction agents are not part of the default workflow.
