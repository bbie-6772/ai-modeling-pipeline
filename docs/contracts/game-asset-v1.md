# 범용 AI 게임 3D 에셋 제작 파이프라인 v1.0

Schema version: `1.0`. 공통 계약과 사례를 분리한 evidence workflow다. QA 항목은 F4 + V4 + S3 + R3 + I2 = **16개**다.

## 구성과 실행

| Core Pipeline | 구현 | 실제 역할 |
|---|---|---|
| Asset Specification | `asset_pipeline/specification.py`, `evidence.py` | 고정 설계 revision·제약·scope·엔진·feature·budget, 등록 파일 hash |
| Modeling Executor | `executor.py`, `adapters/blender/adapter.py`, `adapters/blender/worker.py` | gate → 새 후보 복사 → 신뢰하는 adapter → 보호 입력 hash 검사 → 미채택 receipt |
| Visual QA Engine | `qa.py`, `asset_pipeline/surface.py` | 판정·관측·근거·candidate hash·엔진 budget의 일관성 검사. 이미지 판독/자동 미학 점수 아님 |
| Revision & Approval Manager | `revision.py`, `workflow.py` | 단계, 승인, Detect→Diagnose→Repair→Verify, geometry delta, 회귀, KPI |

Asset Profiles는 `profiles/assets.json`에 독립된 데이터로 둔다. 공통 코어가 특정 캐릭터 이름·좌표·threshold를 알지 않는다. 기존 CLI/import 진입점은 호환용 facade로 유지한다. 실제 구현은 패키지 안에 있고 실험 코드는 `experiments/`에 분리한다.

```console
python -m asset_pipeline templates/asset-run.example.json
python -m asset_pipeline runs/my-run.json
python -m asset_pipeline runs/my-run.json --blender "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" --output candidates/revision-02.blend
python -m unittest -v
```

템플릿은 미승인·자료 없음·budget unknown이므로 exit 2로 차단된다. run 파일의 부모가 경로 root다. 모든 assets/receipt/candidate 경로는 이 root 안에 둔다. 등록 assets는 `{path, role, sha256}`이며 실제 파일과 일치해야 한다. `.blend` 원본·이전 후보·증거를 덮어쓰지 않는다. CLI는 기본적으로 읽기 전용이다. `--blender`와 `--output`을 함께 주었을 때만 명시된 새 복사본을 수정한다. Python 3.11 이상, 표준 라이브러리만 사용한다.

## 8단계와 단계 전환 계약

`stage`는 지금 평가/실행하는 단계다. `completed_stages`에는 그 앞 단계들이 정확한 순서로 한 번씩 있어야 한다. 각 record에 `stage`, `summary`, 등록 파일 `evidence` 목록이 필요하다. 선언된 증거의 일관성 검사이며 앞 단계 작업을 자동 수행하거나 그 의미를 인증하지 않는다.

| 순서 | stage | 산출물과 실행 계획 |
|---|---|---|
| 1 Brief/Reference | `brief-reference` | 고정 설계·원본·baseline/candidate 분리, 단위·scope·예산·엔진 명시, design-lock 인간 승인 |
| 2 Reference Decomposition | `reference-decomposition` | 파츠·뷰·직접 관측/깊이 추정·가림·반복 예외·접합 앵커 기록 |
| 3 Proxy Blockout | `proxy-blockout` | 교체 가능한 proxy, 비율/조립/접지 검토. proxy를 확정 형상으로 승인하지 않음 |
| 4 Geometry Reconstruction | `geometry-reconstruction` | 실제 면 방향·곡률·깊이 재구성, 기존 면 변경 delta, 보호 scope 검사 |
| 5 Visual Critique & Revision | `visual-critique-revision` | 엔진 항목 외 QA 판정, issue loop, 전후 비교·geometry 이력·회귀. 미해결 이슈가 있어도 이 단계의 repair 실행은 가능 |
| 6 Detail/Procedural | `detail-procedural` | **Surface Re-evaluation Gate와 핵심 형상 인간 승인 필수**, 모두 통과한 뒤 detail 작업 |
| 7 Game-Ready Optimization | `game-ready-optimization` | topology/normal, UV, scale/pivot, rig, collision/LOD, texture/material 예산 |
| 8 In-Engine Validation | `in-engine-validation` | 목표 엔진에서 import/runtime 보고서와 실측 budget, 별도 최종 인간 승인 |

