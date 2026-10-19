# 동일 모델의 정투영 도면 생성

저장된 `.blend`에서 선택한 mesh 파츠를 evaluated world snapshot으로 한 번 추출하고,
그 동일 snapshot으로 정면·측면·평면을 렌더한다. 원본은 저장하거나 변경하지 않는다.
Blender background process 두 번(snapshot 추출, 세 뷰 렌더)을 사용하며 기본 렌더는
저비용 Workbench이다. AI 시안 생성·도면에서의 형상 추정·설계 승인을 수행하지 않는다.

`parts.json`은 snapshot exporter와 같은 명시적 object 목록이다.

```json
{"body": ["Body"], "top-part": ["TopPart"]}
```

```console
python -m asset_pipeline.drawing model.blend --blender "C:/path/to/blender.exe" --parts parts.json --output runs/drawing-01 --meters-per-pixel 0.002 --resolution 640 --center 0 0 0 --units mm
```

`--center`는 meter 기준 world 중심점이다. 세 뷰 모두 같은 중심점과 meter-per-pixel을
사용한다. 정면은 -Y에서 +Y를 보고 가로 X·세로 Z, 측면은 +X에서 -X를 보고 가로 Y·세로 Z,
평면은 +Z에서 -Z를 보고 가로 X·세로 Y다. bbox를 맞추기 위한 뷰별 fitting은 하지 않는다.
선택한 형상이 고정 화면의 10px 여백 안에 들어오지 않으면 실패한다. 이 경우 사용자가
중심점 또는 축척을 명시적으로 조정한다. 전후 비교에서는 같은 인자를 재사용한다.

출력 폴더는 새 경로여야 하며 기존 결과를 덮어쓰지 않는다. 실패한 부분 출력도 보존하고
`failure.json`을 남긴다. 성공하면 다음 파일을 생성한다.

- `snapshot.json`, `parts.json`, `render-config.json`: 같은 형상을 재사용하기 위한 입력과 고정 설정.
- `front/side/top.png`: 실제 Blender orthographic render, 파츠별 schematic 색상, 투명 배경.
- `front/side/top.svg`: PNG를 내부에 포함한 편집 가능한 도면. 전체 모델의 투영 AABB 폭·높이 치수,
  world 원점 기준선(화면 안에 있을 때), 축 이름, 파츠 번호와 ID를 표시한다.
- `sheet.svg`: 동일 축척의 세 도면을 나란히 배치한 자체 포함 검토 시트.
- `manifest.json`: 원본 `.blend`와 parts 파일 SHA-256, snapshot·render·SVG hash, Blender 버전,
  원본 frame, camera 위치·target·ortho scale, 해상도·물리 축척·renderer 설정·한계.

치수는 모델에서 측정한 전체 bounds이며 승인 설계의 요구 치수가 아니다. 파츠 번호 위치도
각 파츠 bbox 중심을 투영한 안내 위치다. 숨은 선·단면·내부 치수·제조 공차는 생성하지 않는다.
색은 파츠 구분용이며 원본 재질을 재현하지 않는다. Geometry Nodes instance, rig/animation과
비-mesh 변환의 지원 범위는 snapshot exporter의 한계를 따른다. 현재 frame의 evaluated mesh만 사용한다.

생성 성공은 도면 출력과 출처 연결의 성공이다. 실제 자산의 설계 적합성이나 인간 승인은 별도다.
QA 자료로 사용할 때는 파일을 run assets에 등록하고 원본·후보·참조와의 정합 및 남은 불확실성을
검토해야 한다. SRG 승인이나 단계 전환을 자동 생성하지 않는다.

검증은 비대칭 합성 모델로 실제 PNG alpha bounds와 투영 치수의 일치, 동일 설정 재실행 PNG hash,
원본 보존과 덮어쓰기 거부를 확인한다. Linux headless Workbench는 Xvfb와 software OpenGL을 사용한다.
