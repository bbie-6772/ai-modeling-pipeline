# 선택적 실험

기본 모델링·QA·개발 테스트에는 필요하지 않다. 실험 재현이 요청된 경우에만
읽고 실행한다. 코어는 이 폴더나 Pillow에 의존하지 않는다.

| 위치 | 목적 | 외부 입력 |
|---|---|---|
| synthetic/ | 보정된 합성 PNG의 고정 topology 복원·held-out 평가 | Blender, 일반 Python의 Pillow, 새로운 빈 ROOT |
| minor-on-air/ | 과거 paw/ear 개별 처리·그룹 처리 replay | 당시 프로젝트·baseline·recipe·audit/guard/helper·Pillow·Blender |
| [drawing_batch/](drawing_batch/README.md) | 동일 결과물의 뷰별/묶음 도면 생성 wall time 비교 | 고정 source·parts·case decision·Blender·새 plan/run |

합성 복원:

```console
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python experiments/synthetic/blender.py -- source ROOT
python experiments/synthetic/evaluate.py reconstruct ROOT
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python experiments/synthetic/blender.py -- evaluate ROOT
python experiments/synthetic/evaluate.py evaluate ROOT
```

Minor On Air의 run_experiment.py가 같은 폴더 experiment.py를 호출하며,
analyze_experiment.py는 기존 replay 출력을 비교한다. --project/--blender와
recipe를 명시해야 한다. 외부 파일은 제공하지 않으며 재현 전 script의 CLI와
고정된 scene/object/입력 계약을 확인한다.

기존 실험은 검증된 반복 부품의 그룹 적용과 숨은 깊이·모서리의 추가 뷰 필요성을
보여주는 제한된 사례다. 렌더 시간 차이를 전체 AI 작업/인간 검토/token 절감으로
해석하지 않는다. 실제 Variant C 정확도·일반 도면 인식·범용 DCC/engine 연동을
검증하지 않았다. 과거 raw 측정과 제외/실패 이력은
[측정 자료가 남은 Git snapshot](https://github.com/bbie-6772/ai-modeling-pipeline/tree/04d5303e4efdd9c44e403a9050179a58f749ba35)에서 조회한다.
