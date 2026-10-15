# 모델링 작업 기록 — 복사해서 사용

이 파일은 사람이 채우는 작업 기록이다. `pipeline.py`의 JSON 입력이 아니다. 빈 값이나 예시는 승인·실행 사실을 뜻하지 않는다.

## 시작 정보

- Run ID / 날짜 / 담당자: `pending`
- 프로젝트명 / 승인된 design revision: `pending`
- 실제 프로젝트 경로 / 작업 scene: `unknown`
- 요청 범위 / 변경할 object의 정확한 목록: `pending`
- 현재 채택 baseline 경로 / SHA-256: `unknown`
- 미채택 후보 경로 / 상태: `none 또는 unknown`
- 새 출력 경로 / candidate revision: `pending`
- 설계 고정 사항 / 기존 알려진 문제: `pending`
- DCC·MCP/CLI·helper 버전 / 코드 commit: `unknown`
- 대상 DCC / AI 모델 / target engine·export 형식: `unknown`
- 비교 renderer / CPU·GPU / 해상도·samples / resource 한도: `pending`

## 원본·분석

| 파츠 | 원본 경로/해시 | 주·보조 뷰 / crop pixel 좌표 | 외곽·내부점 JSON / revision | 관측·추정·가림 |
|---|---|---|---|---|
| 작성 | 작성 | 작성 | 작성 | 작성 |

- 단위·scale 근거 / camera·calibration 상태: `unknown`
- 대표 파츠 / 그룹 멤버 / 대칭 plane·배치 규칙: `pending`
- 모든 멤버의 동일성 근거 / 제외할 예외: `pending`
- 원본·점·그룹 범위 승인: `pending`
- 직접 사용자 답변 / 승인된 revision·object subset: `pending`

## 구현·보호

- [ ] baseline/원본 해시 기록, 기존 출력 덮어쓰기 없는 경로 확인
- [ ] 실제 scene audit 및 그룹 밖 fingerprint 저장
- [ ] 승인된 object만 변경, 공유 mesh 영향·미러 winding·방향 확인
- [ ] 멤버별 배치·scale·접합 검사
- [ ] 보호 검사 및 baseline 해시 재확인
- [ ] 새 파일 저장 및 새 process에서 재개방 검사

각 항목의 실제 보고서 경로·결과·미실행 사유: `pending`

## Surface Re-evaluation Gate — 디테일 진입 전 필수

블록아웃은 교체 가능한 proxy이며 형상 확정이 아니다. [SRG 계약](../docs/contracts/surface-gate.md)을 따른다.

- 승인된 scope / blockout 파일·SHA-256 / 전후 geometry snapshot: `pending`
- 원본 정합 근거·crop·camera·renderer·해상도 / 전후 렌더: `pending`

| 파츠·주요 면 영역 | 방향 | 곡률 | 깊이 | 모서리 | 실루엣 | 접합 앵커 |
|---|---|---|---|---|---|---|
| 각 scope 파츠별 작성 | 원본/전/후·증거 | 원본/전/후·증거 | 원본/전/후·증거 | 원본/전/후·증거 | 원본/전/후·증거 | 원본/전/후·증거 |

- `edit / rebuild / retain` 결정 및 topology·앵커·비용 근거: `pending`
- 실제 기존 면/vertex/face 변경 log / 자동 geometry delta: `pending`
- 미해결 차이 / 불확실성 / blocking 여부와 수용 근거: `pending`
- 핵심 형상 직접 인간 승인 답변·검토자·시각·증거 파일·bundle hash: `pending`
- `stage=detail-entry` 검사 결과·exit code / `detail_allowed`: `pending / false`
- [ ] core 승인과 현재 자료가 일치하고 gate 통과를 확인한 뒤에만 detail 실행
- [ ] 후보/원본/정렬/issue 변경 후 stale 승인을 폐기하고 재평가

## 결과 검토

- 원본·변경 전·변경 후 40% overlay: `pending`
- 조립 문맥 사선: `pending`
- 대표 확대: `pending`
- camera/정렬 방법 / 비교 해상도: `pending`
- 추가로 필요한 뷰 / 이유 / 결과: `pending`
- 남은 불확실성·접합·개폐·UV/엔진 검증 문제: `pending`
- 결과 검토 대상 candidate SHA-256 / 증거 bundle revision: `pending`

## 시간·수정 기록

| 항목 | 실제 측정값 |
|---|---|
| 분석 / 구현 / 렌더 | `unknown` |
| 사람 검토 / 대기 / 재수정 | `unknown` |
| 사용자 수정 요청 횟수 | `unknown` |
| 자동 검사 실패 횟수 | `unknown` |
| 실제 모델 token / 비용 / 계측 근거 | `unknown` |

## 최종 상태

- 상태: `pending / blocked / review / approved / adopted / rejected 중 실제 상태`
- 사용자 최종 승인 답변 / 승인한 정확한 candidate·증거 revision: `pending`
- 채택 모델 포인터 / 이전 baseline 보존 경로: `pending`
- 채택 처리 여부: `아니오`
- 다음 작업 허용 범위 / 남은 문제: `pending`

원본/점/범위가 바뀌면 영향받는 분석 승인을, 후보/증거가 바뀌면 결과 승인을 갱신한다. 승인 기록을 복사해 새 후보에 붙이지 않는다.