단계 5부터 비엔진 항목의 `FAIL/SUSPECT/UNKNOWN`은 전환을 막는다. I01/I02는 단계 8에서 필수다. 그 전에는 engine 미실행을 UNKNOWN으로 보존한다. 단계 6 이후 기존 Surface Gate의 모든 파츠·6개 표면 항목·정렬된 전후 렌더·world snapshot·edit/rebuild/retain·기존 면 수정 검사를 그대로 사용한다. `surface_review` 필드는 [기존 계약](surface-gate.md)을 따른다. 새 run의 project/design_revision/scope/assets로 SRG bundle을 구성한다. 마지막 revision의 after snapshot이 SRG after snapshot과 같아야 한다. SRG 승인과 코어의 core-shape 승인 모두 필요하다.

`transition_allowed=true`는 증거 계약을 통과했다는 뜻이다. `execution_allowed`는 adapter 실행 가능 여부이며 단계 5에서는 repair를 위해 transition과 다를 수 있다. `detail_allowed=true`는 단계 6 이후 필수 조건을 만족했을 때만 나온다. `model_validation=not_run`, `design_conformance=not_evaluated`는 validator가 직접 형상/엔진을 실행하지 않았다는 뜻이며 QA record의 선언과 구분한다. `mesh_topology`는 마지막 revision after snapshot의 파츠별 triangles, boundary/non-manifold/winding 불일치 edge, 퇴화 face, 좌표 중복 vertex 수다. 측정값일 뿐 S01 판정이나 전환 조건이 아니며, 의도한 open shell·접촉 object는 설계 근거로 설명한다. `triangle_budget_ratio`는 그 triangles 합계 ÷ spec triangle budget인 조기 경고이며 I02는 engine report로만 판정한다. revision delta의 `changed_bounds`는 나타나거나 사라진 vertex 위치의 box로 검토 camera와 issue region을 정할 때 쓴다.

### 선언 기반 측정 (선택)

spec에 아래 필드를 넣으면 `measurements`가 마지막 after snapshot에서 결과를 계산한다. spec의 일부이므로 승인 bundle에 포함된다. spec 단위는 `m`, `cm`, `mm`만 지원한다. 측정에는 snapshot의 `scene_units.system`이 `METRIC` 또는 `IMPERIAL`이고 `scale_length`가 유한한 양수여야 한다. raw world 좌표에 `scale_length`를 곱해 meter로 환산한 뒤 치수·대칭·anchor는 spec 단위로 비교한다. silhouette의 `meters_per_pixel`은 항상 meter 기준이다. 측정 요청이 없는 기존 snapshot은 단위 metadata 없이도 사용할 수 있지만, 측정을 요청하면 metadata 누락·물리 단위 미지정은 차단한다. snapshot 원본과 geometry delta는 변환하지 않는다.

```json
"dimensions": {"body": {"size": [0.5, 0.3, 0.25], "tolerance": 0.005}},
"symmetry": {"arm_l": {"of": "arm_r", "mirror": "x", "plane": 0, "tolerance": 0.0001},
             "bolt_2": {"of": "bolt_1", "offset": [0.1, 0, 0], "tolerance": 0.0001}},
"anchors": [{"part": "handle", "to": "lid", "relation": "contact", "distance": 0.001}]
```

| 결과 kind | QA | 의미 |
|---|---|---|
| `dimensions` | F02 | world 축 AABB 크기와 선언 크기의 최대 오차 ≤ tolerance |
| `symmetry` | R02 | 선언한 mirror/offset 복사본의 vertex가 양방향 모두 tolerance 안에서 대응. `features.repeated=true`와 mirror/offset 중 정확히 하나가 필요하다. remesh한 쌍에는 선언하지 않는다 |
| `anchor-contact` / `anchor-clearance` | F04 | box 간격은 실제 표면 거리의 하한이다. contact는 위반만, clearance는 충족만 증명하고 나머지는 `unknown` |
| `silhouette-front/side/top` | F01 | run `outlines`의 `reference-outline` JSON `{part, view, meters_per_pixel, origin_px, points}`를 기록된 origin/scale로만 배치한 128칸 raster IoU. 기준값이 없어 `reported` |

