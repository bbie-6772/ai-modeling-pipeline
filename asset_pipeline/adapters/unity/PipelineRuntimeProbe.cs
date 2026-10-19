using System;
using System.IO;
using System.Diagnostics;
using UnityEngine;

[Serializable] public class PipelinePart { public string name; public Vector3[] vertices; public int[] triangles; }
[Serializable] public class PipelineHandoff {
    public string kind, source_sha256, units, coordinate_space, collision;
    public PipelinePart[] parts; public Vector3 bounds_min, bounds_max;
}
[Serializable] public class PipelineMeasurements { public int triangles, materials; public float texture_mib; }
[Serializable] public class PipelineReport {
    public string engine="Unity", version, test_scene, candidate_sha256;
    public bool import_ok, runtime_ok, collision_ok, bounds_ok;
    public int play_mode_frames;
    public double editor_smoke_frame_ms;
    public PipelineMeasurements measurements=new PipelineMeasurements();
}

public class PipelineRuntimeProbe : MonoBehaviour {
    public string inputPath, reportPath, initialReport;
    private PipelineHandoff data; private PipelineReport report;
    private int frames; private long previous; private double elapsed;
    void Start() {
        if(!Application.isBatchMode) { enabled=false; return; }
        data=JsonUtility.FromJson<PipelineHandoff>(File.ReadAllText(inputPath));
        report=JsonUtility.FromJson<PipelineReport>(initialReport);
        previous=Stopwatch.GetTimestamp();
    }
    void Update() {
        long now=Stopwatch.GetTimestamp();
        if (frames>=5) elapsed+=(now-previous)*1000.0/Stopwatch.Frequency;
        previous=now; frames++;
        if(frames<35)return;
        var renderers=GetComponentsInChildren<MeshRenderer>();
        if(renderers.Length==0)throw new InvalidOperationException("Runtime mesh missing");
        Bounds bounds=renderers[0].bounds;
        foreach(var renderer in renderers)bounds.Encapsulate(renderer.bounds);
        report.bounds_ok=(bounds.min-data.bounds_min).magnitude<0.0001f && (bounds.max-data.bounds_max).magnitude<0.0001f;
        Physics.SyncTransforms();
        report.collision_ok=data.collision=="none" || Physics.Raycast(bounds.center+Vector3.up*(bounds.extents.y+1),Vector3.down,bounds.size.y+2);
        report.runtime_ok=report.bounds_ok && report.collision_ok && renderers.Length==data.parts.Length;
        report.play_mode_frames=frames;
        report.editor_smoke_frame_ms=elapsed/30;
        File.WriteAllText(reportPath,JsonUtility.ToJson(report,true));
#if UNITY_EDITOR
        UnityEditor.EditorApplication.Exit(report.runtime_ok?0:2);
#endif
    }
}
