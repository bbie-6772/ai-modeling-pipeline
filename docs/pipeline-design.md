# 검증 중심 설계

## 고정 경계

Variant C는 변경 대상이 아닙니다. 참조 선택, 검토 방법, 처리 단위만 실험합니다. baseline은 승인된 설계 문서·원본 참조·원본 `.blend`의 해시 목록으로 고정합니다. 새 설계 승인이나 리디자인은 이 저장소의 자동화 범위 밖입니다.

현재 입력 부족은 실패가 아니라 `blocked`입니다. 추정한 버텍스 좌표나 대칭성을 확정 사실로 기록하지 않습니다. 숨은 형상, 원근 왜곡, 서로 모순되는 도면은 `unknown`으로 남겨 사람에게 검토시킵니다.

## 실행 단계와 gate

| 단계 | 작업 | 다음 단계 조건 | 구현 상태 |
|---|---|---|---|
| G0 | 설계·참조·baseline 파일 등록 및 hash 고정 | 자료 존재와 담당자의 baseline 확인 | 파일 hash 검사 구현 |
| G1 | 파츠별 crop, 뷰·좌표계·단위·대응 landmark 정의 | 관측/추론 구분 및 사람의 분석 승인 | 수동, 자동화 미구현 |
| G2 | 위험별 작업 묶음과 변경 범위 제안 | 고유 실루엣/접합은 개별, 반복 부품은 대표 표본 승인 | 계획만 |
| G3 | baseline 복사본을 새 run의 candidate로 편집 | 원본 불변, 후보 파일 분리, 오류 시 후보 폐기 | 실행기 미구현 |
| G4 | 동일 camera에서 overlay·사선 접합·확대 + 필요한 추가 뷰 | 가려짐/고위험 파츠는 8방향으로 확대 | 렌더/영상 검사 미구현 |
| G5 | 증거 bundle과 사람의 검토 기록 연결 | 현재 bundle과 승인 hash 일치 | offline gate 구현 |
| G6 | 승인 후보를 별도 산출물로 인도 | 사용자가 최종 판단 | 자동 승격 없음 |

G1/G2 승인까지 현재 코드는 강제하지 않습니다. G5의 기록 일치가 전체 공정 gate 완료를 뜻하지 않습니다. 실제 작업 실행기를 만들 때 각 단계별 승인과 의존성 무효화를 연결해야 합니다.

## 비파괴 Blender/MCP 연결 계획

1. API 이름만 보고 연결 성공을 가정하지 않습니다. 현재 Blender MCP 도구는 발견되었으나 live scene은 조회/변경하지 않았습니다. 작업 대상이 지정되지 않은 세션에는 명령을 보내지 않습니다.
2. 인터페이스 문서, Blender/add-on 버전, 대상 `.blend` 경로를 확인한 후 read-only summary부터 smoke test합니다.
3. baseline hash를 기록하고 새 run 디렉터리에 배타적으로 복사합니다. 기존 run/출력은 덮어쓰지 않습니다. baseline을 연 채로 원격 편집하지 않습니다.
4. 별도 Blender process에서 candidate를 열고, 외부 스크립트 자동 실행을 비활성화합니다. 허용된 object/collection 변경 목록을 먼저 승인받습니다.
5. 작업 전후 baseline hash, 변경 object, mesh 통계, material/transform, camera manifest를 비교합니다. 범위 외 변경이면 후보를 격리하고 승인하지 않습니다.
6. 보고서에는 run ID, 부모 baseline hash, 설정 hash, 코드 commit, 도구 버전, 원본 및 crop 좌표, camera projection/pose/lens/resolution, 시간, token 사용량을 남깁니다.

MCP 재시도는 임의 code execution을 재전송하지 않습니다. 타임아웃 시 실제 반영 여부를 조회하고, candidate checkpoint에서 다시 시작합니다. 실행기 도입 시에만 구현합니다.

## 검증 항목

실루엣 IoU는 camera와 마스크가 정합된 경우에만 사용합니다. landmark 오차는 이미지 대각선으로 정규화하고, 실측 치수는 승인된 단위를 씁니다. 기준 threshold는 아직 정하지 않았으며 사람이 승인해야 합니다. 낮은 신뢰도의 마스크/landmark로 모델을 자동 수정하지 않습니다.

게임용 검증은 scale/origin, transform, normals, UV, material 슬롯, triangle budget, 비정상 topology를 별도로 다룹니다. 열린 표면을 의도한 mesh에 무조건 manifold를 요구하지 않습니다. 예산은 실제 target engine과 asset spec 확보 후 정합니다.
