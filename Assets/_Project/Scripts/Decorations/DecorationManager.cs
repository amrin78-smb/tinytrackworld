using System;
using System.Collections.Generic;
using TinyTracks.Core;
using TinyTracks.Interaction;
using UnityEngine;

namespace TinyTracks.Decorations
{
    [Serializable]
    public class PlacedDecoration
    {
        public int id;
        public string defId;
        public Vector3 position;
        public float yaw;
        [NonSerialized] public GameObject instance;
    }

    /// <summary>Child-placed scenery (trees, houses, animals, people...). Saved; world dressing is not.</summary>
    public class DecorationManager : MonoBehaviour
    {
        public static DecorationManager Instance { get; private set; }

        public ContentLibrary content;
        public event Action Changed;

        private readonly Dictionary<int, PlacedDecoration> placed = new Dictionary<int, PlacedDecoration>();
        private int nextId = 1;
        private Transform root;

        public IEnumerable<PlacedDecoration> All => placed.Values;
        public int Count => placed.Count;
        public bool SuppressEffects { get; set; }

        private void Awake()
        {
            Instance = this;
            root = new GameObject("Decorations").transform;
            root.SetParent(transform, false);
        }

        public PlacedDecoration Get(int id) => placed.TryGetValue(id, out PlacedDecoration p) ? p : null;

        public int Place(string defId, Vector3 pos, float yaw, int id = 0)
        {
            DecorationDefinition def = content.Decoration(defId);
            if (def == null || def.prefab == null) return 0;
            if (id <= 0 || placed.ContainsKey(id)) id = nextId;
            nextId = Mathf.Max(nextId, id + 1);
            GameObject go = Instantiate(def.prefab, root, false);
            go.name = $"Deco_{defId}_{id}";
            go.transform.SetPositionAndRotation(new Vector3(pos.x, 0f, pos.z), Quaternion.Euler(0f, yaw, 0f));
            Interactable it = go.GetComponent<Interactable>();
            if (it != null) it.decorationId = id;
            var p = new PlacedDecoration { id = id, defId = defId, position = new Vector3(pos.x, 0f, pos.z), yaw = yaw, instance = go };
            placed[id] = p;
            if (!SuppressEffects) Juice.PopIn(go.transform);
            Changed?.Invoke();
            return id;
        }

        public void Move(int id, Vector3 pos, float yaw)
        {
            if (!placed.TryGetValue(id, out PlacedDecoration p)) return;
            p.position = new Vector3(pos.x, 0f, pos.z);
            p.yaw = yaw;
            if (p.instance != null)
            {
                p.instance.SetActive(true);
                p.instance.transform.SetPositionAndRotation(p.position, Quaternion.Euler(0f, yaw, 0f));
                Juice.Squash(p.instance.transform, 0.12f);
            }
            Changed?.Invoke();
        }

        public void SetHidden(int id, bool hidden)
        {
            if (placed.TryGetValue(id, out PlacedDecoration p) && p.instance != null) p.instance.SetActive(!hidden);
        }

        public void Remove(int id)
        {
            if (!placed.TryGetValue(id, out PlacedDecoration p)) return;
            placed.Remove(id);
            if (p.instance != null)
            {
                GameObject go = p.instance;
                if (SuppressEffects) Destroy(go);
                else Juice.ShrinkOut(go.transform, () => Destroy(go));
            }
            Changed?.Invoke();
        }

        public void ClearAll()
        {
            foreach (PlacedDecoration p in placed.Values) if (p.instance != null) Destroy(p.instance);
            placed.Clear();
            nextId = 1;
            Changed?.Invoke();
        }

        /// <summary>Placed decoration under a world point (by footprint), or null.</summary>
        public PlacedDecoration At(Vector3 world, float extra = 0.3f)
        {
            PlacedDecoration best = null;
            float bestD = float.MaxValue;
            foreach (PlacedDecoration p in placed.Values)
            {
                DecorationDefinition d = content.Decoration(p.defId);
                float r = (d != null ? d.footprintRadius : 0.6f) + extra;
                float dist = Vector2.Distance(new Vector2(p.position.x, p.position.z), new Vector2(world.x, world.z));
                if (dist < r && dist < bestD) { bestD = dist; best = p; }
            }
            return best;
        }
    }
}
