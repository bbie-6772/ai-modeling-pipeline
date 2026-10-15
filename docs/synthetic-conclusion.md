# 새 원본에서 실제 복원한 최종 결과

2026-10-15. 기존 mesh를 재생하는 비교의 한계를 보완하기 위해, Variant C와 무관한 새 합성 도면을 만들고 PNG로부터 새 mesh를 복원했다. 원래 비교한 개별 분석 A와 대표 공유 B만 사용했다.

## 결론

**대칭/반복이라는 가정이 확인된 범위만 그룹 적용해야 한다. 파츠별 원본 확인을 대표 한 개로 대체하면 예외 형상을 놓칠 수 있다. 정면·측면이 잘 맞아도 사선 형상이 틀릴 수 있으므로, 근거가 부족한 깊이/모서리는 승인하지 않고 보조 뷰를 확보해야 한다.**

이는 이번 세 합성 조건에서 직접 확인한 결과다. 실제 Variant C의 정확도나 LLM token 비용 절감률로 일반화하지 않는다.

## 원본과 정답 분리

정답을 알 수 있도록 Blender에서 3단 단면의 chamfered low-poly 파츠 12개를 생성했다. 세 케이스에 파츠 4개씩이다. 이때 만든 **정면/측면 PNG 24장**만 복원 입력으로 사용했다. 평가용 사선 12장과 정답 vertex/face는 `evaluator/`에 별도 보관했고, 복원 함수는 이 경로나 정답 JSON을 읽지 않는다.

두 방식 모두 camera/정사영 scale/section topology prior는 동일하게 제공했다. A는 파츠마다 정면·측면 silhouette에서 단면 너비·깊이·높이를 측정했다. B는 대표 FL만 측정하고 같은 형상을 네 파츠에 공유했다. 기존 v11 mesh나 Variant C 좌표를 사용하지 않았다. 고정 토폴로지의 단순한 inverse-graphics 실험이며, LLM 이미지 인식이나 임의 topology 복원 실험은 아니다.

평가 사선 camera는 입력의 0°/90°와 다른 방위각 37°·고도 24°다. 같은 camera에서 후보도 다시 렌더해 silhouette IoU를 비교했다. 형상은 정답과 대응 vertex의 RMSE로 별도 비교했다. 임의 image normalization이나 후보별 camera fitting을 하지 않았다.

사전 기준은 정규화 vertex RMSE≤1%, 평가 사선 IoU≥97%를 **모두** 만족하는 것이다. 값은 원본 생성 시 `public.json`에 기록했고 결과를 보고 바꾸지 않았다.

## 결과

표는 조건별 문제 파츠 RR의 결과다. 같은 케이스의 나머지 세 파츠도 모두 평가했다.

| 새 원본 조건 | A 개별 복원: 사선 IoU / vertex RMSE | B 대표 공유: 사선 IoU / vertex RMSE | 판정 |
|---|---|---|---|
| S01: 네 파츠가 실제로 동일 | 99.74% / 2.06mm | 99.74% / 2.06mm | 둘 다 통과 |
| S02: RR만 깊이가 22% 큼 | 99.31% / 2.46mm | 91.70% / 55.86mm | A 통과, B 실패 |
| S03: RR만 모서리 단면이 다름 | 84.92% / 111.39mm | 84.92% / 111.39mm | 둘 다 실패 |

각 방식의 전체 12개 파츠 기준 통과는 A 11/12, B 10/12였다. 서로 관련된 세 개의 의도된 조건이며 일반 데이터셋 정확도 추정치가 아니다.

S03의 FL과 RR 정면·측면 alpha silhouette는 실제로 pixel 단위까지 동일했다. 그런데 RR의 chamfer 계수가 .22에서 .55로 달라 평가 사선이 달라졌다. A/B 모두 공통 prior .22를 사용해 실패했다. 따라서 입력 두 뷰만으로 구별되지 않는 형상을 "정면·측면 일치"로 승인할 수 없다는 반례다. 이때는 추가 사선이나 내부 면/접힘선 정보가 필요하다.

## 속도와 비용

복원 코드만 3회 실행한 중앙값은 A 약 0.0530초, B 약 0.0138초였다. 이미지 decode·분석을 포함하지만 Blender 렌더와 개발/사람 검토 시간은 제외했다. 입력으로 읽은 고유 이미지는 A 24장, B 6장이다. 실행은 A 다음 B였으므로 cache 효과가 섞일 수 있으며 속도 배율을 일반화하지 않는다.

LLM inference를 호출하지 않았으므로 token 수와 모델 비용은 미측정이다. 사람의 최초 승인율·재수정 횟수·검토 시간도 측정하지 않았다. 자동 판정 실패를 사람의 수정 횟수로 대체하지 않았다.

## 검증과 수정 기록

- 36개 정답 reference/evaluator 렌더 및 72개 후보 평가 렌더를 Blender 5.2.2 LTS CLI / Cycles CPU / 640px / 12 samples / 최대8threads로 실행했다.
- 재구성 단계는 새 PNG에서 단면 수치를 읽어 24개 후보(A/B 각각12개)의 vertex/face를 새로 만들었다. 기존 형상을 복사한 replay가 아니다.
- S01의 반복 적용 통과, S02의 개별/공유 차이, S03의 두 방식 실패를 확인하는 runnable assertion이 모두 통과했다. 실패한 후보를 성공으로 처리하지 않았다.
- 최초 구현에서 수평 cap의 부분 coverage가 있는 마지막 pixel row를 측정해 S02 A에도 오차가 생겼다. 원본·정답·threshold는 그대로 두고 측정 row를 3px 안쪽으로 옮겼다. 200px보다 작은 profile은 거부하며 실제 저해상도/가림 도면에는 적용하지 않는다. 이전 실패 출력도 별도로 보존했다.
- Variant C 채택 blend·미채택 v11·state·contract·기존 reference/recipe hash는 이전 기록과 동일함을 재확인했다. 기존 모델/설계/승인은 변경하지 않았다.

## 재현과 산출물

1. 새 빈 디렉터리 ROOT를 만든다.
2. Blender `--background --factory-startup --disable-autoexec --python-exit-code 1 --python synthetic_blender.py -- source ROOT`.
3. 일반 Python `python synthetic_test.py reconstruct ROOT`.
4. 같은 Blender 옵션으로 `--python synthetic_blender.py -- evaluate ROOT`.
5. `python synthetic_test.py evaluate ROOT`.

Python 측 Pillow와 Blender 외 새 dependency는 추가하지 않았다. 저장 파일은 기존 결과를 덮어쓰지 않는다. 공개된 generator는 random seed 20261015를 고정한다. `source-generator-scene.blend`는 렌더 설정만 남은 생성용 scene이고 정답 mesh는 `evaluator/truth.json`에 있다.

[최종 측정 JSON](../results/synthetic-comparison.json)에 모든 파츠별 수치를 기록했다. 로컬 `synthetic-reference-test-final`에 새 원본, 정답, 복원 mesh JSON, 렌더, 비교판이 있다. 실제 게임 자산·불명확한 camera·복잡한 topology·가려짐·재질 경계나 모델별 token 효율은 검증 범위 밖이다.
