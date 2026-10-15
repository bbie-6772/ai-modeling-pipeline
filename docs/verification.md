# 실행 결과 — 2026-10-15 KST

- 환경: Windows, Python 3.13. 외부 Python 패키지 없음.
- `python -m unittest -v`: 4개 테스트 메서드 및 내부 subtest 통과 (0.116초).
- `python pipeline.py config.example.json`: `blocked`, `No baseline assets`. 입력 없는 샘플의 의도된 거부입니다.
- 실제 Blender 실행, MCP 연결, `.blend` 보존 통합 테스트, crop/overlay/8방향 렌더, mesh 검사, E0~E3 실험: 미실행.
- GitHub Actions: workflow만 작성. 원격 실행 성공은 아직 확인하지 않음.

정상 fixture는 임시 텍스트 파일이며 실제 이미지나 `.blend`가 아닙니다. 따라서 테스트 성공은 offline gate 로직에만 적용됩니다.
