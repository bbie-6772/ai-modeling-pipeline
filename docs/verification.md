# 검증·실험 요약

운영 시에는 [PIPELINE](../PIPELINE.md)과 [SRG 계약](surface-reevaluation.md)을 따른다. 이 문서는 테스트 범위와 과거 실험의 적용 한계만 요약한다.

## 재검증

```console
python -m unittest -v
python pipeline.py config.example.json
```

- 첫 명령은 offline 회귀 테스트다. `BLENDER_BIN`에 Blender 실행 파일을 지정하면 snapshot integration test도 실행하며, 없으면 해당 1개를 skip한다.
- 두 번째 명령은 자료 없는 설정이므로 `blocked`, exit 2, `detail_allowed=false`가 정상이다.
- SRG 구현 검증(2026-10-15): Windows / Python 3.14.3 / Blender 5.2에서 23개 테스트 모두 통과. CI Python 3.11/3.13도 성공했으며 Blender test는 skip했다. 현재 변경의 검증 상태는 PR Checks를 따른다.
- offline 검사는 hash·경로·scope·여섯 표면 항목·승인 결속·정렬·미해결 문제·geometry delta를 다룬다. render/승인 fixture는 synthetic placeholder다.
- Blender integration은 임시 cube의 실제 vertex 이동, world transform, evaluated Triangulate modifier, source hash 보존 및 출력 덮어쓰기 거부를 검증한다.

## 과거 실험에서 유지할 결론

| 사례 | 관측 및 적용 한계 |
|---|---|
| 기존 Minor On Air 형상 replay | 검증된 반복 부품의 그룹 적용은 형상을 유지했다. 렌더 수 축소의 시간 차이를 전체 AI 모델링 시간 절감으로 해석하지 않는다. 초기 pilot은 최종 비교에서 제외됐다. |
| 보정된 합성 PNG·고정 topology 복원 | 깊이 예외를 대표 공유가 놓쳤고, 입력 두 뷰로 식별할 수 없는 모서리는 두 방식 모두 실패했다. 파츠별 재확인과 추가 뷰가 필요하다. |
| 공통 한계 | 실제 Variant C 정확도, 원본 일반 인식, 사람 검토·재수정·token 절감, 범용 DCC/MCP/engine 연동은 검증하지 않았다. 실험 threshold를 실제 자산에 전용하지 않는다. |

반복된 실행 보고서·초기 계획·raw 측정 JSON은 현재 트리에서 제거했다. 상세 수치와 실패/제외 이력은 [정리 전 Git snapshot](https://github.com/bbie-6772/ai-modeling-pipeline/tree/04d5303e4efdd9c44e403a9050179a58f749ba35)에서 복구할 수 있다. 재현 코드는 보존했다. 실제 승인·자산별 전후 증거·보호 검사 기록은 정리 대상이 아니다.

## 선택적 실험 재현

Minor On Air replay는 [사례 안내](../examples/minor-on-air/README.md)를 따른다. 합성 복원은 Pillow와 Blender가 필요하며 새 빈 `ROOT`에만 실행한다.

```console
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python synthetic_blender.py -- source ROOT
python synthetic_test.py reconstruct ROOT
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python synthetic_blender.py -- evaluate ROOT
python synthetic_test.py evaluate ROOT
```
