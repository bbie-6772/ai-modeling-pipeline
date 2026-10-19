# 고정 모델의 도면 생성 묶음 실행 검증

```console
python experiments/drawing_batch/benchmark.py --plan PLAN.json --output NEW_OUTPUT_DIRECTORY
```

이 실험은 기존 drawing generator의 묶음 실행 효과를 검증한다. 새 geometry·설계·승인을 만들지 않는다.
A는 뷰마다 snapshot 추출과 render를 독립 실행(실제 Blender process 6회), B는 기존 generator로
snapshot 한 번과 3뷰 render를 묶어 실행(2회)한다. 최종 PNG/SVG·snapshot·parts·camera 설정·sheet
10개 파일의 SHA-256이 정확히 일치해야 시간 비교를 인정한다. A는 구성한 기술 비교 조건이며
관측한 사람의 수작업 baseline이 아니다.

plan에는 source/parts/case_decision/blender의 실제 경로, source_sha256, Blender 버전,
meters_per_pixel/resolution/center_m/units/timeout_seconds, runner_sha256, 모든 입력과 런타임
Python 코드의 input_hashes를 고정한다. 현재 order는 `ABBA, BAAB, ABBA` 6쌍이며 워밍업 A/B 각 1회는
통계에서 제외한다. 실행 entry부터 drawing manifest 완성까지의 wall time을 측정하고, 출력 동등성과
동결 입력 검사는 시간 측정 밖에서 양쪽에 동일하게 적용한다. 실제 subprocess 호출과 소요 시간도 기록한다.

새 출력 폴더만 허용한다. 실패·제외·unknown은 보존하며 retry나 trial 대체를 하지 않는다.
`trials.jsonl`과 `summary.json`, 실제 각 조건 출력 및 plan을 보존한다. 바이트가 달라진 코드나
새 case에는 새 plan과 새 run을 사용한다. OS/driver cache는 초기화하지 않으므로 warm cache
조건의 단일 host·단일 case 결과로 해석한다. 전체 모델링·사람 검토·AI token·Unity 성능 절감은
측정하지 않으며 null로 남긴다. 실제 자산의 품질 판정으로 이 수치를 재사용하지 않는다.
