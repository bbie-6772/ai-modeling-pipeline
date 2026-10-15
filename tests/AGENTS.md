# Test boundaries

Run from repository root; see docs/testing.md. Behavioral tests belong in unit/,
real Blender tests in integration/, shared synthetic fixtures in fixtures/.
Fixtures must not import test case modules. Never use fixture approvals as human
approval. Integration tests must create temporary scenes and must not load the
user's external projects.