결과는 `within/outside/unknown/reported`다. **같은 QA의 PASS와 `outside`가 함께 있으면 finding**이 되어 전환을 막는다. 그 밖의 결과는 판정이 아니며 측정이 PASS를 만들지 않는다. 선언하지 않은 run은 이전과 같다.

## QA와 프로필 정책

| ID | 검사 | 필요한 근거의 예 |
|---|---|---|
| F01 | Silhouette | 고정 camera 외곽 비교, gameplay 거리 |
| F02 | Proportion | 승인 치수·부위별 비율 측정 |
| F03 | Primary form/depth | 면 방향·곡률·두께·깊이, proxy 재평가 |
| F04 | Functional assembly | 접합·접지·관절/손잡이 clearance |
| V01 | Multi-view correspondence | 같은 mesh의 정면/측면/사선/필요한 바닥면 |
| V02 | Surface/shading | normal·곡률·경계·하이라이트 |
| V03 | Visual hierarchy | 주형/보조형/디테일의 시선 우선순위 |
| V04 | Material readability | 승인된 재질 구분·값·광택·게임 조명 |
| S01 | Topology/normals | 퇴화면·non-manifold·winding, 의도한 open shell 예외 명시. run 결과 `mesh_topology` 수치 참고 |
| S02 | Scale/pivot/transforms | 단위·축·pivot·transform·socket |
| S03 | UV/texture | UV 의도·texel density·해상도·texture budget |
| R01 | Rig/deformation | 관절 pose·변형·wind, 강체 관절은 F04로 검토 |
| R02 | Repetition/symmetry | 대표 mesh와 모든 반복 멤버의 위치·방향·예외 |
| R03 | Collision/LOD | 활성화된 collision과 lod를 **모두** coverage에 기록 |
| I01 | Engine import | 실제 엔진/버전/scene·candidate hash·import 결과 |
| I02 | Runtime budget | 실제 엔진의 triangles/materials/texture MiB/frame ms |

모든 QA ID를 항상 열거한다. `PASS`: 지정 방법으로 확인된 일치, `SUSPECT`: 의심되는 차이, `FAIL`: 확인한 차이, `UNKNOWN`: 관측/실행 근거 없음, `N/A`: 승인된 profile/feature 계약에서 비적용. PASS/SUSPECT/FAIL에는 `observation`, `method`, `candidate_sha256`, `evidence`가 필요하다. evidence role은 render/geometry/measurement/engine-report이며 I 항목은 engine-report만 허용한다. PASS는 프로그램이 사진을 보고 부여한 값이 아니다.

프로필 공통 필수는 F01–F04/V01–V04/S01–S02/I01–I02다. S03는 textured, R01은 deforming, R02는 repeated, R03는 collision **또는** lod가 켜지면 필수다. 꺼진 조건만 `profiles/assets.json`의 정확한 exception reason으로 N/A를 허용한다. feature·예산·설계·프로필 변경은 승인을 무효화하므로 AI가 검사 회피 목적으로 바꿀 수 없다. 의도된 open cards나 비대칭은 자동 봉합/대칭화하지 않고 설계 제약과 S01/R02 근거로 설명한다.

| Asset Profile | 추가 검토의 초점 | 비적용 예시 |
|---|---|---|
| `character-monster` | 해부·포즈·표정·관절 변형 | 승인된 static pose는 rig N/A |
| `weapon-tool` | grip·socket·날 방향·간섭 | 강체 도구는 deformation N/A, F04 유지 |
| `machine-robot` | 패널·접합 앵커·관절 가동·반복 부품 | 변형 없는 기계는 rig N/A, F04 유지 |
| `prop` | 게임 거리 가독성·접지·실측 scale | 고유 prop의 repetition N/A |
| `architecture` | grid·module seam·벽 두께·통행 | 비모듈 건물의 repetition N/A |
| `nature` | 유기적 변이·root 접지·wind·overdraw | 정지 식물 rig N/A, 의도한 open leaf card 허용 |
| `background-set` | camera 구도·focal hierarchy·streaming·instancing | 비상호작용 원경 collision N/A, 활성 LOD는 필수 |

