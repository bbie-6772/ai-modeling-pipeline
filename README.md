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

출력은 token을 아끼기 위해 한 줄 JSON이다. 사람이 읽을 때는 `| python -m json.tool`을 붙인다. 템플릿은 자료·budget·승인이 없으므로 `blocked`, exit 2가 정상이다. 통과는 증거 기록의 일관성을 뜻하며 형상 정확도나 승인자 신원을 인증하지 않는다. 실제 인간 승인과 정확한 bundle을 연결한다.

## 목적별 경로

| 목적 | 파일/문서 |
|---|---|
| 에이전트 상황별 시작점 | [AGENTS.md](AGENTS.md) |
| 코어·profile·QA·수정·승인 | [game-asset-v1](docs/contracts/game-asset-v1.md) |
| 단계별 체크리스트(조언용, 읽기 전용) | `python -m asset_pipeline.planner RUN.json` — [모델링 절차 1.1](docs/workflows/modeling.md) |
| Blender snapshot·Surface Gate | [surface-gate](docs/contracts/surface-gate.md) |
| 동일 모델의 정투영 3뷰·치수·파츠 표시 | [도면 생성](docs/workflows/drawings.md), `python -m asset_pipeline.drawing --help` |
| 관측/추정 형상 계약·도면 대조 | [형상 계약](docs/contracts/shape-contract.md), `python -m asset_pipeline.shape_contract --help` |
| AI 시안 요청·미승인 후보·계약 초안 | [시안 후보](docs/workflows/concepts.md), `python -m asset_pipeline.concept --help` |
| 정적 mesh Unity 인계·Play Mode smoke | [Unity 인계](docs/workflows/unity.md), `python -m asset_pipeline.unity --help` |
| 기존 detail-entry/final 설정 | [legacy 템플릿](templates/legacy/surface-gate.example.json), `python pipeline.py CONFIG.json` |
| Variant C | [Minor On Air](examples/minor-on-air/README.md) |
| 개발 테스트 | [testing](docs/testing.md) |
| 선택적 과거 실험 | [experiments](experiments/README.md) |
| 배치·삭제 근거·호환 경로 | [repository map](docs/repository-map.md) |

```console
python -m unittest discover -v
```

Blender 통합 테스트는 `BLENDER_BIN`을 지정하면 실행한다. 자동 이미지 판독·범용 모델 생성·MCP production 실행·Unreal runner는 미구현이다. Unity runner는 새 프로젝트의 정적 geometry import와 headless Play Mode smoke에 한정하며 target-runtime 성능 검증은 별도다. Blender 편집은 승인된 local-space vertex plan을 새 후보에 적용하는 범위이며 성공해도 QA 대기 상태다.
