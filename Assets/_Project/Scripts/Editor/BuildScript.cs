using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace TinyTracks.EditorTools
{
    /// <summary>
    /// Player builds. Every Android build re-applies the mandatory settings (IL2CPP, ARMv7 + ARM64, GLES3).
    /// Batch: Tools/build_android.sh [release|armv7|arm64|all], Tools/build_linux.sh
    /// </summary>
    public static class BuildScript
    {
        public const string Dir = "Builds/Android";

        private static string[] Scenes => EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray();

        [MenuItem("Tiny Tracks/Build Android (development, both ABIs)")]
        public static void AndroidDev() => Build(AndroidArchitecture.ARMv7 | AndroidArchitecture.ARM64, true, "TinyTracksWorld-dev.apk");

        public static void AndroidDevBatch() => Exit(Build(AndroidArchitecture.ARMv7 | AndroidArchitecture.ARM64, true, "TinyTracksWorld-dev.apk"));
        public static void AndroidReleaseBatch() => Exit(Build(AndroidArchitecture.ARMv7 | AndroidArchitecture.ARM64, false, "TinyTracksWorld-universal.apk"));

        /// <summary>Release set: universal (both ABIs), ARMv7-only and ARM64-only APKs.</summary>
        public static void AndroidAllBatch()
        {
            bool ok = Ok(Build(AndroidArchitecture.ARMv7 | AndroidArchitecture.ARM64, false, "TinyTracksWorld-universal.apk"))
                      && Ok(Build(AndroidArchitecture.ARMv7, false, "TinyTracksWorld-armv7.apk"))
                      && Ok(Build(AndroidArchitecture.ARM64, false, "TinyTracksWorld-arm64.apk"));
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARMv7 | AndroidArchitecture.ARM64;
            AssetDatabase.SaveAssets();
            EditorApplication.Exit(ok ? 0 : 1);
        }

        public static BuildReport Build(AndroidArchitecture arch, bool development, string file)
        {
            ProjectSetup.ConfigurePlayer();
            PlayerSettings.Android.targetArchitectures = arch;
            EditorUserBuildSettings.buildAppBundle = false;
            Directory.CreateDirectory(Dir);
            BuildReport report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = Scenes,
                locationPathName = Path.Combine(Dir, file),
                target = BuildTarget.Android,
                targetGroup = BuildTargetGroup.Android,
                options = development ? BuildOptions.Development : BuildOptions.None,
            });
            Log(report);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARMv7 | AndroidArchitecture.ARM64;
            return report;
        }

        public static void LinuxBatch()
        {
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, ScriptingImplementation.Mono2x);
            Directory.CreateDirectory("Builds/Linux");
            BuildReport r = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = Scenes, locationPathName = "Builds/Linux/TinyTracksWorld.x86_64",
                target = BuildTarget.StandaloneLinux64, targetGroup = BuildTargetGroup.Standalone, options = BuildOptions.None,
            });
            Log(r);
            Exit(r);
        }

        private static bool Ok(BuildReport r) => r.summary.result == BuildResult.Succeeded;
        private static void Exit(BuildReport r) => EditorApplication.Exit(Ok(r) ? 0 : 1);

        private static void Log(BuildReport report)
        {
            BuildSummary s = report.summary;
            Debug.Log($"[TT Build] {s.platform} result={s.result} size={s.totalSize / (1024f * 1024f):0.0} MB time={s.totalTime.TotalSeconds:0}s " +
                      $"errors={s.totalErrors} output={s.outputPath} archs={PlayerSettings.Android.targetArchitectures}");
            foreach (BuildStep step in report.steps)
            foreach (BuildStepMessage m in step.messages)
                if (m.type == LogType.Error || m.type == LogType.Exception) Debug.LogError("[TT Build] " + m.content);
        }
    }
}
