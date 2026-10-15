# AI Modeling Pipeline

**[최종 운영 파이프라인](PIPELINE.md)부터 읽고 [작업 템플릿](templates/RUN.md)을 복사해 시작하세요.**

캐릭터·소품·제품·하드서피스 등 AI가 참여하는 3D 모델링 작업에 적용하는 검증 중심 운영 파이프라인입니다. 원본 분석은 파츠별로 수행하고, 동일성이 확인된 반복 적용만 그룹으로 처리합니다. 블록아웃은 수정/교체 가능한 proxy이며, 디테일 전에 [Surface Re-evaluation Gate](docs/surface-reevaluation.md)에서 모든 파츠의 여섯 표면 항목과 실제 기존 면 변화를 재검토하고 인간의 핵심 형상 승인을 확인합니다. 기본 검토는 원본 overlay·조립 사선·대표 확대이며 불확실한 부분은 추가 뷰로 확인합니다. 각 프로젝트의 승인 설계와 원본은 보존하고, 승인된 후보만 채택합니다.

이 저장소는 운영 절차·기록 템플릿·보조 검사·실험 코드를 제공합니다. 도구 중립적인 절차와 파일 검증을 사용할 수 있으며, 실행 예제와 렌더 실험은 Blender로 검증했습니다. 다른 DCC 연동이나 자동 모델링/MCP 실행기는 구현하지 않았습니다. `pipeline.py`는 **offline evidence gate**이며, 합성 PNG 복원 코드는 camera와 topology가 정해진 실험 전용입니다.

## 새 프로젝트에서 시작

1. [프로젝트 적용 가이드](docs/adapting-a-project.md)를 읽고 프로젝트·승인 설계 revision·원본·대상 도구를 정합니다.
2. [작업 템플릿](templates/RUN.md)을 복사해 baseline·파츠·허용 변경 범위를 기록합니다.
3. [운영 절차](PIPELINE.md)에 따라 분석, 승인, 별도 후보 제작, 보호 검사와 결과 검토를 진행합니다.
4. 기존 사례의 object 이름·경로·허용 오차·승인을 새 프로젝트로 가져오지 않습니다.

## 보조 검사 실행

Python 3.11 이상, 외부 패키지 없이 실행합니다.

```console
python -m unittest -v
python pipeline.py config.example.json
```

첫 명령은 fixture 테스트입니다. 두 번째는 자료가 없는 샘플이므로 `blocked`, exit code 2가 정상입니다. `evidence-consistent`와 exit code 0도 SRG 증거·geometry 변화·승인 기록의 일관성만 뜻합니다. `detail_allowed=true`도 원본 적합성 자동 인증이 아닙니다. 모델의 설계 적합성이나 DCC 검증 성공을 뜻하지 않습니다.

## 실제 자료 연결

1. 저장소 안의 `assets/`에 승인된 설계 문서, 원본 이미지, baseline과 별도 candidate 파일, 검토 보드를 배치합니다. 형식은 `.blend`, `.fbx` 등 실제 작업에 맞춥니다. 이 폴더는 Git에서 제외됩니다.
2. 루트에 `config.local.json`을 만들고 `config.example.json`을 복사합니다. `project`는 프로젝트 이름, `design_revision`은 검토 대상 설계 식별자입니다. `assets` 배열에 `role`, `path`, `sha256`을 기록합니다. 기존 필수 role은 `design`, `reference`, `baseline`, `candidate`, `evidence`이며, SRG용 `blockout`, `geometry`, `render`, `alignment`, `human-review`도 [필드 계약](docs/surface-reevaluation.md)에 맞춰 등록합니다. `scope`, `stage`, `surface_review`는 필수입니다. 각 파일은 서로 다른 경로여야 합니다. 여러 참조/보드 파일도 각각 등록합니다. 경로는 설정 파일 위치 기준 상대 경로이며 바깥 경로나 symlink 탈출은 거부합니다.
3. `pipeline.digest(Path(...))`로 파일별 SHA-256을 계산합니다. 승인 전에는 `pending`을 유지합니다. 사람이 검토한 후에만 `reviewer`, `reviewed_at`, `approved`를 기록합니다.
4. `{asset.path: asset.sha256}` 사전과 설정을 `pipeline.bundle_digest(config, hashes)`에 전달해 승인 대상 hash를 계산합니다. 전체 설정과 파일 해시를 묶으며 최종 승인 객체만 제외합니다. 핵심 형상 승인은 먼저 `surface_gate.surface_digest(config, hashes)`로 별도 결속합니다. 프로젝트/설계나 파일·보드가 바뀌면 기존 승인 hash를 재사용하지 않습니다.
5. `python pipeline.py config.local.json`으로 기록 일치를 검사합니다. 이 스크립트는 파일을 쓰지 않습니다. 결과를 보관하려면 새 run 폴더에 stdout을 저장합니다.

승인 기록은 서명이 아닌 로컬 선언입니다. 작성자의 진위, 허위 승인, 잘못된 보드, 이미지와 모델의 정합성을 자동 판별하지 않습니다. 원본 보호도 이 검사기의 읽기 전용 동작에 한정됩니다. 외부 DCC/MCP 작업의 비파괴성까지 보증하지 않습니다. 이전 `variant` 설정과 파일 전용 bundle hash의 이관 방법은 [적용 가이드](docs/adapting-a-project.md)를 따릅니다.

## 문서

- [Surface Re-evaluation Gate — 필드·실행·제약](docs/surface-reevaluation.md)
- [SRG 검증 기록 — 실제 실행과 미검증 범위](docs/surface-verification.md)
- [최종 운영 파이프라인 — 시작점](PIPELINE.md)
- [작업 기록·체크리스트 템플릿](templates/RUN.md)
- [새 프로젝트 적용 및 설정 이관](docs/adapting-a-project.md)

- [검증 설계와 실행 단계](docs/pipeline-design.md)
- [실험 및 테스트 계획](docs/experiments.md)
- [초기 결정 기록](docs/decisions/0001-evidence-first.md)
- [실행 결과](docs/verification.md)
- [두 방식의 최종 비교 결론과 검증 범위](docs/final-conclusion.md)
- [새 합성 원본의 이미지 기반 복원 결과](docs/synthetic-conclusion.md)

## 사례와 검증 범위

특정 캐릭터에서 시작한 [Minor On Air replay 사례](examples/minor-on-air/README.md)는 별도 예제로 보존했습니다. 과거 실험 문서와 결과 수치는 해당 조건의 기록이며 새 프로젝트의 승인/정확도 보증이 아닙니다. 합성 실험은 보정 camera·깨끗한 silhouette·고정 topology 조건에 한정됩니다. 원본·후보 자산과 개인 경로는 일반 설정에 포함하지 않습니다.

Blender snapshot integration test도 실행하려면 `BLENDER_BIN`에 실제 Blender 실행 파일 경로를 지정하고 같은 unittest 명령을 실행합니다. 지정하지 않으면 해당 test는 skip되며 offline 테스트만 실행됩니다. snapshot exporter는 기존 scene을 저장하지 않고 새 JSON만 배타적으로 생성합니다.
