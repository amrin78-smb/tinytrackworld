using System;
using System.Collections.Generic;
using System.IO;
using TinyTracks.Decorations;
using TinyTracks.Tracks;
using TinyTracks.Trains;
using UnityEngine;

namespace TinyTracks.SaveSystem
{
    [Serializable]
    public class TrackSave
    {
        public int id;
        public string type;
        public float x, y, z, yaw;
        public int sw;
    }

    [Serializable]
    public class DecorationSave
    {
        public int id;
        public string def;
        public float x, z, yaw;
    }

    [Serializable]
    public class TrainSave
    {
        public string loco;
        public List<string> cars = new List<string>();
        public bool placed;
        public int node, path;
        public float s;
        public bool forward;
        public int speed = 1;
        /// <summary>Painted body colour as "RRGGBB" (empty = original colours).</summary>
        public string paint = "";
    }

    [Serializable]
    public class WorldSave
    {
        public const int CurrentVersion = 1;
        public int version = CurrentVersion;
        public string world = "sunny_valley";
        public string savedAt;
        public List<TrackSave> tracks = new List<TrackSave>();
        public List<DecorationSave> decorations = new List<DecorationSave>();
        public TrainSave train = new TrainSave();
        /// <summary>Additional trains (0.3+). Older saves simply have none.</summary>
        public List<TrainSave> moreTrains = new List<TrainSave>();
    }

    [Serializable]
    public class SettingsSave
    {
        public float music = 0.45f, sfx = 0.8f, ambient = 0.5f;
        public int quality = -1; // -1 = auto
        public bool tutorialSeen;
        public float voice = 1f;
        public string language = "auto"; // "auto" | "en" | "th"
        public string lastWorld = "sunny_valley";
        /// <summary>Surprises found so far (discoverable locos/animals) and progress towards the next one.</summary>
        public List<string> discovered = new List<string>();
        public float surprisePoints;
    }

    /// <summary>
    /// Versioned JSON saves in Application.persistentDataPath. Writes are atomic (temp file + replace) and keep one
    /// backup; a missing or corrupted save falls back to the backup, then to a fresh default world. Autosave is
    /// debounced so construction never stalls on file IO.
    /// </summary>
    public class SaveManager : MonoBehaviour
    {
        public static SaveManager Instance { get; private set; }

        public float autosaveDelay = 2.5f;
        public TrackNetworkManager network;
        public DecorationManager decorations;
        public TrainManager trains;

        public static string Folder => Application.persistentDataPath;
        /// <summary>The world being played; each world has its own save (Sunny Valley keeps the original file names).</summary>
        public static string WorldId { get; set; } = "sunny_valley";
        private static string Stem => WorldId == "sunny_valley" ? "world" : "world_" + WorldId;
        public static string WorldPath => Path.Combine(Folder, Stem + ".json");
        public static string BackupPath => Path.Combine(Folder, Stem + ".bak.json");
        public static string SettingsPath => Path.Combine(Folder, "settings.json");

        public SettingsSave Settings { get; private set; } = new SettingsSave();
        public bool Loading { get; private set; }
        public string LastError { get; private set; }

        private float dirtyAt = -1f;

        private void Awake()
        {
            Instance = this;
            Settings = LoadSettings();
        }

        private void Start()
        {
            if (network != null) network.NetworkChanged += MarkDirty;
            if (decorations != null) decorations.Changed += MarkDirty;
            if (trains != null) trains.TrainChanged += MarkDirty;
        }

        public void MarkDirty()
        {
            if (Loading) return;
            dirtyAt = Time.unscaledTime;
        }

        private void Update()
        {
            if (dirtyAt >= 0f && Time.unscaledTime - dirtyAt > autosaveDelay)
            {
                dirtyAt = -1f;
                SaveWorld();
            }
        }

        private void OnApplicationPause(bool paused) { if (paused) Flush(); }
        private void OnApplicationQuit() => Flush();

