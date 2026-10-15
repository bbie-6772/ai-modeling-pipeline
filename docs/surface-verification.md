# SRG 검증 기록 — 2026-10-15 KST

대상 저장소: private `bbie-6772/ai-modeling-pipeline`. 시작점은 `main`의 `6d0c9417a66c4215b8229e54315370f6e9cb4ba6`이며 별도 `feat/surface-reevaluation-gate` 브랜치에서 작업했다. 이전 대화에서 assistant 본문은 content-reference만 반환되므로 구현 근거는 사용자의 현재 요구사항과 실제 저장소 코드/문서다.

## 실제 실행

- Windows / Python 3.14.3 / Blender 5.2. 외부 Python 패키지 추가 없음.
- `BLENDER_BIN`을 설치된 Blender 경로로 지정하고 `python -m unittest -v`: **23개 테스트, 13.428초, 모두 통과, skip 없음**.
- offline 테스트 22개: 기존 hash/project/design/path/승인 검사, 전체 scope/여섯 항목 누락, pending core 승인, final 승인 분리, metadata/승인 진술 변경에 따른 stale 처리, blocking issue, 명시적 비차단 불확실성의 재승인, added-detail-only 거부, retain/rebuild, camera 변경·stale geometry manifest, nonfinite 좌표, snapshot source/scope 결속, winding·vertex 재번호, 정상 CLI와 빈 sample 차단을 확인했다.
- Blender integration 1개: 임시 새 cube scene에서 전후 `.blend`를 만들고 별도 Blender process로 exporter를 실행했다. 실제 vertex 하나 이동, world transform 반영, Triangulate modifier의 evaluated 12 faces, 원본 파일 hash 보존, 기존 JSON 출력의 overwrite 거부를 확인했다. 임시 파일은 테스트 종료 후 제거된다.
- `config.example.json`은 자료가 없어 `blocked`, exit 2, `detail_allowed=false`인 것을 CLI 테스트에서 확인했다.
- `git diff --check`: 통과.

## 해석과 남은 작업

offline fixture의 render는 **텍스트 placeholder**이며 승인 진술도 **synthetic-only**다. 이번 변경에서 실제 원본 대비 렌더/overlay나 Variant C 형상 평가를 실행하지 않았다. Blender integration은 실제 geometry exporter를 검증하며 원본 인식·형상 정확도·인간 승인·MCP 작업을 검증하지 않는다. 기존 실험/결과 파일은 수정하지 않았다. 외부 Variant C 설계/채택 모델/후보 자산은 열거나 수정하지 않았다.

CI는 Python 3.11/3.13에서 offline 테스트를 실행하도록 설정했다. `BLENDER_BIN` 없는 CI에서는 integration test 1개가 명시적으로 skip된다. 로컬에서 이 두 Python 버전을 실행했다고 주장하지 않는다. CI 결과는 PR의 실제 Actions 결과를 확인한다.

SRG는 현재 production artifact인 offline validator에 필수 조건으로 연결했다. 실제 제작 실행기가 없는 저장소이므로 외부 Blender/MCP 호출까지 자동 통제하지 않는다. 다음 실제 자산 run에서는 [SRG 계약](surface-reevaluation.md)의 순서대로 approved scope와 자료를 채우고, 프로젝트 adapter에 exit/JSON gate 검사를 detail 호출 직전에 연결한 뒤 전후 렌더·보호 검사와 직접 인간 승인을 수행해야 한다. hash와 선언 기록은 승인자 인증이나 진실한 snapshot/manifest의 자동 보증이 아니다.
