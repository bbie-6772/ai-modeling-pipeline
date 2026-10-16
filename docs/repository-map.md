# 파일 배치와 유지 기준

| 위치 | 책임 | 사용할 때 |
|---|---|---|
| asset_pipeline/ | 런타임·공통 파일 경계·Surface Gate·legacy 검사기 | 구현/검증 변경 |
| asset_pipeline/adapters/blender/ | 승인 plan 실행·Blender worker·snapshot exporter | Blender 연결 |
| profiles/ | 7개 종류의 필수/예외 QA 정책 | profile 선택/수정 |
| templates/ | 재사용 run JSON과 사람이 작성할 RUN 기록 | 새 작업 시작 |
| templates/legacy/ | 지금도 지원하는 detail-entry/final 설정 | 기존 설정 유지 |
| examples/minor-on-air/ | Variant C의 미승인 적용 예시 | 해당 사례 적용 |
| tests/unit/ | offline 계약·회귀·호환·링크 검사 | 일반 코드 수정 |
| tests/integration/ | 실제 Blender의 새 임시 scene 검사 | Blender 코드 수정 |
| tests/fixtures/ | synthetic 증거 생성기·공통 fixture | 테스트에서만 사용 |
| experiments/ | 합성 복원·특정 모델 replay | 실험 재현 요청 |
| docs/workflows/ | 작업자가 따를 운영 순서 | 모델링 실행 |
| docs/contracts/ | 필드·판정·승인·실행 경계의 정식 계약 | 설정 작성·진단 |
| docs/testing.md | 개발 검증 명령과 한계 | 변경 검증 |
| docs/research.md | 외부 연구 근거와 유일한 후속 구현 순서 | 로드맵·설계 판단 |
| runs/, assets/ | Git에서 제외되는 실제 자산·후보·증거 | 승인된 실제 작업 |

루트의 세 Python 파일은 기존 CLI/import 호환용 진입점이다. 패키지의
blender_adapter.py도 기존 import를 유지하는 facade다. 실제 구현은 한 곳에만
있으며 production 코드가 루트 facade나 테스트 모듈을 import하지 않는다.

삭제한 파일과 이유:

- docs/pipeline-design.md: 과거 G0–G6 계획으로 현재 8단계와 충돌하고 승인 identity 구현을 잘못 암시했다. 현재 계약으로 대체했다.
- docs/adapting-a-project.md: 기존 설정을 기본으로 안내하던 중복 가이드였다. 시작 절차는 README, legacy 계약은 Surface Gate 문서로 통합했다.
- examples/minor-on-air/legacy-variant-c.config.json: 현재 두 validator 모두 직접 사용할 수 없는 variant-only 형식이었다. migration 템플릿과 Variant C 회귀 검사는 유지한다.
- 테스트 클래스 사이의 fixture 차용과 중복 discovery를 막던 load_tests 우회: 공통 fixture 모듈 분리로 불필요해졌다.

과거 자료는 변경 전 commit ac00044의 Git 이력에서 조회할 수 있다. 실험 코드는
재현 목적이 있어 삭제하지 않고 기본 운영 경로에서 분리했다. README/AGENTS에서
시작해 현재 작업 문서만 읽는다. 실험 수치·synthetic 승인을 실제 자산의
품질·성능·승인으로 전용하지 않는다.
