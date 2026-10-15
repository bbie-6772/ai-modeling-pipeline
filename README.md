# Minor On Air — Variant C 검증 파이프라인

확정된 Variant C의 형상을 변경하지 않고, 모델링 결과를 검토할 근거와 실험 기록을 관리하는 기반입니다. 기본 `pipeline.py`는 **offline evidence gate**입니다. 별도 `experiment.py`로 기존 발 외피 형상의 개별/그룹 적용과 CPU 렌더 pilot을 실행했습니다. MCP 연동과 새 원본의 자동 3D 복원은 구현하지 않았습니다.

## 빠른 실행

Python 3.11 이상, 외부 패키지 없이 실행합니다.

```console
python -m unittest -v
python pipeline.py config.example.json
```

첫 명령은 synthetic fixture 테스트입니다. 두 번째는 자료가 없는 샘플이므로 `blocked`, exit code 2가 정상입니다. `evidence-consistent`와 exit code 0도 파일 해시와 승인 기록의 일치만 뜻합니다. 설계 적합성이나 Blender 검증 성공을 뜻하지 않습니다.

## 실제 자료 연결

1. 저장소 안의 `assets/`에 승인된 설계 문서, 원본 이미지, baseline `.blend`, 별도 candidate `.blend`, 검토 보드를 배치합니다. 이 폴더는 Git에서 제외됩니다.
2. 루트에 `config.local.json`을 만들고 `config.example.json`을 복사합니다. `assets` 배열에 `role`, `path`, `sha256`을 기록합니다. 필수 role은 `design`, `reference`, `baseline`, `candidate`, `evidence`입니다. 각 파일은 서로 다른 경로여야 합니다. 여러 참조/보드 파일도 각각 등록합니다. 경로는 설정 파일 위치 기준 상대 경로이며 바깥 경로나 symlink 탈출은 거부합니다.
3. `pipeline.digest(Path(...))`로 파일별 SHA-256을 계산합니다. 승인 전에는 `pending`을 유지합니다. 사람이 검토한 후에만 `reviewer`, `reviewed_at`, `approved`를 기록합니다.
4. 승인 대상 bundle hash는 `{asset.path: asset.sha256}` 사전을 `json.dumps(hashes, sort_keys=True).encode()`한 바이트의 SHA-256입니다. 파일이나 보드가 바뀌면 새 bundle로 다시 검토합니다.
5. `python pipeline.py config.local.json`으로 기록 일치를 검사합니다. 이 스크립트는 파일을 쓰지 않습니다. 결과를 보관하려면 새 run 폴더에 stdout을 저장합니다.

승인 기록은 서명이 아닌 로컬 선언입니다. 작성자의 진위, 허위 승인, 잘못된 보드, 이미지와 모델의 정합성을 자동 판별하지 않습니다. 원본 보호도 이 검사기의 읽기 전용 동작에 한정됩니다. 외부 Blender/MCP 작업의 비파괴성까지 보증하지 않습니다.

## 문서

- [검증 설계와 실행 단계](docs/pipeline-design.md)
- [실험 및 테스트 계획](docs/experiments.md)
- [초기 결정 기록](docs/decisions/0001-evidence-first.md)
- [실행 결과](docs/verification.md)
- [두 방식의 최종 비교 결론과 검증 범위](docs/final-conclusion.md)
- [새 합성 원본의 이미지 기반 복원 결과](docs/synthetic-conclusion.md)

초기 구축 당시에는 원본 자산이 없었습니다. 이후 사용자가 제공한 로컬 continuation 폴더에서 기존 자료와 채택/미채택 모델을 확인했습니다. [첫 pilot 결과와 한계](docs/pilot-01.md), [측정 JSON](results/pilot-01.json)을 참고하세요. 원본과 후보 blend는 로컬에 유지합니다. 대화의 assistant 답변은 본문 대신 content-reference로 반환되어 과거의 상세 제안은 복구하지 못했습니다. 치수·topology·부품 목록·허용 오차를 추정하지 않습니다.
