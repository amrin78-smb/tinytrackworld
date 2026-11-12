using System;
using System.Collections.Generic;
using TinyTracks.Audio;
using TinyTracks.Core;
using UnityEngine;

namespace TinyTracks.Tracks
{
    /// <summary>
    /// Owns the railway graph and its visuals: one pooled model per piece (+ accessories such as the station
    /// building, depot shed and crossing barriers), support pillars under elevated track, open-end markers while
    /// building, and tappable switch arrows on junctions.
    /// </summary>
    public class TrackNetworkManager : MonoBehaviour
    {
        public static TrackNetworkManager Instance { get; private set; }

        public ContentLibrary content;

        public TrackGraph Graph { get; } = new TrackGraph();
        public event Action NetworkChanged;
        public event Action<int> PieceRemoved;

        private readonly Dictionary<int, TrackPieceView> views = new Dictionary<int, TrackPieceView>();
        private readonly Dictionary<TrackType, Stack<TrackPieceView>> pool = new Dictionary<TrackType, Stack<TrackPieceView>>();
        private readonly List<GameObject> markers = new List<GameObject>();
        private readonly List<(TrackNode node, int connector)> openScratch = new List<(TrackNode, int)>();
        private Transform root, markerRoot;
        private bool markersVisible;
        private bool markersDirty = true;
        private Material markerMat;

        public bool SuppressEffects { get; set; }

        private void Awake()
        {
            Instance = this;
            root = new GameObject("Railway").transform;
            root.SetParent(transform, false);
            markerRoot = new GameObject("OpenEnds").transform;
            markerRoot.SetParent(transform, false);
            Graph.NodeAdded += OnNodeAdded;
            Graph.NodeRemoved += OnNodeRemoved;
            Graph.Changed += () => { markersDirty = true; RefreshSwitchArrows(); NetworkChanged?.Invoke(); };
        }

        // ------------------------------------------------------------------------------------------------ editing API
        public TrackNode Place(TrackType type, TrackPose pose, int id = 0, int switchState = 0)
        {
            TrackNode n = Graph.Add(type, pose, id);
            if (n != null && n.shape.isSwitch && switchState != 0) Graph.SetSwitch(n.id, switchState);
            return n;
        }

        public bool Remove(int id) => Graph.Remove(id);

        public void ClearAll() => Graph.Clear();

        public TrackPieceView View(int id) => views.TryGetValue(id, out TrackPieceView v) ? v : null;

        // ------------------------------------------------------------------------------------------------ visuals
        private void OnNodeAdded(TrackNode n)
        {
            TrackPieceView v = Rent(n.type);
            v.Bind(n);
            v.transform.SetPositionAndRotation(n.pose.position, n.pose.Rotation);
            v.gameObject.SetActive(true);
            BuildPillars(v, n);
            views[n.id] = v;
            if (!SuppressEffects) Juice.PopIn(v.Visual);
        }

        private void OnNodeRemoved(TrackNode n)
        {
            if (!views.TryGetValue(n.id, out TrackPieceView v)) return;
            views.Remove(n.id);
            PieceRemoved?.Invoke(n.id);
            if (SuppressEffects) { Return(v); return; }
            Juice.ShrinkOut(v.Visual, () => Return(v));
        }

        private TrackPieceView Rent(TrackType type)
        {
            if (pool.TryGetValue(type, out Stack<TrackPieceView> s) && s.Count > 0) return s.Pop();
            TrackPieceDefinition def = content != null ? content.Track(type) : null;
            var go = new GameObject("Track_" + type);
            go.transform.SetParent(root, false);
            TrackPieceView v = go.AddComponent<TrackPieceView>();
            v.Create(def, content);
            return v;
        }

        private void Return(TrackPieceView v)
        {
            if (v == null) return;
            Juice.Kill(v.Visual);
            v.Visual.localScale = Vector3.one;
            v.ClearPillars();
            v.gameObject.SetActive(false);
            if (!pool.TryGetValue(v.Type, out Stack<TrackPieceView> s)) pool[v.Type] = s = new Stack<TrackPieceView>();
            s.Push(v);
        }

        private void BuildPillars(TrackPieceView v, TrackNode n)
        {
            if (content == null || content.pillarPrefab == null) return;
            if (n.type == TrackType.Ramp || n.type == TrackType.WoodenBridge || n.type == TrackType.StoneBridge) return;
            TrackPath p = n.shape.paths[0];
            float len = p.Length;
            int count = Mathf.Max(1, Mathf.RoundToInt(len / 3.2f));
            for (int i = 0; i < count; i++)
            {
                float s = len * (i + 0.5f) / count;
                Vector3 w = n.pose.TransformPoint(p.Evaluate(s));
                if (w.y < 0.6f) continue;
                v.AddPillar(content.pillarPrefab, w, n.pose.yaw);
            }
        }

        // ------------------------------------------------------------------------------------------------ markers
        public void ShowOpenEnds(bool show)
        {
            markersVisible = show;
            markersDirty = true;
        }

