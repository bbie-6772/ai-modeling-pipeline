# Surface Re-evaluation Gate (SRG)

블록아웃은 **수정/교체 가능한 proxy**다. 배치나 비율 검토를 통과했어도 면 방향·곡률·깊이·모서리·실루엣·접합 앵커가 확정된 것이 아니다. 원본 도면과 맞지 않으면 기존 면을 고친다. 나사·주름·bevel·재질을 더해 오류를 가리지 않는다. Variant C의 확정 설계와 기존 자산은 보존하고, 승인 범위 안의 새 후보에서만 작업한다.

## 실행 순서와 판단

1. `scope`에 이번 승인 대상 파츠를 빠짐없이 등록한다. 반복 파츠도 각 멤버를 기록한다. 원본/설계/baseline/blockout을 hash로 고정한다.
2. 블록아웃의 evaluated world-space mesh snapshot과 렌더를 저장한다. 기존 면 영역을 이름/face/vertex/landmark로 식별한다. snapshot의 `source_asset`과 `source_sha256`은 실제 저장된 자산에 연결한다.
3. 각 파츠를 정합된 **원본**의 주·보조 뷰와 다시 비교한다. 여섯 항목 모두 `source_observation`, `before_observation`, `after_observation`, `surface_region`, 렌더 `evidence`를 기록한다. silhouette만 맞는 것으로 내부 면을 통과시키지 않는다. 관측되지 않는 깊이·접합은 `uncertainties`로 보고한다.
4. 아래 기준으로 `edit`/`rebuild`/`retain`을 정하고 근거를 남긴다. 명백한 불일치는 인간 수정 요청을 기다리지 않고 승인 범위에서 먼저 수정한다. 수정 자체가 설계 변경을 요구하면 보류한다.
5. 수정 후 별도 candidate를 저장·재개방해 snapshot을 추출하고, 동일 camera/renderer/resolution으로 전후 렌더를 만든다. 원본 overlay·조립 사선·확대를 포함하고 부족한 뷰를 추가한다. `change_log`에 이동한 주요 면/vertex와 topology 교체를 적는다.
6. 여섯 항목의 `match`/`corrected`, 미해결 차이, 불확실성, 자동 산출 geometry delta를 함께 검토한다. `pending`/`unknown`/`mismatch` 또는 blocking issue는 디테일 진입을 막는다. 불확실성을 자동으로 해소한 것으로 만들지 않는다.
7. **핵심 형상에 대한 직접 인간 승인**을 해당 bundle에 기록한 다음 `stage=detail-entry`를 검사한다. `status=evidence-consistent`와 `detail_allowed=true`, exit 0을 모두 확인한 실행기만 detail 명령을 호출한다. 비정상 종료·잘못된 JSON·기타 값은 중단한다. `stage=final`은 별도의 최종 `approval`도 요구한다.

| 결정 | 선택 조건 | 필요한 증거 |
|---|---|---|
| `edit` | 국소 vertex/edge/face 이동으로 원본에 맞출 수 있고 주변 접합/topology를 유지할 수 있음 | 고친 기존 면, 전후 관측, 실제 geometry 변화 |
| `rebuild` | proxy topology/단면/깊이 구조가 부적합하거나 누적 보정이 원본과의 관계를 흐림 | 재구성 이유, 유지할 앵커, 교체 범위, 원본과 새 면 대응 및 geometry 변화 |
| `retain` | 여섯 항목이 원본과 맞으며 수정 필요가 없음을 적극적으로 확인 | 모든 항목 `match`, 유지 근거, 동일 geometry, 인간 검토 |

기존 면 변화 없이 독립 detail mesh만 추가한 `edit`/`rebuild`는 차단한다. face winding 변경도 기록하고 단순 vertex 재번호는 표면 수정으로 세지 않는다. 이 수치는 변화를 입증하는 보조 자료다. 잘못된 방향으로 움직였는지, 실제 주 면을 고쳤는지, topology 재구성이 적절한지는 원본/전후 자료와 사람이 판단한다.

## 설정과 증거 계약

설정 파일 위치 기준 상대 경로만 사용한다. `assets`에 기존 필수 role인 `design`, `reference`, `baseline`, `candidate`, `evidence` 외에 `blockout`, `geometry`, `render`, `alignment`, `human-review`를 등록한다. 파일별 `path`, `role`, `sha256`은 실제 파일을 가리켜야 한다. 전후 snapshot·render는 별도 파일이며, snapshot의 part key 집합은 `scope`와 정확히 같아야 한다.

`templates/legacy/surface-gate.example.json`은 필드 구조만 제공한다. `pending`, 빈 assets/관측/승인은 정상적으로 차단된다. `tests/fixtures/surface.py`는 임시 테스트 데이터 생성기이며 실제 승인이나 이미지를 제공하지 않는다.

snapshot은 다음 구조를 쓴다. `vertices`는 evaluated world 좌표, `faces`는 vertex index다. 각 파츠의 여러 mesh object는 offset을 적용해 하나로 합칠 수 있다. exporter는 변환과 modifier 결과를 반영한다. Geometry Nodes instance, 비-mesh, animation 시점 등은 프로젝트 adapter에서 별도로 검증해야 한다.

```json
{
  "source_asset": "assets/blockout.blend",
  "source_sha256": "ACTUAL_SHA256",
  "coordinate_space": "world",
  "parts": {
    "body": {"objects": ["Body"], "vertices": [[0,0,0],[1,0,0],[0,1,0]], "faces": [[0,1,2]]}
  }
}
```

