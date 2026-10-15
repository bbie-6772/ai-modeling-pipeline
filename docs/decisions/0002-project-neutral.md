# 0002 — AI Modeling Pipeline으로 일반화

상태: 사용자 요청으로 적용, 2026-10-15.

저장소 이름을 `ai-modeling-pipeline`으로 변경하고 private visibility와 commit 이력을 유지한다. 운영 절차·작업 템플릿·파일 검증은 특정 캐릭터와 분리하고, 기존 프로젝트의 replay는 `examples/minor-on-air/`에서 사례로 보존한다. 실험 수치와 당시 승인은 역사적 사실로 유지한다.

검증기의 고정 project/variant 비교는 제거한다. 대신 비어 있지 않은 `project`, `design_revision`을 요구하고 두 값과 파일 해시를 승인 bundle에 함께 묶는다. 다른 프로젝트나 설계 revision으로 바꾸면 같은 자산 파일이어도 과거 승인은 통과하지 않는다. 이전 hash를 자동으로 새 승인으로 이관하지 않는다.

Blender는 검증된 실행 예제이며 다른 DCC의 연동은 구현하지 않았다. 범용 운영 절차가 있다는 이유로 범용 자동 모델러라고 표시하지 않는다. 실제 프로젝트 파일이나 기존 모델·설계·승인 기록은 변경하지 않는다.