## Issue Report와 수정 이력

Detect → Diagnose → Repair → Verify를 `open → diagnosed → repaired → verified`로 기록한다. 최종 상태만 적더라도 이전 단계의 필드가 모두 있어야 한다. `id`, QA `check`, `part`, `region`, `severity`, `observation`, `expected`, 등록 `evidence`, 원래 `candidate`/hash가 필수다. 진단부터 `diagnosis`, 수정부터 `repair`와 실제 geometry `repair_revision`, 검증부터 `verification`, 현재 `verified_candidate`, `verification_evidence`가 필요하다. **수정했다고 검증된 것으로 간주하지 않는다.** 미검증 issue는 단계 전환을 막는다. FAIL/SUSPECT는 반드시 열려 있는 Issue Report가 있어야 한다.

```json
{
  "id": "ISSUE-001", "check": "F03", "part": "body", "region": "primary panel",
  "severity": "medium", "status": "verified",
  "observation": "측면에서 패널 깊이가 승인 도면보다 얕음", "expected": "승인 도면의 깊이",
  "candidate": "assets/revision-01.blend", "candidate_sha256": "REPLACE",
  "evidence": ["assets/before-side.png"], "diagnosis": "주면 vertex 깊이 불일치",
  "repair": "주면을 새 후보에서 수정", "repair_revision": "rev-02",
  "verification": "고정 camera 전후와 사선 재검토", "verified_candidate": "assets/revision-02.blend",
  "verification_evidence": ["assets/after-side.png", "assets/after-oblique.png"]
}
```

`revisions`의 각 event는 `id`, `before_snapshot`, `after_snapshot`, 실제 변경 `parts`, `reason`, 전체 16개 `regression` 판정을 담는다. snapshot 형식은 기존 exporter의 source_asset/source_sha256/coordinate_space=world/parts 계약을 재사용한다. 이력은 frozen baseline에서 시작하여 마지막 candidate로 끝나야 하며 event 간 snapshot 체인이 이어져야 한다. 실제 geometry delta와 parts 불일치, 승인 specification scope 밖 변경, 해시가 다른 source, 누락된 회귀는 차단한다. 각 regression은 status/candidate_sha256/evidence가 필요하다. 마지막 회귀 판정은 현재 QA와 같아야 한다. 이전 revision의 실패는 이력으로 보존하며 마지막 미해결 회귀는 단계 전환을 막는다. 단계 5에서는 실패/불확실 회귀를 숨기지 않고 repair를 실행할 수 있다. I 항목의 UNKNOWN은 단계 8 전에는 전환을 막지 않는다. 나머지는 전환 시 PASS 또는 profile과 일치하는 N/A여야 한다. reindexing을 형상 수정으로 세지 않고 winding 변경은 감지한다. delta는 원본 적합성을 증명하지 않는다.

## 승인·설계 고정·실행 경계

모든 실행에 `design-lock`이 필요하다. low는 승인된 설계·scope 안의 수정, medium은 재구성(rebuild), high는 파괴적 변경(destructive)이다. 명시 risk보다 rebuild/destructive와 대상 파츠의 미해결 issue severity가 정한 최소 위험도가 우선한다. medium/high에는 각각 `operation-medium`/`operation-high`가 추가로 필요하다. `changes_design=true`는 승인 record를 추가해도 실행을 차단한다. 디자인 변경은 별도 specification/design_revision과 새로운 design-lock으로 시작한다. 단계 6부터 `core-shape`, 단계 8은 `final` 승인도 요구한다.

approval record는 `kind`, `status=approved`, `reviewer`, `reviewed_at`, `statement`, human-review role의 `evidence`, `bundle_sha256`을 담는다. `asset_pipeline.evidence.run_digest(run)`은 approvals를 제외한 전체 run과 **profile 정책 파일 hash**에 연결된다. spec·candidate·원본·plan·예외·판정·metrics·이력·단계가 바뀌면 이 구현에서는 새 bundle 승인이 필요하다. 보수적으로 전체 bundle을 고정했으며 부분 승인 재사용은 구현하지 않았다. hash 계산은 승인 행위가 아니며 실제 사용자가 승인한 자료만 기록한다. 현 구현은 승인자의 계정/서명을 인증하지 않는다. 불변 원격 approval ledger가 필요하면 후속 adapter에서 구현해야 한다.

