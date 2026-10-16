# AI 3D 모델링 연구 근거와 보완 로드맵

작성 2026-10-16. 로드맵·설계 판단의 근거 문서이며 실행 명령이나 승인 기준이 아니다. 내용은 각 논문 초록·공개 페이지 기준이고 이 저장소에서 재현하지 않았다. 논문 수치를 실제 자산의 품질·시간·token 성과로 옮기지 않는다. 이 문서는 후속 구현 순서의 유일한 출처다.

## 1. 연구 흐름과 시사점

| 흐름 | 대표 자료 | 이 저장소에 주는 시사점 |
|---|---|---|
| 이미지/텍스트 → 3D | TRELLIS, Hunyuan3D 2.0 | 빠른 형상 초안은 가능하나 승인 도면 일치·topology·budget을 보장하지 않음 → 결과는 `blockout` role의 교체 가능한 proxy로만 등록 |
| 파츠 단위 생성 | PartCrafter, MeshCoder | 생성기도 파츠 구조로 이동 → 파츠별 scope·분석 계약과 일치. part ID를 생성·편집·QA의 공통 키로 유지 |
| artist mesh 생성 | MeshAnything, DeepMesh | dense mesh를 적은 face의 artist mesh로 바꾸는 것이 핵심 난제. DeepMesh는 인간 평가와 기하 지표를 함께 사용 → 결정적 기하 지표가 먼저 필요 |
| LLM이 Blender 코드 작성 | LL3M, BlenderAlchemy, MeshCoder | 코드 생성 + render 피드백 루프. 실행 실패·저품질 코드가 흔함 → 임의 Python 대신 part 범위가 선언된 typed operation과 신뢰 adapter |
| 생성기-검증기 루프 | BlenderGym | 최신 VLM도 사람에게 쉬운 Blender 편집에 실패하고, 계산을 생성과 검증에 나누는 방식이 성능을 좌우 → **생성보다 측정 먼저** |
| VLM 평가 | GPTEval3D, 3DGen-Bench | 다시점 RGB·normal render의 쌍대 비교가 인간 선호와 잘 맞지만 기준별 편차가 있음 → AI 평가는 이전 후보 대비 쌍대 비교로 issue(SUSPECT)만 연다 |
| 자동 rig·UV | UniRig, PartUV | AI mesh용 도구가 생김 → 결과도 R01/S03 증거로 검사하며 자동 통과가 아님 |
| 실시간 에셋 표준 | Khronos Asset Creation Guidelines 2.0, glTF Validator, Asset Auditor | 허용 범위를 담은 audit profile이 업계 방식 → glTF export는 Validator 보고서를 measurement 증거로 첨부 |
| 에이전트 context | Anthropic, Effective context engineering | 필요한 것만 필요한 때 읽기 → planner 현재 단계 출력, AGENTS 라우팅, RUN 기록 |

## 2. 보완 사항과 적용 상태

| # | 보완 | 근거 | 상태 |
|---|---|---|---|
| 1 | 단계 체크리스트를 계약 코드에서 계산하고 run의 현재 단계만 출력 | context engineering | 적용: `asset_pipeline/planner.py` |
| 2 | 결정적 mesh hygiene 측정: triangles, boundary/non-manifold/winding 불일치 edge, 퇴화 face, 좌표 중복 vertex | BlenderGym, DeepMesh, MeshAnything | 적용: `surface.topology`, run 결과 `mesh_topology`(판정 아님) |
| 3 | 생성 모델 결과는 `blockout` role 후보로만 사용 | TRELLIS, Hunyuan3D, PartCrafter | 적용: [모델링 절차 4.1](workflows/modeling.md) |
| 4 | 형상 검토에 같은 camera의 shading/normal render, AI 평가는 쌍대 비교로 issue만 | GPTEval3D, 3DGen-Bench | 적용: [모델링 절차 5](workflows/modeling.md) |
| 5 | export 파일 검증(glTF는 Khronos Validator) | Khronos | 적용: planner `validate_export_file` |
| 6 | 아래 3절 항목 | 각 행 근거 | 미적용 |

## 3. 다음 구현 순서 (측정 → 구조 → 실행 → 연결)

1. **고정 camera 캡처**: snapshot exporter 옆에 RGB·normal render adapter를 두고 camera 값과 hash를 증거로 남긴다. 같은 camera 재실행 hash 비교가 통과 기준이다.
2. **파츠 그래프**: part ID ⊆ scope, observed/inferred 구분, 다른 part를 가리키는 anchor, 반복 그룹 멤버 전수 검증. 모순 anchor fixture가 실패해야 한다.
3. **typed operation**: `vertex-edits-v1`처럼 kind별 schema, 대상 part allowlist, 결정적 출력(bevel/mirror/extrude 등). LLM 텍스트나 생성 코드를 직접 실행하지 않는다.
4. **AI critic 연결**: 이전 후보와 같은 camera 쌍대 비교, 출력은 issue(SUSPECT)로만. 인간 판정과의 일치율을 별도 KPI로 측정한다.
5. **외부 연결**: 인증된 승인 store, 위 operation만 전달하는 MCP transport(timeout 후 실제 반영 확인), Unity/Unreal runner와 engine report 생성.
6. **실제 자산 benchmark**: profile별 held-out 자산으로 인간 대비 시간·수정 횟수·승인률을 측정하고 token은 실측만 기록한다.

## 출처

- [TRELLIS: Structured 3D Latents (arXiv 2412.01506)](https://arxiv.org/abs/2412.01506)
- [Hunyuan3D 2.0 (arXiv 2501.12202)](https://arxiv.org/abs/2501.12202)
- [PartCrafter (arXiv 2506.05573)](https://arxiv.org/abs/2506.05573)
- [MeshCoder (arXiv 2508.14879)](https://arxiv.org/abs/2508.14879)
- [MeshAnything (arXiv 2406.10163)](https://arxiv.org/abs/2406.10163)
- [DeepMesh (arXiv 2503.15265)](https://arxiv.org/abs/2503.15265)
- [LL3M: Large Language 3D Modelers (arXiv 2508.08228)](https://arxiv.org/abs/2508.08228)
- [BlenderAlchemy (arXiv 2404.17672)](https://arxiv.org/abs/2404.17672)
- [BlenderGym (arXiv 2504.01786)](https://arxiv.org/abs/2504.01786)
- [GPTEval3D: GPT-4V(ision) is a Human-Aligned Evaluator for Text-to-3D (arXiv 2401.04092)](https://arxiv.org/abs/2401.04092)
- [3DGen-Bench (arXiv 2503.21745)](https://arxiv.org/abs/2503.21745)
- [UniRig (arXiv 2504.12451)](https://arxiv.org/abs/2504.12451)
- [PartUV (arXiv 2511.16659)](https://arxiv.org/abs/2511.16659)
- [Khronos Asset Creation Guidelines 2.0](https://www.khronos.org/blog/introducing-asset-creation-guidelines-2.0-siggraph-2025)
- [Khronos glTF Asset Auditor](https://www.khronos.org/blog/khronos-gltf-asset-auditor)
- [Anthropic, Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
