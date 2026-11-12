using System;
using TinyTracks.Trains;
using TinyTracks.World;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace TinyTracks.Performance
{
    public enum QualityPreset { Low = 0, Medium = 1, High = 2 }

    /// <summary>
    /// Graphics presets. Low (default on 32-bit / low-memory phones such as the Redmi A3): no realtime shadows,
    /// 0.8 render scale, no MSAA, fewer optional props and ambient animations, 30 FPS cap. Medium/High add shadows,
    /// MSAA and full dressing. A light governor drops render scale if the average frame rate stays low.
    /// </summary>
    public class PerformanceManager : MonoBehaviour
    {
        public static PerformanceManager Instance { get; private set; }

        public QualityPreset Current { get; private set; } = QualityPreset.Medium;
        public float AverageFps { get; private set; } = 30f;
        public event Action<QualityPreset> Changed;

        private float fpsTimer;
        private int frames;
        private float lowTime;
        private bool governed;

        private void Awake() => Instance = this;

        public static QualityPreset AutoDetect()
        {
            bool is32 = IntPtr.Size == 4;
            int mem = SystemInfo.systemMemorySize;
            if (Application.isMobilePlatform && (is32 || mem < 4500 || SystemInfo.processorCount <= 4)) return QualityPreset.Low;
            if (Application.isMobilePlatform && mem < 7000) return QualityPreset.Medium;
            return Application.isMobilePlatform ? QualityPreset.High : QualityPreset.High;
        }

        public void Apply(QualityPreset p)
        {
            Current = p;
            governed = false;
            var urp = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
            if (urp != null)
            {
                urp.renderScale = p == QualityPreset.Low ? 0.8f : (p == QualityPreset.Medium ? 0.9f : 1f);
                urp.msaaSampleCount = p == QualityPreset.Low ? 1 : (p == QualityPreset.Medium ? 2 : 4);
                urp.shadowDistance = p == QualityPreset.Low ? 0f : (p == QualityPreset.Medium ? 35f : 55f);
            }
            Light sun = RenderSettings.sun;
            if (sun == null) foreach (Light l in FindObjectsByType<Light>(FindObjectsSortMode.None)) if (l.type == LightType.Directional) { sun = l; break; }
            if (sun != null)
            {
                sun.shadows = p == QualityPreset.Low ? LightShadows.None : (p == QualityPreset.Medium ? LightShadows.Hard : LightShadows.Soft);
                sun.shadowStrength = 0.6f;
            }
            Application.targetFrameRate = p == QualityPreset.Low ? 30 : 60;
            QualitySettings.vSyncCount = 0;
            AmbientAnimator.LowDetail = p == QualityPreset.Low;
            WorldManager.Instance?.SetLowDetail(p == QualityPreset.Low);
            FindAnyObjectByType<TrainEffects>()?.SetLowDetail(p == QualityPreset.Low);
            Debug.Log($"[TT Perf] preset={p} 32bit={IntPtr.Size == 4} mem={SystemInfo.systemMemorySize}MB gpu={SystemInfo.graphicsDeviceName} api={SystemInfo.graphicsDeviceType}");
            Changed?.Invoke(p);
        }

        private void Update()
        {
            frames++;
            fpsTimer += Time.unscaledDeltaTime;
            if (fpsTimer < 2f) return;
            AverageFps = frames / fpsTimer;
            frames = 0;
            fpsTimer = 0f;
            float floor = Current == QualityPreset.Low ? 24f : 40f;
            lowTime = AverageFps < floor ? lowTime + 2f : 0f;
            if (lowTime >= 8f && !governed)
            {
                governed = true;
                var urp = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
                if (urp != null) urp.renderScale = Mathf.Max(0.65f, urp.renderScale - 0.15f);
                if (Current != QualityPreset.Low)
                {
                    Light sun = RenderSettings.sun;
                    if (sun != null) sun.shadows = LightShadows.None;
                }
                Debug.Log($"[TT Perf] governor: fps={AverageFps:0.0} -> render scale lowered");
            }
        }
    }
}