        public void Flush()
        {
            if (dirtyAt >= 0f) { dirtyAt = -1f; SaveWorld(); }
            else if (trains != null && trains.Current != null) SaveWorld(); // keep the train position fresh
        }

        public static bool HasSave() => File.Exists(WorldPath) || File.Exists(BackupPath);

        // ------------------------------------------------------------------------------------------------ capture
        public WorldSave Capture()
        {
            var w = new WorldSave { savedAt = DateTime.UtcNow.ToString("o"), world = WorldId };
            foreach (TrackNode n in network.Graph.Nodes.Values)
                w.tracks.Add(new TrackSave
                {
                    id = n.id, type = n.type.ToString(), x = n.pose.position.x, y = n.pose.position.y, z = n.pose.position.z,
                    yaw = n.pose.yaw, sw = n.switchState,
                });
            if (decorations != null)
                foreach (PlacedDecoration d in decorations.All)
                    w.decorations.Add(new DecorationSave { id = d.id, def = d.defId, x = d.position.x, z = d.position.z, yaw = d.yaw });
            if (trains != null)
            {
                w.train.loco = trains.SelectedLocoId;
                w.train.cars = new List<string>(trains.SelectedCars);
                Fill(w.train, trains.Current);
                foreach (TrainController t in trains.All)
                {
                    if (t == trains.Current) continue;
                    var ts = new TrainSave { loco = t.LocoDefinition != null ? t.LocoDefinition.id : null };
                    foreach (TinyTracks.Core.TrainDefinition d in t.CarDefinitions()) ts.cars.Add(d.id);
                    Fill(ts, t);
                    if (ts.placed) w.moreTrains.Add(ts);
                }
            }
            return w;
        }

        private void Fill(TrainSave ts, TrainController t)
        {
            if (t == null || !t.Spine.IsValid) return;
            Span h = t.Spine.Head;
            TrackNode n = network.Graph.Get(h.node);
            if (n == null) return;
            TrackPath p = n.shape.paths[h.path];
            ts.placed = true;
            ts.node = h.node;
            ts.path = h.path;
            ts.forward = h.forward;
            ts.s = h.forward ? t.Spine.headS : p.Length - t.Spine.headS;
            ts.speed = t.SpeedLevel;
            ts.paint = t.PaintColor.HasValue ? ColorUtility.ToHtmlStringRGB(t.PaintColor.Value) : "";
        }

        private static Color? ParsePaint(string hex) =>
            !string.IsNullOrEmpty(hex) && ColorUtility.TryParseHtmlString("#" + hex, out Color c) ? c : (Color?)null;

        public bool SaveWorld()
        {
            try
            {
                string json = JsonUtility.ToJson(Capture(), true);
                WriteAtomic(WorldPath, BackupPath, json);
                LastError = null;
                return true;
            }
            catch (Exception e)
            {
                LastError = e.Message;
                Debug.LogWarning("[TT Save] save failed: " + e.Message);
                return false;
            }
        }

        public static void WriteAtomic(string path, string backup, string content)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            string tmp = path + ".tmp";
            File.WriteAllText(tmp, content);
            if (File.Exists(path))
            {
                if (backup != null) File.Copy(path, backup, true);
                File.Delete(path);
            }
            File.Move(tmp, path);
        }

        // ------------------------------------------------------------------------------------------------ load
        /// <summary>Reads the save (or its backup). Returns null if neither is usable.</summary>
        public static WorldSave ReadWorld(out string problem)
        {
            problem = null;
            foreach (string p in new[] { WorldPath, BackupPath })
            {
                if (!File.Exists(p)) continue;
                try
                {
                    WorldSave w = Parse(File.ReadAllText(p));
                    if (w != null) return w;
                    problem = "unreadable " + Path.GetFileName(p);
                }
                catch (Exception e)
                {
                    problem = e.Message;
                }
            }
            return null;
        }

