using System.Collections.Generic;
using TinyTracks.Core;
using UnityEngine;

namespace TinyTracks.Tracks
{
    /// <summary>The visible model of one placed track piece. Pooled by <see cref="TrackNetworkManager"/>.</summary>
    public class TrackPieceView : MonoBehaviour
    {
        public int NodeId { get; private set; }
        public TrackType Type { get; private set; }
        /// <summary>Child that holds the meshes (tweened for pop-in / wobble so the root stays on the exact pose).</summary>
        public Transform Visual { get; private set; }
        public Transform SwitchArrow { get; private set; }
        public Transform Accessory { get; private set; }

        private readonly List<GameObject> pillars = new List<GameObject>();
        private readonly Stack<GameObject> pillarPool = new Stack<GameObject>();

        public void Create(TrackPieceDefinition def, ContentLibrary content)
        {
            Visual = new GameObject("Visual").transform;
            Visual.SetParent(transform, false);
            if (def != null)
            {
                Type = def.type;
                if (def.prefab != null) Instantiate(def.prefab, Visual, false).name = "Model";
                if (def.accessory != null)
                {
                    GameObject acc = Instantiate(def.accessory, Visual, false);
                    acc.name = "Accessory";
                    acc.transform.localPosition = def.accessoryOffset;
                    acc.transform.localRotation = Quaternion.Euler(0f, def.accessoryYaw, 0f);
                    Accessory = acc.transform;
                }
                if (TrackShapeLibrary.Get(def.type).isSwitch && content != null)
                {
                    var a = new GameObject("SwitchArrow");
                    a.transform.SetParent(Visual, false);
                    a.AddComponent<MeshFilter>().sharedMesh = MeshFactory.Arrow(new Color32(255, 214, 60, 0));
                    var mr = a.AddComponent<MeshRenderer>();
                    mr.sharedMaterial = content.toyMaterial;
                    mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                    a.transform.localScale = new Vector3(1.1f, 1f, 1.1f);
                    SwitchArrow = a.transform;
                }
            }
        }

        public void Bind(TrackNode n)
        {
            NodeId = n.id;
            Type = n.type;
            name = $"Track_{n.type}_{n.id}";
            foreach (CrossingBarrier cb in GetComponentsInChildren<CrossingBarrier>(true)) cb.Bind(n.id);
            if (SwitchArrow != null) ShowSwitch(n);
        }

        /// <summary>Points the arrow along the active branch, a little way in from the shared entry.</summary>
        public void ShowSwitch(TrackNode n)
        {
            if (SwitchArrow == null) return;
            var list = new List<int>(2);
            n.shape.PathsAt(0, list);
            if (list.Count == 0) return;
            TrackPath p = n.shape.paths[list[Mathf.Clamp(n.switchState, 0, list.Count - 1)]];
            float s = Mathf.Min(2.2f, p.Length * 0.5f);
            Vector3 a = p.Evaluate(s - 0.4f), b = p.Evaluate(s + 0.4f);
            SwitchArrow.localPosition = (a + b) * 0.5f + Vector3.up * 0.2f;
            SwitchArrow.localRotation = Quaternion.LookRotation((b - a).normalized);
        }

        public void AddPillar(GameObject prefab, Vector3 worldTop, float yaw)
        {
            GameObject p = pillarPool.Count > 0 ? pillarPool.Pop() : Instantiate(prefab, Visual, false);
            p.SetActive(true);
            float top = Mathf.Max(0.2f, worldTop.y - 0.16f);
            p.transform.SetPositionAndRotation(new Vector3(worldTop.x, 0f, worldTop.z), Quaternion.Euler(0f, yaw, 0f));
            p.transform.localScale = new Vector3(1f, top / 1.84f, 1f);
            pillars.Add(p);
        }

        public void ClearPillars()
        {
            foreach (GameObject p in pillars) { p.SetActive(false); pillarPool.Push(p); }
            pillars.Clear();
        }
    }
}
