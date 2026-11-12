using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using TinyTracks.Audio;
using TinyTracks.Building;
using TinyTracks.Cameras;
using TinyTracks.Core;
using TinyTracks.Decorations;
using TinyTracks.Inputs;
using TinyTracks.Interaction;
using TinyTracks.Performance;
using TinyTracks.SaveSystem;
using TinyTracks.Tracks;
using TinyTracks.Trains;
using TinyTracks.UI;
using TinyTracks.World;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace TinyTracks.EditorTools
{
    /// <summary>
    /// Generates everything Unity-side from the Blender output and code: project/Android settings, URP, materials,
    /// prefabs, ScriptableObject definitions, content library, world layout and the main scene. Re-runnable.
    /// Batch: Tools/setup.sh  (menu: Tiny Tracks ▸ Setup Project)
    /// </summary>
    public static class ProjectSetup
    {
        public const string Root = "Assets/_Project";
        public const string Models = Root + "/Art/Models";
        public const string Prefabs = Root + "/Prefabs";
        public const string Defs = Root + "/ScriptableObjects";
        public const string Mats = Root + "/Materials";
        public const string SettingsDir = Root + "/Settings";
        public const string ScenePath = Root + "/Scenes/Main.unity";
        public const string AppId = "com.nocvault.tinytracksworld";
        public const string Version = "0.2.1";
        public const int VersionCode = 3;

        [MenuItem("Tiny Tracks/Setup Project")]
        public static void Run()
        {
            ConfigurePlayer();
            ConfigureRenderPipeline();
            AssetDatabase.Refresh();
            Texture2D detail = BuildDetailTexture();
            Dictionary<string, Material> mats = BuildMaterials(detail);
            var prefabs = BuildPrefabs(mats);
            ContentLibrary lib = BuildContent(prefabs, mats);
            BuildScene(lib, mats);
            AssetDatabase.SaveAssets();
            Resources.UnloadUnusedAssets();
            Validate(AssetDatabase.LoadAssetAtPath<ContentLibrary>(Root + "/Resources/" + ContentLibrary.ResourcePath + ".asset"));
            Debug.Log("[TT Setup] done");
        }

        public static void RunBatch()
        {
            try { Run(); EditorApplication.Exit(0); }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }

        // ------------------------------------------------------------------------------------------------ player
        public static void ConfigurePlayer()
        {
            PlayerSettings.companyName = "Nocvault";
            PlayerSettings.productName = "Tiny Tracks World";
            PlayerSettings.bundleVersion = Version;
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, AppId);
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Standalone, AppId);
            PlayerSettings.Android.bundleVersionCode = Math.Max(VersionCode, PlayerSettings.Android.bundleVersionCode);
            PlayerSettings.defaultInterfaceOrientation = UIOrientation.AutoRotation;
            PlayerSettings.allowedAutorotateToLandscapeLeft = true;
            PlayerSettings.allowedAutorotateToLandscapeRight = true;
            PlayerSettings.allowedAutorotateToPortrait = false;
            PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;

            // MANDATORY: IL2CPP with 32-bit ARMv7 AND ARM64 (the Redmi A3 runs a 32-bit Android).
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARMv7 | AndroidArchitecture.ARM64;
            PlayerSettings.Android.minSdkVersion = (AndroidSdkVersions)25;
            // Target 35 (meets Google Play's current requirement). At 36 Android ignores the edge-to-edge opt-out that
            // Unity's legacy full-screen needs, and the status bar stays visible (seen on a TCL tablet, Android 15).
            PlayerSettings.Android.targetSdkVersion = (AndroidSdkVersions)35;
            PlayerSettings.Android.forceInternetPermission = false;
            PlayerSettings.Android.forceSDCardPermission = false;
            PlayerSettings.Android.renderOutsideSafeArea = false;
            PlayerSettings.SetManagedStrippingLevel(NamedBuildTarget.Android, ManagedStrippingLevel.Low);
            // OpenGL ES 3.0 only: the baseline every target supports; Vulkan is not required (and PowerVR GPUs such as
            // the Redmi A3's GE8320 crashed with Vulkan in this owner's other Unity games).
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.OpenGLES3 });
            PlayerSettings.colorSpace = ColorSpace.Linear;
            PlayerSettings.gpuSkinning = false;
            PlayerSettings.runInBackground = true;
            PlayerSettings.SplashScreen.showUnityLogo = false;
            PlayerSettings.SplashScreen.backgroundColor = new Color32(143, 211, 255, 255);
            PlayerSettings.SetStackTraceLogType(LogType.Log, StackTraceLogType.None);
            EditorUserBuildSettings.buildAppBundle = false;
            PlayerSettings.fullScreenMode = FullScreenMode.FullScreenWindow; // hide the status bar (immersive)
            PlayerSettings.defaultScreenWidth = 1280;
            PlayerSettings.defaultScreenHeight = 720;
            PlayerSettings.resizableWindow = true;
            QualitySettings.vSyncCount = 0;

            // Input System only.
            var ps = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset")[0]);
            SerializedProperty handler = ps.FindProperty("activeInputHandler");
            if (handler != null) { handler.intValue = 1; ps.ApplyModifiedPropertiesWithoutUndo(); }
        }

        // ------------------------------------------------------------------------------------------------ URP
        public static void ConfigureRenderPipeline()
        {
            EnsureFolder(SettingsDir);
            string rendererPath = SettingsDir + "/TT_Renderer.asset";
            string pipePath = SettingsDir + "/TT_URP.asset";
            var renderer = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(rendererPath);
            if (renderer == null)
            {
                renderer = ScriptableObject.CreateInstance<UniversalRendererData>();
                AssetDatabase.CreateAsset(renderer, rendererPath);
            }
            renderer.renderingMode = RenderingMode.Forward;
            renderer.depthPrimingMode = DepthPrimingMode.Disabled;
            EditorUtility.SetDirty(renderer);
            var pipe = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(pipePath);
            if (pipe == null)
            {
                pipe = UniversalRenderPipelineAsset.Create(renderer);
                AssetDatabase.CreateAsset(pipe, pipePath);
            }
            var so = new SerializedObject(pipe);
            void SetI(string n, int v) { SerializedProperty p = so.FindProperty(n); if (p != null) p.intValue = v; }
            void SetF(string n, float v) { SerializedProperty p = so.FindProperty(n); if (p != null) p.floatValue = v; }
            void SetB(string n, bool v) { SerializedProperty p = so.FindProperty(n); if (p != null) p.boolValue = v; }
            SetB("m_SupportsHDR", false);
            SetI("m_MSAA", 2);
            SetF("m_RenderScale", 1f);
            SetB("m_MainLightShadowsSupported", true);
            SetI("m_MainLightShadowmapResolution", 1024);
            SetB("m_SoftShadowsSupported", true);
            SetF("m_ShadowDistance", 40f);
            SetI("m_ShadowCascadeCount", 1);
            SetI("m_AdditionalLightsRenderingMode", 0);
            SetB("m_SupportsCameraDepthTexture", false);
            SetB("m_SupportsCameraOpaqueTexture", false);
            SetB("m_UseSRPBatcher", true);
            SetB("m_SupportsDynamicBatching", false);
            so.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(pipe);
            GraphicsSettings.defaultRenderPipeline = pipe;
            // Every quality level uses the same pipeline; the game's own presets do the rest at runtime.
            string[] names = QualitySettings.names;
            int current = QualitySettings.GetQualityLevel();
            for (int i = 0; i < names.Length; i++)
            {
                QualitySettings.SetQualityLevel(i, false);
                QualitySettings.renderPipeline = pipe;
            }
            QualitySettings.SetQualityLevel(current, false);
            AssetDatabase.SaveAssets();
        }

        // ------------------------------------------------------------------------------------------------ textures/materials
        private static Texture2D BuildDetailTexture()
        {
            string path = Root + "/Art/Textures/T_Detail.png";
            EnsureFolder(Path.GetDirectoryName(path));
            const int n = 256;
            var tex = new Texture2D(n, n, TextureFormat.RGBA32, false);
            var px = new Color32[n * n];
            var rng = new System.Random(7);
            for (int y = 0; y < n; y++)
            for (int x = 0; x < n; x++)
            {
                // R: wood grain - long wavy stripes along V (tileable via sin of whole periods).
                float u = x / (float)n, v = y / (float)n;
                float warp = 0.06f * Mathf.Sin(v * Mathf.PI * 2f * 2f + Mathf.Sin(u * Mathf.PI * 2f * 3f) * 1.2f);
                float g = 0.5f + 0.5f * Mathf.Sin((u + warp) * Mathf.PI * 2f * 9f);
                g = Mathf.Pow(g, 3f);
                float fine = 0.5f + 0.5f * Mathf.Sin((u + warp * 0.5f) * Mathf.PI * 2f * 37f);
                float r = 0.5f + 0.13f * (0.5f - g) * 2f - 0.04f * fine + 0.05f;
                // G: soft speckle noise (tileable perlin via periodic coords).
                float nz = 0f, amp = 1f, tot = 0f;
                for (int o = 0; o < 4; o++)
                {
                    float f = 4f * (1 << o);
                    nz += amp * Periodic(u * f, v * f, f);
                    tot += amp;
                    amp *= 0.5f;
                }
                nz /= tot;
                float gg = 0.5f + (nz - 0.5f) * 0.55f + (float)(rng.NextDouble() - 0.5) * 0.05f;
                px[y * n + x] = new Color(Mathf.Clamp01(r), Mathf.Clamp01(gg), 0.5f, 1f);
            }
            tex.SetPixels32(px);
            tex.Apply();
            File.WriteAllBytes(path, tex.EncodeToPNG());
            AssetDatabase.ImportAsset(path);
            var ti = (TextureImporter)AssetImporter.GetAtPath(path);
            ti.sRGBTexture = false;
            ti.wrapMode = TextureWrapMode.Repeat;
            ti.mipmapEnabled = true;
            ti.maxTextureSize = 256;
            ti.textureCompression = TextureImporterCompression.Compressed;
            ti.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        private static float Periodic(float x, float y, float period)
        {
            // Bilinear blend of four Perlin samples so the noise tiles with the given period.
            float fx = x / period, fy = y / period;
            float a = Mathf.PerlinNoise(x, y), b = Mathf.PerlinNoise(x - period, y);
            float c = Mathf.PerlinNoise(x, y - period), d = Mathf.PerlinNoise(x - period, y - period);
            return Mathf.Lerp(Mathf.Lerp(a, b, fx), Mathf.Lerp(c, d, fx), fy);
        }

        private static Material Mat(string name, string shader, Action<Material> setup)
        {
            EnsureFolder(Mats);
            string path = $"{Mats}/{name}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            Shader s = Shader.Find(shader);
            if (s == null) throw new Exception("Shader not found: " + shader);
            if (m == null) { m = new Material(s); AssetDatabase.CreateAsset(m, path); }
            m.shader = s;
            setup?.Invoke(m);
            m.enableInstancing = false;
            EditorUtility.SetDirty(m);
            return m;
        }

        private static Dictionary<string, Material> BuildMaterials(Texture2D detail)
        {
            var d = new Dictionary<string, Material>
            {
                ["toy"] = Mat("M_ToyLit", "TinyTracks/ToyLit", m => { m.SetTexture("_DetailTex", detail); m.SetFloat("_DetailScale", 1f); }),
                ["ghost"] = Mat("M_Ghost", "TinyTracks/Ghost", null),
                ["blob"] = Mat("M_BlobShadow", "TinyTracks/Blob", m => { m.SetColor("_BaseColor", new Color(0.1f, 0.15f, 0.1f, 0.35f)); m.SetFloat("_Softness", 0.7f); }),
                ["marker"] = Mat("M_OpenEnd", "TinyTracks/Blob", m =>
                {
                    m.SetColor("_BaseColor", new Color(0.3f, 0.95f, 0.45f, 0.75f)); m.SetFloat("_Softness", 0.25f); m.SetFloat("_Ring", 0.55f); m.SetFloat("_Pulse", 1f);
                }),
                ["water"] = Mat("M_Water", "TinyTracks/Water", null),
                ["sky"] = Mat("M_Sky", "TinyTracks/SkyGradient", null),
            };
            AssetDatabase.SaveAssets();
            return d;
        }

        // ------------------------------------------------------------------------------------------------ prefabs
        private static readonly string[] Groups = { "Tracks", "Trains", "Animals", "People", "Nature", "Buildings", "Props" };

        private static Dictionary<string, GameObject> BuildPrefabs(Dictionary<string, Material> mats)
        {
            var result = new Dictionary<string, GameObject>();
            foreach (string g in Groups)
            {
                string dir = $"{Models}/{g}";
                if (!AssetDatabase.IsValidFolder(dir)) continue;
                EnsureFolder($"{Prefabs}/{g}");
                foreach (string guid in AssetDatabase.FindAssets("t:Model", new[] { dir }))
                {
                    string path = AssetDatabase.GUIDToAssetPath(guid);
                    if (!path.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase)) continue;
                    string name = Path.GetFileNameWithoutExtension(path);
                    var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                    var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
                    PrefabUtility.UnpackPrefabInstance(inst, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
                    inst.name = name;
                    foreach (Renderer r in inst.GetComponentsInChildren<Renderer>(true))
                    {
                        var arr = new Material[Mathf.Max(1, r.sharedMaterials.Length)];
                        for (int i = 0; i < arr.Length; i++) arr[i] = mats["toy"];
                        r.sharedMaterials = arr;
                        bool big = g == "Buildings" || g == "Nature" || g == "Trains" || g == "Animals" || g == "People" || g == "Props";
                        r.shadowCastingMode = big && !name.StartsWith("Cloud") && !name.StartsWith("Grass") && !name.StartsWith("Flowers")
                            ? ShadowCastingMode.On : ShadowCastingMode.Off;
                        r.lightProbeUsage = LightProbeUsage.Off;
                        r.reflectionProbeUsage = ReflectionProbeUsage.Off;
                    }
                    if (g != "Tracks" && g != "Trains") AddColliderAndBehaviour(inst, g, name);
                    if (g == "Trains" || g == "Animals" || g == "People") AddBlob(inst, mats["blob"], g == "Trains" ? 1.1f : 0.8f);
                    string pp = $"{Prefabs}/{g}/{name}.prefab";
                    result[g + "/" + name] = PrefabUtility.SaveAsPrefabAsset(inst, pp);
                    UnityEngine.Object.DestroyImmediate(inst);
                }
            }
            // Level crossing: two barriers either side of the road.
            if (result.TryGetValue("Props/Barrier_Crossing", out GameObject barrier))
            {
                var pair = new GameObject("CrossingBarriers");
                var a = (GameObject)PrefabUtility.InstantiatePrefab(barrier, pair.transform);
                a.transform.localPosition = new Vector3(1.0f, 0f, -1.5f);
                a.transform.localRotation = Quaternion.Euler(0f, 90f, 0f);
                var b = (GameObject)PrefabUtility.InstantiatePrefab(barrier, pair.transform);
                b.transform.localPosition = new Vector3(-1.0f, 0f, 1.5f);
                b.transform.localRotation = Quaternion.Euler(0f, -90f, 0f);
                foreach (Collider c in pair.GetComponentsInChildren<Collider>()) UnityEngine.Object.DestroyImmediate(c);
                foreach (Interactable it in pair.GetComponentsInChildren<Interactable>()) UnityEngine.Object.DestroyImmediate(it);
                pair.AddComponent<CrossingBarrier>();
                result["Props/CrossingBarriers"] = PrefabUtility.SaveAsPrefabAsset(pair, $"{Prefabs}/Props/CrossingBarriers.prefab");
                UnityEngine.Object.DestroyImmediate(pair);
            }
            AssetDatabase.SaveAssets();
            return result;
        }

        private static void AddBlob(GameObject go, Material blob, float scale)
        {
            Bounds b = Bounds(go);
            var s = new GameObject("BlobShadow");
            s.transform.SetParent(go.transform, false);
            s.transform.localPosition = new Vector3(b.center.x - go.transform.position.x, 0.03f, b.center.z - go.transform.position.z);
            s.transform.localScale = new Vector3(b.size.x * 1.3f * scale, 1f, b.size.z * 1.15f * scale);
            s.AddComponent<MeshFilter>().sharedMesh = GroundQuadAsset();
            var mr = s.AddComponent<MeshRenderer>();
            mr.sharedMaterial = blob;
            mr.shadowCastingMode = ShadowCastingMode.Off;
            mr.receiveShadows = false;
        }

        private static Mesh GroundQuadAsset()
        {
            string path = Root + "/Art/Models/GroundQuad.asset";
            var m = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (m != null) return m;
            m = UnityEngine.Object.Instantiate(MeshFactory.GroundQuad());
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        private static Bounds Bounds(GameObject go)
        {
            var rs = go.GetComponentsInChildren<Renderer>(true);
            if (rs.Length == 0) return new Bounds(go.transform.position, Vector3.one);
            Bounds b = rs[0].bounds;
            foreach (Renderer r in rs) if (!r.name.StartsWith("BlobShadow")) b.Encapsulate(r.bounds);
            return b;
        }

        private static void AddColliderAndBehaviour(GameObject go, string group, string name)
        {
            if (name == "Pillar" || name.StartsWith("Cloud")) return;
            Bounds b = Bounds(go);
            var bc = go.AddComponent<BoxCollider>();
            bc.center = b.center - go.transform.position;
            bc.size = Vector3.Max(b.size, new Vector3(0.6f, 0.6f, 0.6f));
            var it = go.AddComponent<Interactable>();
            it.reaction = ReactionFor(group, name);
        }

        private static TapReaction ReactionFor(string group, string name)
        {
            if (name == "Bird") return TapReaction.Bird;
            if (group == "Animals") return TapReaction.Animal;
            if (group == "People") return TapReaction.Person;
            if (name.StartsWith("Tree") || name == "Bush") return TapReaction.Tree;
            if (name == "Windmill") return TapReaction.Windmill;
            if (name == "Station") return TapReaction.Station;
            if (group == "Buildings") return TapReaction.House;
            return TapReaction.Wobble;
        }

        // ------------------------------------------------------------------------------------------------ content
        private static T Asset<T>(string path) where T : ScriptableObject
        {
            EnsureFolder(Path.GetDirectoryName(path).Replace('\\', '/'));
            var a = AssetDatabase.LoadAssetAtPath<T>(path);
            if (a == null) { a = ScriptableObject.CreateInstance<T>(); AssetDatabase.CreateAsset(a, path); }
            return a;
        }

        private static Sprite Sprite(string path) => AssetDatabase.LoadAssetAtPath<Sprite>(path);

        private static ContentLibrary BuildContent(Dictionary<string, GameObject> prefabs, Dictionary<string, Material> mats)
        {
            var lib = Asset<ContentLibrary>(Root + "/Resources/" + ContentLibrary.ResourcePath + ".asset");
            lib.toyMaterial = mats["toy"];
            lib.ghostMaterial = mats["ghost"];
            lib.blobMaterial = mats["blob"];
            lib.markerMaterial = mats["marker"];
            lib.waterMaterial = mats["water"];
            prefabs.TryGetValue("Props/Pillar", out lib.pillarPrefab);
            lib.quadMesh = GroundQuadAsset();

            // Tracks
            lib.tracks.Clear();
            foreach (TrackType t in TrackShapeLibrary.AllTypes)
            {
                var d = Asset<TrackPieceDefinition>($"{Defs}/TrackDefinitions/Track_{t}.asset");
                d.type = t;
                d.displayName = Nice(t.ToString());
                d.category = CategoryOf(t);
                prefabs.TryGetValue("Tracks/" + t, out d.prefab);
                d.icon = Sprite($"{Root}/Art/UI/Thumbs/Track_{t}.png");
                d.accessory = null;
                d.accessoryOffset = Vector3.zero;
                d.accessoryYaw = 0f;
                if (t == TrackType.Station && prefabs.TryGetValue("Buildings/Station", out GameObject st))
                { d.accessory = st; d.accessoryOffset = new Vector3(0f, 0f, TrackShapeLibrary.StationLength / 2f); }
                if (t == TrackType.Depot && prefabs.TryGetValue("Buildings/Depot", out GameObject dp))
                { d.accessory = dp; d.accessoryOffset = new Vector3(0f, 0f, 2.1f); d.accessoryYaw = 180f; }
                if (t == TrackType.Crossing && prefabs.TryGetValue("Props/CrossingBarriers", out GameObject cb))
                { d.accessory = cb; d.accessoryOffset = new Vector3(0f, 0f, TrackShapeLibrary.StraightLength / 2f); }
                EditorUtility.SetDirty(d);
                lib.tracks.Add(d);
            }

            // Trains (from the Blender manifest + empties measured on the prefab)
            lib.trains.Clear();
            var trainColours = new Dictionary<string, Color>
            {
                ["Loco_RedExpress"] = new Color32(242, 71, 75, 255), ["Loco_BlueAdventure"] = new Color32(46, 139, 230, 255),
                ["Loco_GreenExplorer"] = new Color32(61, 186, 90, 255), ["Loco_YellowSunshine"] = new Color32(255, 204, 46, 255),
            };
            foreach (Manifest.Item m in Manifest.Read("trains_manifest.json"))
            {
                if (!prefabs.TryGetValue("Trains/" + m.name, out GameObject pf)) continue;
                var d = Asset<TrainDefinition>($"{Defs}/TrainDefinitions/{m.name}.asset");
                d.id = m.name;
                d.displayName = string.IsNullOrEmpty(m.displayName) ? Nice(m.name) : m.displayName;
                d.kind = m.kind == "loco" ? VehicleKind.Locomotive : VehicleKind.Carriage;
                d.engine = m.name.Contains("Green") ? EngineSound.Motor : EngineSound.Steam;
                d.prefab = pf;
                d.icon = Sprite($"{Root}/Art/UI/Thumbs/{m.name}.png");
                d.uiColor = trainColours.TryGetValue(m.name, out Color c) ? c : new Color32(200, 220, 255, 255);
                MeasureVehicle(pf, d);
                EditorUtility.SetDirty(d);
                lib.trains.Add(d);
            }
            lib.trains = lib.trains.OrderBy(t => t.kind).ThenBy(t => Array.IndexOf(new[] { "Loco_RedExpress", "Loco_BlueAdventure", "Loco_GreenExplorer", "Loco_YellowSunshine" }, t.id)).ToList();

            // Audio
            AudioConfig audio = Asset<AudioConfig>($"{Defs}/AudioConfig.asset");
            AudioClip A(string folder, string n) => AssetDatabase.LoadAssetAtPath<AudioClip>($"{Root}/Audio/{folder}/{n}.wav");
            audio.music = A("Music", "music_loop");
            audio.ambience = A("Ambient", "countryside_loop");
            audio.whistle = A("SFX", "whistle"); audio.bell = A("SFX", "bell"); audio.chugLoop = A("SFX", "chug_loop");
            audio.rollingLoop = A("SFX", "rolling_loop"); audio.motorLoop = A("SFX", "motor_loop");
            audio.trackPlace = A("SFX", "track_place"); audio.trackSnap = A("SFX", "track_snap"); audio.trackRemove = A("SFX", "track_remove");
            audio.invalid = A("SFX", "invalid"); audio.button = A("SFX", "button"); audio.buttonToggle = A("SFX", "button_toggle");
            audio.undo = A("SFX", "undo"); audio.placeDecor = A("SFX", "place_decor"); audio.stationChime = A("SFX", "station_chime");
            audio.crossingBell = A("SFX", "crossing_bell"); audio.puff = A("SFX", "puff"); audio.tada = A("SFX", "tada");
            audio.switchFlip = A("SFX", "switch_flip");
            audio.moo = A("SFX", "moo"); audio.baa = A("SFX", "baa"); audio.cluck = A("SFX", "cluck"); audio.bark = A("SFX", "bark");
            audio.meow = A("SFX", "meow"); audio.neigh = A("SFX", "neigh"); audio.tweet = A("SFX", "tweet");
            EditorUtility.SetDirty(audio);
            lib.audio = audio;

            // Decorations (creatures + environment manifests)
            lib.decorations.Clear();
            var sounds = new Dictionary<string, AudioClip>
            {
                ["moo"] = audio.moo, ["baa"] = audio.baa, ["cluck"] = audio.cluck, ["bark"] = audio.bark, ["meow"] = audio.meow,
                ["neigh"] = audio.neigh, ["tweet"] = audio.tweet,
            };
            foreach (Manifest.Item m in Manifest.Read("creatures_manifest.json").Concat(Manifest.Read("env_manifest.json")))
            {
                string group = GroupOf(m.fbx);
                if (!prefabs.TryGetValue(group + "/" + m.name, out GameObject pf)) continue;
                if (m.name == "Pillar" || m.name == "Barrier_Crossing" || m.name == "Depot") continue;
                var d = Asset<DecorationDefinition>($"{Defs}/DecorationDefinitions/{m.name}.asset");
                d.id = m.name;
                d.displayName = Nice(m.name);
                d.category = DecoCategory(group, m);
                d.prefab = pf;
                d.icon = Sprite($"{Root}/Art/UI/Thumbs/{m.name}.png");
                Bounds b = PrefabBounds(pf);
                d.footprintRadius = Mathf.Clamp(Mathf.Max(b.extents.x, b.extents.z) * 0.85f, 0.25f, 3.5f);
                d.height = b.size.y;
                d.reaction = ReactionFor(group, m.name);
                d.sound = m.sound != null && sounds.TryGetValue(m.sound, out AudioClip clip) ? clip : null;
                d.placeable = !(m.name.StartsWith("Cloud") || m.name == "Bird");
                d.lowDetailOptional = m.name.StartsWith("Grass") || m.name.StartsWith("Flowers") || m.name.StartsWith("Rock_Small") || m.name == "Mushroom";
                EditorUtility.SetDirty(d);
                lib.decorations.Add(d);
                Interactable it = pf.GetComponent<Interactable>();
                if (it != null && d.sound != null) { it.sound = d.sound; EditorUtility.SetDirty(pf); }
            }

            // World
            WorldDefinition world = Asset<WorldDefinition>($"{Defs}/WorldDefinitions/SunnyValley.asset");
            world.props = WorldLayout.SunnyValley(lib);
            EditorUtility.SetDirty(world);
            lib.worlds = new List<WorldDefinition> { world };

            // Icons
            // Narrator lines (Tools/voice/voice_lines.json + generated clips) and the Thai-capable caption font.
            lib.voice.Clear();
            foreach (VoiceLines.Line l in VoiceLines.Read())
            {
                AudioClip V(string lang) => AssetDatabase.LoadAssetAtPath<AudioClip>($"{Root}/Audio/Voice/{lang}/{l.key}.wav");
                lib.voice.Add(new VoiceLine { key = l.key, en = l.en, th = l.th, enClip = V("en"), thClip = V("th") });
            }
            lib.captionFont = AssetDatabase.LoadAssetAtPath<Font>($"{Root}/Art/UI/Fonts/Mitr-Medium.ttf");

            lib.icons.Clear();
            foreach (string guid in AssetDatabase.FindAssets("t:Sprite", new[] { Root + "/Art/UI/Icons" }))
            {
                string p = AssetDatabase.GUIDToAssetPath(guid);
                lib.icons.Add(new NamedSprite { name = Path.GetFileNameWithoutExtension(p), sprite = Sprite(p) });
            }
            EditorUtility.SetDirty(lib);
            AssetDatabase.SaveAssets();
            return lib;
        }

        private static void MeasureVehicle(GameObject prefab, TrainDefinition d)
        {
            Transform Find(string n) => prefab.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == n);
            Transform bf = Find("BogieFront"), br = Find("BogieRear"), cf = Find("CouplerFront"), cr = Find("CouplerRear");
            Bounds b = PrefabBounds(prefab);
            float front = cf != null ? cf.position.z : b.max.z;
            float rear = cr != null ? cr.position.z : b.min.z;
            d.length = Mathf.Max(0.8f, front - rear);
            if (bf != null && br != null)
            {
                d.bogieSpacing = Mathf.Max(0.3f, bf.position.z - br.position.z);
                d.frontOverhang = Mathf.Max(0f, front - bf.position.z);
            }
            else
            {
                d.bogieSpacing = d.length * 0.6f;
                d.frontOverhang = d.length * 0.2f;
            }
        }

        private static Bounds PrefabBounds(GameObject prefab)
        {
            var rs = prefab.GetComponentsInChildren<MeshFilter>(true).Where(f => f.sharedMesh != null && f.name != "BlobShadow").ToArray();
            if (rs.Length == 0) return new Bounds(Vector3.zero, Vector3.one);
            Bounds b = default;
            bool first = true;
            foreach (MeshFilter f in rs)
            {
                Bounds mb = f.sharedMesh.bounds;
                Matrix4x4 m = prefab.transform.worldToLocalMatrix * f.transform.localToWorldMatrix;
                foreach (Vector3 c in Corners(mb))
                {
                    Vector3 p = m.MultiplyPoint3x4(c);
                    if (first) { b = new Bounds(p, Vector3.zero); first = false; }
                    else b.Encapsulate(p);
                }
            }
            return b;
        }

        private static IEnumerable<Vector3> Corners(Bounds b)
        {
            for (int i = 0; i < 8; i++)
                yield return new Vector3(i % 2 == 0 ? b.min.x : b.max.x, (i / 2) % 2 == 0 ? b.min.y : b.max.y, i / 4 == 0 ? b.min.z : b.max.z);
        }

        private static string GroupOf(string fbx)
        {
            if (string.IsNullOrEmpty(fbx)) return "";
            foreach (string g in Groups) if (fbx.Contains("/" + g + "/")) return g;
            return "";
        }

        private static DecorationCategory DecoCategory(string group, Manifest.Item m)
        {
            switch (group)
            {
                case "Animals": return DecorationCategory.Animals;
                case "People": return DecorationCategory.People;
                case "Buildings": return DecorationCategory.Buildings;
                case "Nature": return DecorationCategory.Nature;
                default: return DecorationCategory.Props;
            }
        }

        private static TrackCategory CategoryOf(TrackType t)
        {
            switch (t)
            {
                case TrackType.Straight: case TrackType.ShortStraight: case TrackType.EndPiece: case TrackType.ElevatedStraight: case TrackType.Ramp:
                    return TrackCategory.Straight;
                case TrackType.GentleLeft: case TrackType.GentleRight: case TrackType.TightLeft: case TrackType.TightRight:
                case TrackType.SCurveLeft: case TrackType.SCurveRight:
                    return TrackCategory.Curve;
                case TrackType.JunctionLeft: case TrackType.JunctionRight: case TrackType.JunctionY: case TrackType.Cross:
                    return TrackCategory.Junction;
                case TrackType.WoodenBridge: case TrackType.StoneBridge: case TrackType.Tunnel:
                    return TrackCategory.BridgeTunnel;
                default:
                    return TrackCategory.Station;
            }
        }

        private static string Nice(string s) => System.Text.RegularExpressions.Regex.Replace(s.Replace("_", " ").Replace("Loco ", ""), "([a-z])([A-Z])", "$1 $2");

        // ------------------------------------------------------------------------------------------------ scene
        private static void BuildScene(ContentLibrary lib, Dictionary<string, Material> mats)
        {
            EnsureFolder(Path.GetDirectoryName(ScenePath));
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            var sunGo = new GameObject("Sun");
            Light sun = sunGo.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.intensity = 1.15f;
            sun.shadows = LightShadows.Soft;
            sun.shadowStrength = 0.6f;
            sunGo.transform.rotation = Quaternion.Euler(48f, -35f, 0f);
            RenderSettings.sun = sun;
            RenderSettings.skybox = mats["sky"];

            var camGo = new GameObject("Main Camera") { tag = "MainCamera" };
            Camera cam = camGo.AddComponent<Camera>();
            cam.fieldOfView = 42f;
            cam.nearClipPlane = 0.5f;
            cam.farClipPlane = 260f;
            cam.clearFlags = CameraClearFlags.Skybox;
            camGo.AddComponent<UniversalAdditionalCameraData>().renderPostProcessing = false;
            camGo.AddComponent<AudioListener>();
            CameraController cc = camGo.AddComponent<CameraController>();

            var systems = new GameObject("Systems");
            T Sys<T>(string n) where T : Component { var g = new GameObject(n); g.transform.SetParent(systems.transform, false); return g.AddComponent<T>(); }
            InputManager input = Sys<InputManager>("InputManager");
            AudioManager audioMgr = Sys<AudioManager>("AudioManager");
            audioMgr.config = lib.audio;
            WorldManager world = Sys<WorldManager>("WorldManager");
            world.content = lib;
            world.world = lib.worlds.FirstOrDefault();
            world.sun = sun;
            TrackNetworkManager net = Sys<TrackNetworkManager>("TrackNetworkManager");
            net.content = lib;
            TrackPlacementController place = Sys<TrackPlacementController>("TrackPlacementController");
            place.network = net; place.content = lib; place.cam = cam;
            DecorationManager deco = Sys<DecorationManager>("DecorationManager");
            deco.content = lib;
            DecorationPlacementController dplace = Sys<DecorationPlacementController>("DecorationPlacementController");
            dplace.decorations = deco; dplace.network = net; dplace.content = lib; dplace.cam = cam;
            TrainEffects fx = Sys<TrainEffects>("TrainEffects");
            fx.content = lib;
            TrainManager trains = Sys<TrainManager>("TrainManager");
            trains.content = lib; trains.network = net; trains.effects = fx;
            SaveManager save = Sys<SaveManager>("SaveManager");
            save.network = net; save.decorations = deco; save.trains = trains;
            PerformanceManager perf = Sys<PerformanceManager>("PerformanceManager");
            Sys<AmbientAnimator>("AmbientAnimator");
            GameManager gm = Sys<GameManager>("GameManager");
            gm.content = lib; gm.input = input; gm.cameraController = cc; gm.network = net; gm.placement = place;
            gm.decorations = deco; gm.decoPlacement = dplace; gm.trains = trains; gm.world = world; gm.audioManager = audioMgr;
            gm.save = save; gm.performance = perf;
            UIManager ui = Sys<UIManager>("UI");
            ui.content = lib;
            ui.game = gm;

            // Execution order: input and world first, game manager after the systems it wires.
            SetOrder(typeof(InputManager), -200);
            SetOrder(typeof(WorldManager), -150);
            SetOrder(typeof(TrackNetworkManager), -120);
            SetOrder(typeof(GameManager), -50);

            EditorSceneManager.SaveScene(scene, ScenePath);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
        }

        private static void SetOrder(Type t, int order)
        {
            foreach (MonoScript s in MonoImporter.GetAllRuntimeMonoScripts())
                if (s.GetClass() == t && MonoImporter.GetExecutionOrder(s) != order) MonoImporter.SetExecutionOrder(s, order);
        }

        // ------------------------------------------------------------------------------------------------ validation
        public static void Validate(ContentLibrary lib)
        {
            var problems = new List<string>();
            foreach (TrackPieceDefinition t in lib.tracks)
            {
                if (t.prefab == null) problems.Add("track model missing: " + t.type);
                if (t.icon == null) problems.Add("track icon missing: " + t.type);
            }
            if (lib.Locomotives().Count() < 4) problems.Add("fewer than 4 locomotives");
            foreach (TrainDefinition t in lib.trains) if (t.icon == null) problems.Add("train icon missing: " + t.id);
            foreach (DecorationDefinition d in lib.decorations) if (d.icon == null && d.placeable) problems.Add("decoration icon missing: " + d.id);
            if (lib.audio == null || lib.audio.whistle == null || lib.audio.music == null) problems.Add("audio missing");
            if (lib.pillarPrefab == null) problems.Add("pillar prefab missing");
            if (lib.voice.Count == 0) problems.Add("narrator lines missing");
            foreach (VoiceLine v in lib.voice)
                if (v.enClip == null || v.thClip == null) problems.Add("voice clip missing: " + v.key);
            if (lib.captionFont == null) problems.Add("caption font missing");
            foreach (string icon in new[] { "go", "stop", "whistle", "bell", "undo", "delete", "rotate", "confirm", "home", "play" })
                if (lib.Icon(icon) == null) problems.Add("UI icon missing: " + icon);
            if ((PlayerSettings.Android.targetArchitectures & AndroidArchitecture.ARMv7) == 0) problems.Add("ARMv7 NOT enabled");
            if ((PlayerSettings.Android.targetArchitectures & AndroidArchitecture.ARM64) == 0) problems.Add("ARM64 NOT enabled");
            if (PlayerSettings.GetScriptingBackend(NamedBuildTarget.Android) != ScriptingImplementation.IL2CPP) problems.Add("not IL2CPP");
            Debug.Log($"[TT Validate] tracks={lib.tracks.Count} trains={lib.trains.Count} decorations={lib.decorations.Count} icons={lib.icons.Count} props={lib.worlds.FirstOrDefault()?.props.Count}");
            foreach (string p in problems) Debug.LogWarning("[TT Validate] " + p);
            Debug.Log(problems.Count == 0 ? "[TT Validate] OK" : $"[TT Validate] {problems.Count} problem(s)");
        }

        public static void EnsureFolder(string path)
        {
            path = path.Replace('\\', '/');
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = Path.GetDirectoryName(path).Replace('\\', '/');
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
        }
    }

    /// <summary>Reads the Blender manifests in Tools/blender/models/*.json.</summary>
    /// <summary>Tools/voice/voice_lines.json: the narrator's captions (the clips are generated from it).</summary>
    public static class VoiceLines
    {
        [Serializable] public class Line { public string key, en, th; }
        [Serializable] private class File { public Line[] lines; }

        public static IEnumerable<Line> Read()
        {
            const string path = "Tools/voice/voice_lines.json";
            if (!System.IO.File.Exists(path)) { Debug.LogWarning("[TT Setup] voice lines missing: " + path); return Array.Empty<Line>(); }
            File f = JsonUtility.FromJson<File>(System.IO.File.ReadAllText(path, System.Text.Encoding.UTF8));
            return f?.lines ?? Array.Empty<Line>();
        }
    }

    public static class Manifest
    {
        [Serializable]
        public class Item
        {
            public string name, fbx, kind, displayName, sound, category;
            public float height, footprintRadius;
        }

        [Serializable]
        private class Wrapper { public Item[] items; }

        public static IEnumerable<Item> Read(string file)
        {
            string path = Path.Combine("Tools/blender/models", file);
            if (!File.Exists(path)) { Debug.LogWarning("[TT Setup] manifest missing: " + path); return Array.Empty<Item>(); }
            string json = File.ReadAllText(path).Trim();
            if (json.StartsWith("[")) json = "{\"items\":" + json + "}";
            else if (!json.Contains("\"items\""))
            {
                // Accept {"models": [...]} or similar single-array objects.
                int i = json.IndexOf('[');
                int j = json.LastIndexOf(']');
                if (i >= 0 && j > i) json = "{\"items\":" + json.Substring(i, j - i + 1) + "}";
            }
            Wrapper w = JsonUtility.FromJson<Wrapper>(json);
            return w?.items ?? Array.Empty<Item>();
        }
    }
}
