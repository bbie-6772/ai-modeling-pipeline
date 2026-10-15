# 일반화 변경 검증 — 2026-10-15

- 저장소: `ai-modeling-pipeline`, 기존 저장소를 rename. 사용자 bbie-6772와 private visibility 유지.
- README·PIPELINE·작업 템플릿·설계 문서를 프로젝트 중립적으로 정리. 프로젝트별 replay 3개는 `examples/minor-on-air/`로 이동하고 개인 기본 경로를 제거.
- 설정은 임의의 비어 있지 않은 `project`/`design_revision`을 지원. 승인 hash는 두 식별자와 asset hash를 함께 포함. 이전 설정의 자동 승인 이관 없음.
- `python -m unittest -v`: 6개 테스트 메서드 및 내부 subtest 통과, 0.130초. 다른 프로젝트/설계에 과거 승인 재사용 거부와 새 프로젝트의 유효 bundle 통과를 포함.
- `python pipeline.py config.example.json`: 자료 없는 sample은 `blocked`, exit code 2 확인. 출력 key는 `model_validation=not_run`.
- 변경은 운영 문서·검증 코드·예제 정리에 한정. 실제 모델/DCC 통합이나 다른 engine 연동을 새로 실행했다고 주장하지 않음. 과거 실험의 원본 수치는 수정하지 않음.
