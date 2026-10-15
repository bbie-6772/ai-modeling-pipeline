# 실험 및 테스트 계획

## 비교 설계

기존 느린 정밀 프로세스를 control로 두고 동일 baseline·참조·파츠·camera·검토자·모델 버전을 사용합니다. 고유 실루엣, 접합부, 반복 부품을 포함하는 작은 대표 세트를 실제 설계에서 선택합니다. 지금은 실제 부품 이름을 만들지 않습니다.

| 실험 | 바꾸는 변수 | 고정 조건 | 판단 |
|---|---|---|---|
| E0 | 기존 파츠별 분석/승인 + 8방향 | 기준 workflow | 정확도·소요량 baseline 측정 |
| E1 | 반복 부품만 대표 1개 승인 후 동일 규칙 적용 | 고유 파츠 개별 검토 유지 | 반복 전체의 배치 오차도 검사 |
| E2 | 3보드 + 불확실성/가려짐 시 8방향 | E1과 동일 처리 단위 | 절감 시간보다 재수정 증가가 크면 기각 |
| E3 | 저비용 모델이 crop 설명/landmark 제안만 작성 | main reviewer와 모델러 동일 | 추출 정확도·재검토 비용 포함 비교 |

E1→E2→E3 순으로 한 변수씩 도입합니다. E3는 자동 적용이나 자동 승인을 하지 않습니다. 각 조건은 파츠별 최소 3회 탐색하고 순서를 교차합니다. 작은 표본은 일반화 근거로 주장하지 않습니다.

기록: 최초 승인까지 총 시간(대기/작업 구분), human review 분, 재수정 횟수, 최초 승인율, 오류 심각도, silhouette/landmark 측정값, 입력/출력 token 및 당시 가격으로 계산한 비용. 비용 절감만으로 성공 판정하지 않습니다. 품질 threshold와 허용 비열등 margin을 먼저 사람이 정하고, 이를 충족한 조건만 시간·비용의 median과 범위로 비교합니다. 측정 전 우승 workflow를 정하지 않습니다.

## 실행 가능한 offline 검사

`python -m unittest -v`: synthetic bundle 정상 경로, 원본 불변, Variant 변경 거부, apply mode 거부, 누락 자료, pending 승인, stale bundle, 경로 탈출/절대 경로/누락 파일, 변조 hash, 중복 파일, 잘못된 JSON의 CLI exit code를 확인합니다. fixture 통과는 실제 설계 승인과 무관합니다.

## 실제 자료가 있어야 실행할 검사

- baseline 변조/기존 run 충돌/편집 중단/연결 timeout 시 원본 보존과 복구.
- G1 승인 없이 G3 실행 차단, candidate 또는 camera 변경 후 승인 무효화.
- 동일 camera overlay 정합, 원근/정사영 구분, 가려진 접합부 8방향 검토.
- MCP read-only smoke test → 복사본 변경 → checkpoint/reopen → mesh/transform 비교.
- 실제 asset spec 기반 topology/UV/normals/scale/engine import 검사.

위 항목은 현재 실행되지 않았습니다. GitHub Actions workflow도 배치 파일일 뿐 원격 성공 여부를 별도로 확인해야 합니다.
