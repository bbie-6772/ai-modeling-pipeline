# 새 프로젝트에 적용하기

이 저장소를 캐릭터·소품·제품 등 새 자산에 적용할 때 아래 정보만 먼저 정한다. 과거 사례의 이름이나 경로를 코드에 다시 고정하지 않는다.

| 항목 | 정할 내용 |
|---|---|
| 프로젝트 | `project` 이름과 검토 대상 `design_revision` 식별자 |
| 입력 | 승인 설계·원본 이미지/도면·채택 baseline과 해시 |
| 작업 범위 | object/collection 이름, 수정할 geometry/transform 등과 보호 범위 |
| 도구 | DCC·버전·AI 모델·MCP/CLI 연결 방법, 읽기 전용 audit 및 변경 guard 유무 |
| 규격 | 좌표계·단위·scale, topology/UV/material 요구, target engine/export 형식 |
| 검토 | renderer/해상도, camera 근거, 검토자와 승인 기록 위치 |
| 산출물 | 새 run 경로, 후보 파일 형식, 검토 보드와 검사 결과 |

절차는 [PIPELINE.md](../PIPELINE.md), 기록은 [RUN 템플릿](../templates/RUN.md)을 사용한다. Blender 외 DCC에서도 절차와 파일 해시 검사는 사용할 수 있지만 scene 검사·렌더·저장/재개방 자동화는 해당 도구에서 구현하고 검증해야 한다. 없는 기능이 작동한다고 가정하지 않는다.

## 설정 예시와 역할

`config.example.json`의 `project`와 `design_revision`은 임의의 비어 있지 않은 문자열이다. 예를 들어 `project="Furniture"`, `design_revision="chair-v4"`를 사용할 수 있다. 샘플은 승인 전 빈 자료 상태이므로 검사는 차단되어야 한다.

이 설정은 detail-entry/final 파일·SRG·승인 기록 검사에 사용한다. `scope`와 `surface_review`를 [SRG 계약](surface-reevaluation.md)에 맞춰 채우고, 핵심 형상 직접 승인과 최종 승인을 분리한다. object 편집 범위나 단계별 모델링 실행을 자동 제어하지 않는다. 실제 자산은 무시되는 `assets/`에, 로컬 설정은 무시되는 `config.local.json`에 둔다. paths는 설정 파일 위치 기준 상대 경로다.

1. 각 파일의 hash는 `pipeline.digest(Path(...))`로 계산한다.
2. `hashes = {asset['path']: asset['sha256'] for asset in config['assets']}`를 만든다.
3. 실제 검토한 프로젝트/설계/자료 묶음의 hash는 `pipeline.bundle_digest(config, hashes)`로 계산한다.
4. 직접 사용자 검토 후에만 `approval.status`, `reviewer`, `reviewed_at`, `bundle_sha256`를 기록한다.
5. `python pipeline.py config.local.json`으로 일치를 확인한다. 성공은 모델의 시각적/설계적 정확도 인증이 아니다.

## 이전 설정에서 이관

이전 프로젝트 전용 `variant` 키는 일반적인 `design_revision`으로 변경되었다. `variant="C"`라면 실제 승인된 설계를 식별할 수 있도록 `design_revision="variant-c-approved-<revision>"`처럼 사용자가 확인한 이름을 부여한다. 새 프로젝트를 기존 사례의 이름으로 위장하지 않는다.

승인 bundle은 예전의 파일 hash 사전만 포함하던 방식에서 **project + design_revision + assets**를 포함하는 방식으로 바뀌었다. 기존 bundle hash는 그대로 통과하지 않는다. 자동 승인 이관은 하지 않으며, 기존 직접 승인 증거가 정확히 어떤 프로젝트/설계/파일에 해당하는지 재검토하고 기록한다. 코드의 검사 결과 키 `blender_validation`은 도구 중립적인 `model_validation`으로 바뀌었다.

기존 replay 파일 세 개는 `examples/minor-on-air/`로 이동했다. 해당 코드의 object/scene/파일명은 그 사례의 기록이며 수정할 필요가 없는 역사적 정보다. 사용자별 기본 경로는 제거했고, 재현할 때 `--project`와 `--blender`를 직접 지정해야 한다.

## v1.2 SRG 이관

이전 설정은 SRG 자료 없이 통과하지 않는다. 원본과 전후 snapshot/render/alignment, 모든 파츠의 여섯 항목, 수정/재구성 판단, 미해결 차이/불확실성, 직접 core 승인 근거를 새 run에 등록한다. 기존 설계 승인을 core 승인으로 복사하지 않는다. `surface_digest`는 core 승인 hash만 제외한 surface review와 project/design/scope/assets에, `bundle_digest`는 최종 승인 객체만 제외한 전체 설정에 결속한다. 과거 hash는 자동 이관하지 않는다. 외부 실행기에는 exit 0과 `detail_allowed=true` 검사를 detail 명령 직전에 연결한다.
