# 0001 — 설계 동결과 증거 일치 검사를 먼저 구현

초기 프로젝트에서의 역사적 결정 기록이다. 현재 저장소는 `ai-modeling-pipeline`으로 일반화했으며 운영 절차와 설정은 루트 문서를 따른다. 아래 초기 계정/경로/프로젝트 정보는 현재 작업 지시가 아니다.

상태: 파이프라인 구현 결정. Variant C 디자인 승인 기록이 아님.

기존 대화는 파츠별 검토의 정확도와 일괄 처리의 재수정 문제를 설명하지만 상세 설계와 자산은 포함하지 않습니다. 따라서 형상을 만들거나 추정 치수로 검증하지 않고 읽기 전용 파일 gate부터 구축합니다.

Python 표준 라이브러리와 unittest를 사용합니다. JSON을 설정 형식으로 사용하고 외부 schema/영상 라이브러리는 추가하지 않습니다. Blender/MCP 실행, 이미지 지표, 비동기 agent orchestration은 실제 입력과 실험 근거가 생길 때 추가합니다.

기존 `bbie-6772/2d-survivor`의 README와 `docs/conventions.md`에서 한국어 문서, `docs/decisions`, Conventional Commits, main 기반 소규모 작업 관행을 확인했습니다. 해당 프로젝트의 C#/Unity 규칙과 멘토 모드는 가져오지 않습니다.

연결 GitHub 계정은 bbie-6772, 활성 CLI 계정은 yoon7270으로 달랐습니다. 사용자가 bbie-6772를 선택했습니다. 접근 가능한 bbie-6772 저장소 18개에 `minor-on-air-variant-c-pipeline` 이름은 없었습니다. 연결 도구에는 저장소 생성 endpoint가 없고 bbie-6772 CLI 인증은 유효하지 않아 브라우저 로그인 또는 사용자 생성이 필요합니다. 다른 계정에 대신 만들지 않습니다.
