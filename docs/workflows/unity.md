# 정적 mesh의 Unity 인계와 Play Mode smoke

실제 Blender evaluated triangle indices가 있는 최신 snapshot을 사용한다. 원본 파일의 SHA-256과
snapshot을 대조하고, physical scene scale을 반영해 meter로 바꾼다. Blender Z-up right-handed →
Unity Y-up left-handed `(x,z,y)` 변환에 맞춰 triangle winding도 뒤집는다. concave n-gon을 임의
fan triangulation하지 않으며 exporter가 내보낸 실제 loop triangle만 사용한다.

```console
python -m asset_pipeline.unity --snapshot unity-snapshot.json --candidate model.blend --unity "C:/Program Files/Unity/Hub/Editor/6000.3.25f1/Editor/Unity.exe" --output runs/unity-01 --collision box
```

output은 새 폴더만 허용한다. 기존 Unity 프로젝트는 열거나 변경하지 않는다. 설치된 Unity와
유효한 사용자 라이선스가 필요하며 코드가 설치·로그인·라이선스 동의를 자동 수행하지 않는다.
Unity가 제공하는 `-batchmode`, `-nographics`, `-createProject`, `-executeMethod`를 사용한다.
첫 process에서 새 프로젝트를 만들고, 두 번째에서 C# importer로 Mesh asset·diagnostic material·
Prefab·test scene을 만든 뒤 실제 Play Mode 35 frame을 실행한다. CLI 각 process timeout은 300초다.

`handoff.json`은 정적 geometry 전용 형식이다. 원본 UV·rig·animation·재질·텍스처를 이식하지 않는다.
진단용 단색 material 1개를 만든다. collision은 명시적으로 none 또는 bounds 기반 box proxy를 선택한다.
box 통과는 실제 shape에 맞는 collision 검증이 아니다. FBX/glTF exporter도 이 단계에 포함하지 않는다.

실제 런타임 mesh 수·bounds·요청한 collision raycast, triangle/material 수를 검사한다.
`engine-report.json`은 원본·snapshot·handoff hash, Unity 버전, 실제 test scene과 import/runtime smoke
결과를 기록한다. Editor headless frame 간 시간은 `editor_smoke_frame_ms` 진단값으로만 남긴다.
`runtime_budget_verified=false`, `measurements.frame_ms=null`, I02=UNKNOWN이다. 새 report를
기존 코어의 target-runtime budget 통과 근거로 사용하면 차단한다. 실기기/게임 scene의 성능·재질·
rig·UV·LOD·최종 승인은 별도로 검증해야 한다. 실패 시 log와 후보 프로젝트를 남기며 성공으로 바꾸지 않는다.

공식 API: [command line](https://docs.unity3d.com/6000.0/Documentation/Manual/EditorCommandLineArguments.html),
[EditorApplication.isPlaying](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/EditorApplication-isPlaying.html).
