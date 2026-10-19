# 개발 검증

저장소 루트에서 실행한다. 기본 테스트는 Python 표준 라이브러리만 사용한다.

```console
python -m unittest discover -v
python -m unittest discover -s tests/unit -t . -v
python -m unittest tests.unit.test_asset_pipeline -v
```

`tests/unit/`은 코어·Surface Gate·legacy CLI·단계 체크리스트와 파일 구조/문서 링크를 검사한다.
`tests/fixtures/`는 synthetic 자료만 만들며 실제 승인이나 asset 증거가 아니다.
공통 fixture가 테스트 케이스를 import하지 않아 unit/integration을 따로 실행할 수 있다.

## Blender 통합

PowerShell 예:

```powershell
$env:BLENDER_BIN = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
python -m unittest discover -s tests/integration -t . -v
python -m unittest discover -v
```

`BLENDER_BIN`이 없으면 통합 2개를 skip한다. 테스트는 임시 scene만 사용하며
실제 프로젝트를 열거나 변경하지 않는다. vertex 이동, 별도 process 재개방,
evaluated geometry/transform/modifier, 보호 object와 입력 hash 보존,
exporter 덮어쓰기 거부를 검사한다.

## 호환성과 템플릿

```console
python -m asset_pipeline templates/asset-run.example.json
python pipeline.py templates/legacy/surface-gate.example.json
```

미완성 템플릿의 blocked/exit 2는 정상이다. root pipeline.py, surface_gate.py,
blender_surface_snapshot.py, asset_pipeline.blender_adapter 호환 진입점을 유지한다.
기존 config를 옮길 때는 등록 asset 상대 경로도 config 부모 기준으로 조정한다.

CI는 Python 3.11/3.13에서 전체 discovery를 실행한다. 이 두 job의 Blender skip과
별도 `blender-integration` job을 구분한다. 통합 job은 Ubuntu 24.04에서 공식 Blender
4.5.3 Linux x64 배포본을 고정 SHA-256으로 검사하고 실제 통합 테스트를 실행한다.
실행 파일 누락·테스트 0개·skip은 실패다. 최신 실행 결과는 PR Checks를 확인한다.

## 검증 범위

hash·경로·scope·16개 QA·profile 예외·단계·승인·issue loop·geometry 이력과
마지막 회귀·SRG·엔진 보고서 계약·KPI 일관성을 다룬다. 엔진 report는 synthetic
fixture로 검사하며 Unity/Unreal을 실행하지 않는다. 자동 visual judge,
production Variant C 정확도, token/인간 검토 시간 절감, 실제 모델의 엔진 통과는
미검증이다. 선택적 연구 재현은 [experiments](../experiments/README.md)에서 시작한다.
