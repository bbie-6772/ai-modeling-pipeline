using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

public static class PipelineEditorImport {
    static string Argument(string key) {
        var values=Environment.GetCommandLineArgs();
        int index=Array.IndexOf(values,key);
        if(index<0 || index+1>=values.Length)throw new ArgumentException("Missing "+key);
        return values[index+1];
    }
    public static void Run() {
        if(!Application.isBatchMode)throw new InvalidOperationException("Isolated batch project required");
        string input=Argument("-pipelineInput"), output=Argument("-pipelineReport");
        var data=JsonUtility.FromJson<PipelineHandoff>(File.ReadAllText(input));
        if(data.kind!="unity-static-mesh-v1" || data.units!="m")throw new ArgumentException("Invalid handoff");
        if(Directory.Exists("Assets/PipelineOutput"))throw new IOException("Existing output refused");
        AssetDatabase.CreateFolder("Assets","PipelineOutput");
        var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
        var root=new GameObject("PipelineCandidate");
        var shader=Shader.Find("Standard");
        if(shader==null)throw new InvalidOperationException("Diagnostic shader unavailable");
        var material=new Material(shader){name="PipelineDiagnostic"};
        AssetDatabase.CreateAsset(material,"Assets/PipelineOutput/Diagnostic.mat");
        int triangles=0;
        for(int i=0;i<data.parts.Length;i++) {
            var part=data.parts[i];
            var mesh=new Mesh {name=part.name,indexFormat=IndexFormat.UInt32};
            mesh.vertices=part.vertices; mesh.triangles=part.triangles;
            mesh.RecalculateNormals();mesh.RecalculateBounds();
            AssetDatabase.CreateAsset(mesh,$"Assets/PipelineOutput/Mesh{i}.asset");
            var obj=new GameObject(part.name);obj.transform.SetParent(root.transform,false);
            obj.AddComponent<MeshFilter>().sharedMesh=mesh;
            obj.AddComponent<MeshRenderer>().sharedMaterial=material;
            if(data.collision=="box") {
                if(mesh.bounds.size.x<=0 || mesh.bounds.size.y<=0 || mesh.bounds.size.z<=0)
                    throw new ArgumentException("Box proxy requires volume");
                var collider=obj.AddComponent<BoxCollider>();collider.center=mesh.bounds.center;collider.size=mesh.bounds.size;
            }
            triangles+=mesh.triangles.Length/3;
        }
        PrefabUtility.SaveAsPrefabAsset(root,"Assets/PipelineOutput/Candidate.prefab");
        var report=new PipelineReport {version=Application.unityVersion,
            candidate_sha256=data.source_sha256,import_ok=true,test_scene="Assets/PipelineOutput/Smoke.unity"};
        report.measurements.triangles=triangles;report.measurements.materials=1;report.measurements.texture_mib=0;
        var probe=root.AddComponent<PipelineRuntimeProbe>();
        probe.inputPath=input;probe.reportPath=output;probe.initialReport=JsonUtility.ToJson(report);
        EditorSceneManager.SaveScene(scene,report.test_scene);AssetDatabase.SaveAssets();
        EditorApplication.isPlaying=true;
    }
}
