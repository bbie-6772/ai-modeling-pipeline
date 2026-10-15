# AI Modeling Pipeline

게임 3D 에셋의 제작 단계·QA·수정·인간 승인·증거를 관리하는 Python 코어다. 7개 Asset Profile과 제한된 Blender vertex 편집 adapter를 제공한다. Python 3.11 이상이며 코어는 외부 패키지 의존성이 없다.

## 새 작업 시작

1. [모델링 절차](docs/workflows/modeling.md)를 읽고 [RUN 기록](templates/RUN.md)에 채택 baseline·후보·참조·정확한 변경 scope를 기록한다.
2. [run 설정](templates/asset-run.example.json)을 새 `runs/RUN_ID/run.json`에 복사한다. 경로 기준은 **설정 파일의 부모 폴더**다. 해당 run 아래 원본/후보/증거를 따로 두고 실제 파일·SHA-256을 등록한다.
3. 승인된 design revision·제약·단위·엔진·budget·feature를 채우고 [프로필](profiles/assets.json)을 선택한다. 모르는 값과 미승인 상태를 임의로 채우지 않는다.
4. [코어 계약](docs/contracts/game-asset-v1.md)에 따라 단계·QA·이력·승인을 기록한다. detail 전에는 [Surface Gate](docs/contracts/surface-gate.md)도 충족해야 한다.

```console
python -m asset_pipeline runs/RUN_ID/run.json
```

템플릿은 자료·budget·승인이 없으므로 `blocked`, exit 2가 정상이다. 통과는 증거 기록의 일관성을 뜻하며 형상 정확도나 승인자 신원을 인증하지 않는다. 실제 인간 승인과 정확한 bundle을 연결한다.

## 목적별 경로

| 목적 | 파일/문서 |
|---|---|
| 에이전트 상황별 시작점 | [AGENTS.md](AGENTS.md) |
| 코어·profile·QA·수정·승인 | [game-asset-v1](docs/contracts/game-asset-v1.md) |
| Blender snapshot·Surface Gate | [surface-gate](docs/contracts/surface-gate.md) |
| 기존 detail-entry/final 설정 | [legacy 템플릿](templates/legacy/surface-gate.example.json), `python pipeline.py CONFIG.json` |
| Variant C | [Minor On Air](examples/minor-on-air/README.md) |
| 개발 테스트 | [testing](docs/testing.md) |
| 선택적 과거 실험 | [experiments](experiments/README.md) |
| 배치·삭제 근거·호환 경로 | [repository map](docs/repository-map.md) |

```console
python -m unittest discover -v
```

Blender 통합 테스트는 `BLENDER_BIN`을 지정하면 실행한다. 자동 이미지 판독·범용 모델 생성·MCP production 실행·Unity/Unreal runner는 미구현이다. Blender 편집은 승인된 local-space vertex plan을 새 후보에 적용하는 범위이며 성공해도 QA 대기 상태다.

## 범용 AI 에셋 생성 계획 (작업 브랜치)

[일반적인 AI 제작 파이프라인](docs/workflows/ai-generation.md)은 제작 순서와 구현 로드맵을 정의한다. 기존 8-stage evidence/QA/인간 승인 계약은 유지한다. 추가된 read-only planner는 55개 작업, feature별 생략, 4개 검토 게이트, 의존 순서를 JSON으로 출력한다. **생성·Blender MCP 제어·엔진 자동 검증 기능이 구현되었다는 뜻은 아니다.**

```console
python -m asset_pipeline.plan_cli templates/ai-plan-request.example.json
python -m asset_pipeline.plan_cli templates/ai-plan-request.example.json --output asset-plan.json
python -m unittest tests.unit.test_planner -v
```

`asset-plan.json`은 새 파일로만 생성한다. 등록된 baseline/candidate나 승인 상태는 변경하지 않는다. 계획의 task 상태 `not-executed`와 gate 상태 `unverified`는 실제 QA 통과와 다르다. 기존 `python -m asset_pipeline RUN.json` 경로만 실증 자료의 일관성과 승인 조건을 판단한다.
