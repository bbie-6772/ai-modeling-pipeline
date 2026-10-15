# 첫 비교 실험: 발 외피 4개 처리와 검토 뷰 구성

실행일: 2026-10-15. Blender 5.2.2 LTS CLI, Cycles CPU, 640×640, 12 samples, 최대 8 threads, autoexec 비활성화.

## 무엇을 비교했는가

이번은 **기존 형상을 재생한 제한된 pilot**이다. 원본을 보고 새로 추출·모델링하는 전체 workflow 비교는 아직 아니다. 채택 ear v02를 두 실행의 동일 baseline으로 열고, 미채택 legs v11에서 읽은 발 외피만 적용했다. A는 각 발의 저장된 vertex/face를 개별 적용하고, B는 FL 외피의 world 좌표를 X=0과 다리 pivot 앞뒤 중앙 Y에 대해 미러했다. 다른 파츠는 수정하지 않았다.

기존 2D A01 추출점을 새로 승인하거나 새 3D 복원에 사용했다고 주장하지 않는다. 두 방식 모두 같은 v11 형상 정보를 사용한다. 이 방식은 처리 단위와 검토 자료 생성의 차이를 먼저 확인하기 위한 것이다. 현재 사용자의 비교 실험 진행 지시는 별도 후보 제작에만 적용했고, 기존 프로젝트 contract/승인 기록과 채택 모델은 변경하지 않았다.

## 측정 결과

| 항목 | A: 개별 처리 | B: 대표 1개 + 미러 |
|---|---:|---:|
| 형상 적용 | 0.005293초 | 0.005353초 |
| 검토 렌더 수 | 발 4개 × 8방향 = 32장 | 그룹 정면·사선·아래 = 3장 |
| 렌더 시간 합계 | 8.103936초 | 0.567763초 |
| 재개방/보호 검사 | 통과 | 통과 |

두 후보의 world vertex 최대 차이는 모든 발에서 **0m**였다. face 순서, material 배정, smooth flag도 같았다. 각 후보를 새 Blender process에서 다시 열어 보호 object fingerprint와 material fingerprint, object 목록, evaluated mesh의 boundary/zero-area/winding 충돌 검사도 통과했다. 입력 채택 모델과 v11 파일 hash는 종료 후에도 같았다.

렌더 시간은 이 실행에서 약 93% 줄었다. **1회, A 다음 B 순서**이므로 cache와 순서 효과를 분리하지 않았다. 형상 적용 시간의 0.00006초 차이는 의미 있는 우열로 해석하지 않는다. process 시작/파일 로드·저장, 분석·코드 작성 시간은 표의 형상 적용 및 렌더 시간에 포함되지 않는다. 시간 측정 범위가 전체 작업 시간이 아님을 유지한다.

## 관찰과 판단

그룹 정면에서는 뒷발이 앞발에 가려지고, 640px 한 장에 4개를 넣으면 개별 발의 픽셀 수가 줄어든다. 따라서 이번처럼 **형상이 같아도 검토 정보는 같지 않다.** 단순히 32장을 3장으로 줄인 것을 전체 품질 유지의 증거로 삼을 수 없다.

다음 실험 가설은 "반복 형상 생성은 대표 규칙을 공유하되, 검토는 대표 근접 뷰와 반복 배치 문맥을 함께 유지하면 재수정을 줄일 수 있다"이다. 이 pilot만으로 채택하지 않는다.

원본 적합성 점수, 사람 검토 시간, 최초 승인율, 재수정 횟수, 방식별 모델 token/비용은 **미측정**이다. calibrated camera나 승인된 치수도 새로 확보하지 않았다. 후보는 미채택이며 기존 Variant C 설계 승인과 별개다. MCP 호출은 사용하지 않았고 CLI로만 실행했다.

## 재현

`experiment.py`는 Blender 내부용이다. `extract`는 기존 v11을 읽어 `recipe.json`을 새로 쓰고, `A`/`B`는 각각 채택 baseline을 읽어 존재하지 않는 출력 폴더에 후보와 렌더를 쓴다. `check`는 각 후보를 다시 열어 검사한다. 모든 실행에 `--background --disable-autoexec`, 실패를 전파하는 `--python-exit-code 1`을 사용했다.

Blender 옵션 뒤 `--python experiment.py -- STAGE --project PROJECT --out OUTPUT --recipe RECIPE`를 전달한다. STAGE별 입력 blend는 extract=v11, A/B=ear v02, check=각 candidate다. extract 이전에 공통 run 디렉터리만 만들고 A/B 하위 폴더는 만들지 않는다. check 출력이 이미 있으면 기존 증거를 덮어쓰지 않고 실패한다.

일반 Python에서 `python analyze_experiment.py RUN_DIRECTORY`로 두 geometry 및 input hash를 비교하고 결과 JSON/보드를 생성한다. 보드에는 기존 환경의 Pillow를 사용했다. 이 스크립트의 assert가 일치/원본 보존 검사이며 실패하면 결과를 생성하지 않는다. 분석 출력도 기존 파일을 덮어쓰지 않는다.

원본 blend와 생성 후보·이미지는 로컬 산출물에 유지하고 이 저장소에는 실행 코드, 측정 JSON, 실험 설명만 반영한다.
