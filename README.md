# AI Modeling Pipeline

AI 보조 3D 모델링의 운영 절차와 offline evidence validator다. 자동 모델링/MCP 제작 실행기는 제공하지 않는다.

## 실행 순서

1. [PIPELINE.md](PIPELINE.md)를 읽고 [RUN 템플릿](templates/RUN.md)에 baseline·원본·scope·승인 설계를 기록한다.
2. [프로젝트 적용 가이드](docs/adapting-a-project.md)에 따라 `config.example.json`을 `config.local.json`으로 복사하고 실제 파일·hash를 등록한다. 자산은 Git에서 제외되는 `assets/`에 둔다.
3. 블록아웃은 교체 가능한 proxy로 취급한다. [Surface Re-evaluation Gate 계약](docs/surface-reevaluation.md)에 따라 모든 파츠의 여섯 표면 항목, 전후 렌더·geometry, 미해결 문제와 인간의 핵심 형상 승인을 기록한다.
4. `stage=detail-entry`에서 아래 검사를 실행한다. detail adapter는 **exit 0 및 `detail_allowed=true`**를 확인한 뒤에만 작업한다. `stage=final`은 별도의 최종 승인도 요구한다.

```console
python pipeline.py config.local.json
```

Python 3.11 이상, validator의 외부 패키지 의존성 없음. `config.example.json` 자체는 자료가 없어 차단되는 것이 정상이다. 파일·설정·증거가 바뀌면 해당 bundle을 재검토한다. 기존 설계와 자산은 보존하고 새 후보만 편집한다.

검사 통과는 증거와 승인 기록의 일관성을 뜻한다. 원본 적합성 자동 판정, 승인자 인증, 외부 DCC 작업 보호를 보증하지 않는다. 전후 evaluated mesh 추출은 `blender_surface_snapshot.py`를 사용하며 명령과 필드는 SRG 계약을 따른다.

## 개발 검증 및 선택적 사례

```console
python -m unittest -v
```

`BLENDER_BIN`을 지정하면 실제 Blender snapshot test도 실행하며, 없으면 해당 test를 skip한다. [검증·실험 요약](docs/verification.md)에 적용 한계와 선택적 실험 재현 명령을 모았다. [Minor On Air replay](examples/minor-on-air/README.md)와 합성 복원 코드는 실험용이며 실제 제작 실행 경로에 필요하지 않다.
