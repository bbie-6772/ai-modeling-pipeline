# 실행 결과 — 2026-10-15 KST

- 환경: Windows, Python 3.13. 외부 Python 패키지 없음.
- `python -m unittest -v`: 4개 테스트 메서드 및 내부 subtest 통과 (0.116초).
- `python pipeline.py config.example.json`: `blocked`, `No baseline assets`. 입력 없는 샘플의 의도된 거부입니다.
- 초기 구축 당시 실제 Blender/MCP/모델 실험은 미실행. 이후 Blender CLI 기반 발 외피 replay와 보존·재개방 검사를 수행했으며 범위와 결과는 [pilot-01](pilot-01.md)에 별도로 기록했습니다. MCP 연결과 전체 E0~E3 workflow 비교는 여전히 미실행입니다.
- GitHub Actions: 구현 commit `0301815`의 [run 38685041423](https://github.com/bbie-6772/minor-on-air-variant-c-pipeline/actions/runs/38685041423)에서 test job 및 unittest step `completed/success` 확인. 문서 갱신 이후 run은 별도 확인 대상입니다.

정상 fixture는 임시 텍스트 파일이며 실제 이미지나 `.blend`가 아닙니다. 따라서 테스트 성공은 offline gate 로직에만 적용됩니다.

이후 두 방식의 교차 조건을 각 3회(총 12개 후보) 실행하고 모든 후보의 저장/재개방·보호·mesh 검사를 통과했습니다. 대표 정면 pixel과 world vertex가 전 조건에서 동일했습니다. 기본 offline 테스트 4개도 다시 통과했습니다. 전체 과정, 제외한 준비 실행, 미측정 항목은 [최종 비교 기록](final-conclusion.md)에 명시했습니다.
