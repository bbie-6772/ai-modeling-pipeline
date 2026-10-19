# AI 시안 후보 생성과 형상 계약 초안

brief JSON에 `asset_id`, 새 제안 `design_revision`, `description`, 고유한 제안 파츠 ID 목록 `parts`,
제약 문자열 목록 `constraints`를 기록한다. 기존 승인 설계를 바꿀 때는 기존 revision을 재사용하지 않는다.

```console
python -m asset_pipeline.concept prepare brief.json --output runs/concept-01
```

생성된 prompt.txt를 수정 없이 imagegen built-in tool에 전달한다. 실제 참조 이미지가 있다면
tool의 reference로 함께 전달하고 출처를 작업 기록에 보존한다. 이 CLI는 imagegen SDK·API를
직접 호출하지 않는다. 에이전트의 built-in tool 단계와 생성된 파일 등록을 연결한다.
API key를 가정하거나 다른 image model로 자동 대체하지 않는다. 생성 후 실제 PNG를 등록한다.

```console
python -m asset_pipeline.concept register runs/concept-01 --image generated.png --provider image_gen.imagegen
```

brief/prompt 변조와 후보 덮어쓰기를 거부하고 candidate 이미지·hash·provider·prompt hash를 기록한다.
model_id는 tool이 제공하지 않으면 null이다. candidate는 항상 pending-human-review, selected=false,
approved=false다. 형상 계약 초안의 치수·깊이·mesh mapping은 unknown으로 남긴다. 생성 이미지에
그려진 여러 뷰가 서로 일치한다고 간주하지 않는다. 도면은 실제 모델에서 별도로 생성한다.

실제 사용자의 선택·분석·설계 결정 후에만 새 계약 revision과 기존 인간 승인 계약을 적용한다.
이 도구가 선택·승인·자동 모델링·QA 통과 기록을 만들어내지는 않는다.