`execute(run, root, output, adapter)`는 신뢰하는 로컬 adapter용 API다. `.receipt.json`에 전후 hash와 scope/stage, 실패, QA/geometry/regression 필요 상태를 남긴다. 기존 파일을 덮어쓰지 않고 실패 후보도 보존한다. 성공해도 `candidate-pending-qa`, `adopted=false`다. 모든 등록 입력 파일을 전후 검사하지만 arbitrary in-process adapter에 대한 OS sandbox나 rollback은 제공하지 않는다. 보호 위반을 감지하면 오류를 반환한다.

Blender adapter는 operation.plan이 가리키는 executor-plan role의 등록 파일만 사용한다. 승인 bundle에 계획이 포함되어야 한다. `kind=vertex-edits-v1`, operation parts와 같은 `parts` object map, `edits` 목록을 사용한다. object/vertex 중복·범위 초과·NaN/Inf·공유 mesh·linked mesh·shape key를 차단한다. 모든 edit를 먼저 검사한 뒤 새 후보에서 **local-space 좌표**를 적용하고 저장한다. 실행 후 새 Blender process에서 snapshot을 추출해 QA/회귀와 새 승인을 진행한다. 임의 Python 생성, topology rebuild, modifier/rig/UV 자동 제작은 구현하지 않았으며 trusted external adapter/사람 작업으로 수행하고 같은 증거 계약을 따른다.

```json
{
  "kind": "vertex-edits-v1",
  "parts": {"body": ["Body"]},
  "edits": [{"object": "Body", "vertex": 0, "position": [-1, -1, -0.75]}]
}
```

## 엔진 보고서와 KPI

engine_report는 등록된 JSON 파일이다. `engine`(spec target_engine과 일치), `version`, `test_scene`, `candidate_sha256`, `import_ok=true`, `runtime_ok=true`, `measurements={triangles, materials, texture_mib, frame_ms}`가 필요하다. budget은 spec에서 승인된 유한한 비음수 값이며 초과하면 차단한다. I01/I02와 회귀는 이 engine-report를 근거로 사용한다. [Unity 정적 handoff runner](../workflows/unity.md)는 새 프로젝트의 실제 import/Play Mode smoke 보고서를 생성한다. 그 보고서는 `runtime_budget_verified=false`, frame_ms=null이므로 target-runtime budget 검증을 통과할 수 없다. Unreal runner와 실기기 성능 benchmark는 별도다.

KPI는 analysis/modeling/render/human_review/waiting/revision seconds, total seconds, 측정된 tokens와 token_source, human_revision_requests, geometry_revisions, qa_pass_rate, qa_coverage, unresolved_issues를 출력한다. 모르는 값은 null이다. 하나라도 시간이 unknown이면 총시간도 null이다. PASS rate 분모는 PASS+FAIL이며 coverage는 전체 적용 항목 중 PASS+FAIL 비율이다. SUSPECT/UNKNOWN을 성공률에 섞지 않는다. 인간 수정 요청 수와 자동 issue 수는 별도다. 시간/토큰 절감 효과의 인과관계나 실제 프로젝트 성능 향상은 측정하지 않았다.

## Variant C와 후속 구현

`examples/minor-on-air/variant-c.run.example.json`은 machine-robot profile 위의 **미승인 migration 템플릿**이다. 실제 Variant C 설계 파일·규격·승인은 레포에 없어 값을 만들어 넣지 않았다. 현재 지원하지 않는 과거 variant-only 설정은 Git 이력에 보존하고 현재 트리에서는 제거했다. Variant C fixture는 미승인 설계 변경과 baseline 변조를 거부하는 사례로 검증한다. 과거 replay는 `experiments/minor-on-air/`에 격리한다.

후속 구현 순서와 연구 근거는 [research](../research.md) 3절 한 곳에서 관리한다. 현재 코어는 spec·evidence 계약, 제한된 Blender 실행, snapshot 연결과 mesh hygiene 수치, QA/approval workflow, 조언용 단계 체크리스트를 구현했다. 범용 image-to-3D 모델 생성·자동 visual judge·production 자산의 엔진 통과는 미완료다.