        private void LateUpdate()
        {
            if (!markersDirty) return;
            markersDirty = false;
            if (markerMat == null && content != null) markerMat = content.markerMaterial;
            int used = 0;
            if (markersVisible)
            {
                Graph.OpenEnds(openScratch);
                foreach ((TrackNode node, int c) in openScratch)
                {
                    GameObject m = used < markers.Count ? markers[used] : CreateMarker();
                    used++;
                    Vector3 dir = TrackMath.HeadingToDir(node.worldConnectorHeading[c]);
                    m.transform.SetPositionAndRotation(node.worldConnectorPos[c] + dir * 0.75f + Vector3.up * 0.2f,
                        Quaternion.LookRotation(dir));
                    m.SetActive(true);
                }
            }
            for (int i = used; i < markers.Count; i++) markers[i].SetActive(false);
        }

        private GameObject CreateMarker()
        {
            var go = new GameObject("OpenEnd");
            go.transform.SetParent(markerRoot, false);
            var disc = new GameObject("Disc");
            disc.transform.SetParent(go.transform, false);
            disc.transform.localScale = new Vector3(1.6f, 1f, 1.6f);
            disc.AddComponent<MeshFilter>().sharedMesh = MeshFactory.GroundQuad();
            var mr = disc.AddComponent<MeshRenderer>();
            mr.sharedMaterial = markerMat;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            var arrow = new GameObject("Arrow");
            arrow.transform.SetParent(go.transform, false);
            arrow.transform.localScale = new Vector3(0.9f, 1f, 0.9f);
            arrow.transform.localPosition = new Vector3(0f, 0.02f, 0f);
            arrow.AddComponent<MeshFilter>().sharedMesh = MeshFactory.Arrow(new Color32(255, 255, 255, 0));
            var ar = arrow.AddComponent<MeshRenderer>();
            ar.sharedMaterial = content != null ? content.toyMaterial : null;
            ar.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            go.AddComponent<MarkerBob>();
            markers.Add(go);
            return go;
        }

        /// <summary>Nearest open end to a world point within a radius (for tap-to-select an end).</summary>
        public bool NearestOpenEnd(Vector3 world, float radius, out TrackNode node, out int connector)
        {
            node = null; connector = -1;
            float best = radius;
            Graph.OpenEnds(openScratch);
            foreach ((TrackNode n, int c) in openScratch)
            {
                Vector3 dir = TrackMath.HeadingToDir(n.worldConnectorHeading[c]);
                Vector3 p = n.worldConnectorPos[c] + dir * 0.75f;
                float d = Vector2.Distance(new Vector2(p.x, p.z), new Vector2(world.x, world.z));
                if (d < best) { best = d; node = n; connector = c; }
            }
            return node != null;
        }

        // ------------------------------------------------------------------------------------------------ switches
        private void RefreshSwitchArrows()
        {
            foreach (KeyValuePair<int, TrackPieceView> kv in views)
            {
                TrackNode n = Graph.Get(kv.Key);
                if (n != null && n.shape.isSwitch) kv.Value.ShowSwitch(n);
            }
        }

        /// <summary>Flips the junction nearest the point (if any within reach). Returns true if one flipped.</summary>
        public bool TryFlipSwitchNear(Vector3 world, float radius)
        {
            TrackNode best = null;
            float bestD = radius;
            foreach (TrackNode n in Graph.Nodes.Values)
            {
                if (!n.shape.isSwitch) continue;
                Vector3 c = n.pose.TransformPoint(n.shape.localCenter);
                float d = Vector2.Distance(new Vector2(c.x, c.z), new Vector2(world.x, world.z));
                if (d < bestD) { bestD = d; best = n; }
            }
            if (best == null) return false;
            Graph.ToggleSwitch(best.id);
            if (views.TryGetValue(best.id, out TrackPieceView v)) Juice.Squash(v.SwitchArrow, 0.25f);
            AudioManager.Sfx(AudioManager.Clips != null ? AudioManager.Clips.switchFlip : null);
            return true;
        }

        public void Wiggle(int id)
        {
            if (views.TryGetValue(id, out TrackPieceView v)) Juice.Wobble(v.Visual, 6f, 0.4f);
        }

        public IEnumerable<TrackPieceView> Views => views.Values;
    }

    /// <summary>Gentle bob + pulse for open-end markers (one tiny component, only on a handful of objects).</summary>
    public class MarkerBob : MonoBehaviour
    {
        private Transform arrow;
        private float phase;

        private void Awake()
        {
            arrow = transform.Find("Arrow");
            phase = UnityEngine.Random.value * 6f;
        }

        private void Update()
        {
            float t = Time.time * 3f + phase;
            if (arrow != null) arrow.localPosition = new Vector3(0f, 0.05f + 0.12f * (0.5f + 0.5f * Mathf.Sin(t)), Mathf.Sin(t) * 0.12f);
        }
    }
}
