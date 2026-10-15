# Minor On Air / Variant C 적용 예시

[run 템플릿](variant-c.run.example.json)은 공통 코어의 machine-robot profile을
사용한다. 실제 승인 설계·scope·파일·budget·hash·승인을 채우기 전에는 blocked다.
샘플 이름을 실제 승인이나 채택 상태로 취급하지 않는다.

일반 절차는 [모델링 workflow](../../docs/workflows/modeling.md), 필드는
[코어 계약](../../docs/contracts/game-asset-v1.md)을 따른다. 사례의 설계나
object 이름을 범용 코어에 고정하지 않는다. Variant C 회귀는
tests/unit/test_asset_pipeline.py에 있으며 미승인 revision과 baseline 변조를 검사한다.

과거 paw/ear replay는 [별도 실험 폴더](../../experiments/README.md)로 이동했다.
현재 validator에서 사용할 수 없는 variant-only 과거 설정은 Git 이력에만 남긴다.