        /// <summary>Parses and migrates a save; returns null for corrupted / future-version data.</summary>
        public static WorldSave Parse(string json)
        {
            if (string.IsNullOrWhiteSpace(json)) return null;
            WorldSave w;
            try { w = JsonUtility.FromJson<WorldSave>(json); }
            catch { return null; }
            if (w == null || w.version <= 0 || w.version > WorldSave.CurrentVersion) return null;
            w.tracks ??= new List<TrackSave>();
            w.decorations ??= new List<DecorationSave>();
            w.train ??= new TrainSave();
            return w;
        }

        /// <summary>Rebuilds tracks, decorations and the train from a save (connections are reconstructed from poses).</summary>
        public void Apply(WorldSave w)
        {
            Loading = true;
            network.SuppressEffects = true;
            if (decorations != null) decorations.SuppressEffects = true;
            try
            {
                trains?.RemoveAll();
                network.ClearAll();
                decorations?.ClearAll();
                foreach (TrackSave t in w.tracks)
                {
                    if (!Enum.TryParse(t.type, out TrackType type)) continue;
                    if (float.IsNaN(t.x) || float.IsNaN(t.z)) continue;
                    network.Place(type, new TrackPose(new Vector3(t.x, t.y, t.z), t.yaw), t.id, t.sw);
                }
                if (decorations != null)
                    foreach (DecorationSave d in w.decorations) decorations.Place(d.def, new Vector3(d.x, 0f, d.z), d.yaw, d.id);
                if (trains != null && w.train != null)
                {
                    if (!string.IsNullOrEmpty(w.train.loco)) trains.SelectLoco(w.train.loco);
                    trains.SetCarriages(w.train.cars ?? new List<string>());
                    TrackNode n = w.train.placed ? network.Graph.Get(w.train.node) : null;
                    if (n != null && w.train.path >= 0 && w.train.path < n.shape.paths.Length)
                    {
                        trains.PlaceAt(n.id, w.train.path, Mathf.Clamp(w.train.s, 0f, n.shape.paths[w.train.path].Length), w.train.forward);
                        trains.Current?.SetSpeedLevel(w.train.speed);
                        Color? paint = ParsePaint(w.train.paint);
                        if (paint.HasValue) trains.Current?.Paint(paint);
                    }
                    TrainController selected = trains.Current;
                    if (w.moreTrains != null)
                        foreach (TrainSave ts in w.moreTrains)
                        {
                            TrackNode m = network.Graph.Get(ts.node);
                            if (m == null || ts.path < 0 || ts.path >= m.shape.paths.Length) continue;
                            TrainController extra = trains.RestoreTrain(ts.loco, ts.cars ?? new List<string>(), m.id, ts.path,
                                Mathf.Clamp(ts.s, 0f, m.shape.paths[ts.path].Length), ts.forward, ts.speed);
                            Color? p2 = ParsePaint(ts.paint);
                            if (extra != null && p2.HasValue) extra.Paint(p2);
                        }
                    if (selected != null) trains.Select(selected);
                }
            }
            finally
            {
                network.SuppressEffects = false;
                if (decorations != null) decorations.SuppressEffects = false;
                Loading = false;
            }
        }

        public void DeleteWorld()
        {
            try
            {
                if (File.Exists(WorldPath)) File.Delete(WorldPath);
                if (File.Exists(BackupPath)) File.Delete(BackupPath);
            }
            catch (Exception e) { Debug.LogWarning("[TT Save] delete failed: " + e.Message); }
        }

        // ------------------------------------------------------------------------------------------------ settings
        public static SettingsSave LoadSettings()
        {
            try
            {
                if (File.Exists(SettingsPath))
                {
                    SettingsSave s = JsonUtility.FromJson<SettingsSave>(File.ReadAllText(SettingsPath));
                    if (s != null) return s;
                }
            }
            catch (Exception e) { Debug.LogWarning("[TT Save] settings unreadable: " + e.Message); }
            return new SettingsSave();
        }

        public void SaveSettings()
        {
            try { WriteAtomic(SettingsPath, null, JsonUtility.ToJson(Settings, true)); }
            catch (Exception e) { Debug.LogWarning("[TT Save] settings save failed: " + e.Message); }
        }
    }
}