각 `views`는 등록된 원본·전후 렌더·alignment 파일을 연결한다. alignment 예시의 camera는 실제 projection/pose/lens/scale, renderer는 engine/device/samples 등 비교 조건을 모두 기록한다. 원본 crop은 원본 pixel 좌표다. 보정 불가·가림·깊이 모호성은 uncertainty와 파츠 issue에 명시한다. 뷰 하나로 판별할 수 없다면 추가 view를 등록한다. 전후 camera fitting, 비균일 warp로 오차를 숨기지 않는다.

```json
{
  "reference": "assets/original.png",
  "source_view": "front",
  "crop_pixels": [0, 0, 640, 640],
  "projection": "orthographic",
  "registration_method": "Approved camera calibration revision ...",
  "uncertainty": "Describe remaining registration limits, or explicitly none",
  "before": {
    "camera": {"projection": "ORTHO", "matrix_world": "ACTUAL_MATRIX", "ortho_scale": 2},
    "renderer": {"engine": "CYCLES", "device": "CPU", "samples": 12},
    "resolution": [640, 640], "geometry_sha256": "BEFORE_SNAPSHOT_HASH"
  },
  "after": {
    "camera": {"projection": "ORTHO", "matrix_world": "ACTUAL_MATRIX", "ortho_scale": 2},
    "renderer": {"engine": "CYCLES", "device": "CPU", "samples": 12},
    "resolution": [640, 640], "geometry_sha256": "AFTER_SNAPSHOT_HASH"
  }
}
```

`unresolved_differences`와 `uncertainties`는 생략할 수 없는 배열이다. 각 issue는 `description`, `reason`, `disposition`을 갖는다. 차단 문제는 `blocking`으로 기록한다. 형상 오류를 명목상 불확실성으로 바꾸지 않는다. 사람이 명시적으로 수용한 비차단 한계만 `accepted-nonblocking`으로 기록하고 재승인한다. 여섯 check 자체의 오류/미확인은 수용 표시로 우회할 수 없다.

## Blender 추출과 승인 연결

새 run에서 `parts.json`을 `{"body": ["Body"]}`처럼 작성하고 저장된 전후 파일을 각각 새 process에서 연다. 출력은 덮어쓰지 않는다. 다음 명령을 전후 파일에 각각 적용한다.

```console
blender --background --disable-autoexec --python-exit-code 1 assets/blockout.blend --python asset_pipeline/adapters/blender/snapshot.py -- --parts parts.json --output assets/before-geometry.json --asset-path assets/blockout.blend
blender --background --disable-autoexec --python-exit-code 1 assets/core-candidate.blend --python asset_pipeline/adapters/blender/snapshot.py -- --parts parts.json --output assets/after-geometry.json --asset-path assets/core-candidate.blend
python pipeline.py config.local.json
```

승인 hash를 계산하기 전에 모든 파일·관측·정렬·issue와 승인 근거 파일을 확정한다. 실제 사람의 답변은 role `human-review`인 파일에 보존한다. `surface_review.approval`의 `reviewer`, `reviewed_at`, `statement`, `evidence`를 직접 승인에 근거해 채운다. 사람의 검토 전에 approved를 만들지 않는다.

```python
hashes = {a['path']: a['sha256'] for a in config['assets']}
from asset_pipeline.surface import surface_digest
config['surface_review']['approval']['bundle_sha256'] = surface_digest(config, hashes)
# stage=final: 최종 결과에 대한 별도 직접 승인 후에만 계산
from asset_pipeline.legacy import bundle_digest
config['approval']['bundle_sha256'] = bundle_digest(config, hashes)
```

core hash는 project/design/scope/모든 파일 hash/재평가 내용에 연결된다. core 승인 객체의 bundle_sha256만 제외하므로 승인 진술·근거 경로도 결속한다. 최종 hash는 최종 승인 객체만 제외한 전체 설정에 연결된다. source, candidate, render, camera manifest, issue, scope가 바뀌면 재검토하고 hash를 갱신한다. 디테일 후 최종 후보가 바뀌어도 예전 core snapshot으로 대체하지 않는다. 최종 후보에 대해 재평가 자료와 승인을 갱신한다. 이전 파일-only 승인이나 v1.1 설정은 자동 이관하지 않는다.

## 실제 강제 범위와 다음 adapter 구현

이 문서의 기존 Surface Gate는 offline validator다. 범용 코어의 제한된 Blender adapter는 별도 실행 경로이며 같은 Gate를 재사용한다. **이 검사기의 디테일 진입/최종 gate**에서는 SRG를 생략할 수 없지만, 직접 Blender/MCP 명령을 보내는 외부 작업까지 가로막지는 않는다. 실제 adapter는 (1) scope를 작업 object 목록과 대조, (2) 입력 hash 재확인, (3) gate 호출 및 JSON/exit 검사, (4) 승인된 후보 복사본에 detail 작업, (5) 보호 검사·재개방·새 증거·재승인을 연결해야 한다. 다른 실행 경로도 같은 precondition을 사용해야 한다.

hash는 파일 일치와 snapshot 연결을 검사한다. mesh snapshot/렌더/manifest가 진실한지, calibration이 정확한지, 승인자가 누구인지 인증하지 않는다. 이미지에서 여섯 항목을 자동 측정하지 않으며 자동 modeling/승인도 하지 않는다. 실제 exporter의 smoke test는 별도 합성 scene에 한정한다. Variant C 실제 자산의 면을 고쳤거나 인간 승인을 받았다는 뜻이 아니다.
