# 형상 계약과 도면 검증

`templates/shape-contract.example.json`은 미완성 템플릿이다. 근거를 읽고 확인한 값만 채운다.
`observed`는 근거에서 확인한 값, `inferred`는 추정, `unknown`은 미확정이다. inferred/unknown은
수치를 넣어도 자동 PASS로 바꾸지 않는다. 추정·미확정은 사람의 설계 결정과 새 revision이 필요하다.

형식 `shape-contract-v1`은 asset_id/design_revision/units, 모든 파츠의 object 목록과 관측,
참조 파일의 상대 경로·SHA-256·뷰, 선택 치수·대칭·anchor·outline, 불확실성 목록을 담는다.
참조 경로 기준은 standalone에서는 계약 파일의 부모, run에서는 run 파일의 부모다.
각 관측·측정에는 basis/description/reference_ids가 필요하다. 치수·대칭·anchor 값은 기존
선언 기반 측정과 같다. outline은 기존 reference-outline 필드와 `minimum_iou`(0..1)를 사용한다.
치수·외곽 위반은 FAIL, 관측되지 않은 값·한쪽만 증명하는 anchor 결과·blocking uncertainty는
UNKNOWN이다. 제약이 하나도 관측·측정되지 않은 계약도 통과하지 않는다.

```console
python -m asset_pipeline.shape_contract shape.json --candidate assets/candidate.blend --drawing-manifest drawings/manifest.json --output shape-report.json
```

저장 모델 → 도면 출력 → 이 검사를 순서대로 실행한다. report의 성공은 선언된 제약만의 충족이다.
불일치는 exit 2, 일관된 선언 제약은 exit 0이다. 이미지 내용이나 승인자 신원을 인증하지 않는다.
output은 exclusive-create이며 후보·원본·QA 판정·인간 승인을 수정하지 않는다.

기존 코어 run에 `shape_contract`(등록 role `shape-contract`)와 `drawing_manifest`(role
`drawing-manifest`) 경로를 추가하면 단계 5부터 검사한다. 계약 asset_id/design_revision/scope,
현재 candidate hash, 마지막 revision snapshot과 도면 snapshot의 완전 일치, 도면 파일 hash,
camera/scale과 geometry의 일치 및 모든 bundle 파일의 run 등록을 요구한다. 참조 파일은
role `reference`로 등록한다. findings는 기존 단계 전환 판정에 합쳐지며 manual PASS로 덮을 수 없다.
기존 run에 두 필드가 없으면 이전 동작을 유지한다. JSON과 증거 파일 변경은 기존 승인 bundle을 무효화한다.

후보가 `assets/candidate.blend`처럼 하위 경로에 있다면 도면 생성에 `--asset-path assets/candidate.blend`를
전달한다. 동일 snapshot을 revision의 after_snapshot에도 사용한다. 등록 role은 snapshot `geometry`,
PNG/SVG `render`, config/parts `measurement`로 사용할 수 있다. manifest에 기록된 파일은 모두 등록한다.
실제 run의 design-lock/core-shape/final 승인은 이 검사가 생성하지 않는다.
