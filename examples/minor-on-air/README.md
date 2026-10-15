# Minor On Air — 보존된 프로젝트 사례

이 폴더는 특정 캐릭터의 과거 replay 실험 코드다. `N15_*` object, scene 이름과 `model_ear_v02_cpu.blend`/v11 파일을 전제로 하며 범용 실행기가 아니다.

일반 모델링 작업은 저장소 루트의 [PIPELINE.md](../../PIPELINE.md)를 따른다. 이 사례 코드를 다른 프로젝트에 그대로 실행하지 않는다. 사용자별 기본 경로는 제거했으며 재현에는 `--project`와 `--blender`를 명시해야 한다. 실제 자산과 외부 audit/helper도 별도로 필요하다.

기존 CLI 문법은 보존하되 Python 파일 경로는 이 폴더 기준으로 변경되었다. [과거 실험](../../docs/verification.md)의 수치·모델 승인은 해당 사례에만 해당한다.

[Variant C migration 템플릿](variant-c.run.example.json)은 범용 코어의 `machine-robot` profile을 사용한다. 실제 승인 설계·scope·예산·파일·hash를 등록하기 전에는 blocked다. 기존 자산이나 승인을 새로 만들거나 변경하지 않았다.

[과거 Variant C 설정](legacy-variant-c.config.json)은 project-neutral 전환 직전 Git 이력에서 복원한 미승인 설정이다. 새 코어로 실행하려면 migration 템플릿에 실제 값을 채운다. 이전의 variant 전용 승인 hash는 재사용하지 않는다. 기존 evidence tests는 그대로 보존하고 `test_asset_pipeline.py`에서 Variant C 사례·미승인 설계 변경·baseline 변조 거부를 추가 검증한다.
