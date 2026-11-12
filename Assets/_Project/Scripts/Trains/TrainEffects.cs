using System.Collections.Generic;
using TinyTracks.Core;
using UnityEngine;

namespace TinyTracks.Trains
{
    /// <summary>Pooled smoke puffs (soft white spheres that rise, grow and shrink away) and the dead-end hint marker.</summary>
    public class TrainEffects : MonoBehaviour
    {
        public ContentLibrary content;
        public int maxPuffs = 24;
        public float PuffInterval { get; set; } = 0.55f;

        private struct PuffState
        {
            public Transform t;
            public float age, life, size;
            public Vector3 vel;
        }

        private readonly List<PuffState> live = new List<PuffState>();
        private readonly Stack<Transform> pool = new Stack<Transform>();
        private Mesh sphere;
        private Transform deadEnd;
        private float deadEndTime;

        private void Awake()
        {
            sphere = BuildSphere();
        }

        public void SetLowDetail(bool low)
        {
            maxPuffs = low ? 10 : 24;
            PuffInterval = low ? 0.9f : 0.55f;
        }

        public void Puff(Vector3 at, float scale = 1f)
        {
            if (live.Count >= maxPuffs) return;
            Transform t = pool.Count > 0 ? pool.Pop() : CreatePuff();
            t.gameObject.SetActive(true);
            t.position = at;
            t.localScale = Vector3.one * 0.1f;
            live.Add(new PuffState
            {
                t = t, age = 0f, life = Random.Range(1.1f, 1.6f), size = Random.Range(0.45f, 0.65f) * scale,
                vel = new Vector3(Random.Range(-0.2f, 0.2f), Random.Range(1.0f, 1.5f), Random.Range(-0.2f, 0.2f)),
            });
        }

        private Transform CreatePuff()
        {
            var go = new GameObject("Puff");
            go.transform.SetParent(transform, false);
            go.AddComponent<MeshFilter>().sharedMesh = sphere;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = content != null ? content.toyMaterial : null;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            mr.receiveShadows = false;
            return go.transform;
        }

        private void Update()
        {
            float dt = Time.deltaTime;
            for (int i = live.Count - 1; i >= 0; i--)
            {
                PuffState p = live[i];
                p.age += dt;
                float k = p.age / p.life;
                if (k >= 1f)
                {
                    p.t.gameObject.SetActive(false);
                    pool.Push(p.t);
                    live.RemoveAt(i);
                    continue;
                }
                p.t.position += p.vel * dt;
                p.vel *= 1f - dt * 0.8f;
                float grow = Mathf.Sin(Mathf.Min(1f, k * 1.4f) * Mathf.PI * 0.5f);
                float shrink = k > 0.6f ? 1f - (k - 0.6f) / 0.4f : 1f;
                p.t.localScale = Vector3.one * (p.size * grow * shrink);
                live[i] = p;
            }
            if (deadEnd != null && deadEnd.gameObject.activeSelf)
            {
                deadEndTime += dt;
                deadEnd.localScale = Vector3.one * (1f + 0.12f * Mathf.Sin(deadEndTime * 5f));
                deadEnd.Rotate(0f, 60f * dt, 0f, Space.World);
            }
        }

        /// <summary>A bobbing yellow "!" sign at the end of the line so the child sees where track is missing.</summary>
        public void ShowDeadEnd(Vector3 at)
        {
            if (deadEnd == null)
            {
                var go = new GameObject("DeadEndHint");
                go.transform.SetParent(transform, false);
                var bar = new GameObject("Bar");
                bar.transform.SetParent(go.transform, false);
                bar.AddComponent<MeshFilter>().sharedMesh = sphere;
                bar.AddComponent<MeshRenderer>().sharedMaterial = content != null ? content.toyMaterial : null;
                bar.transform.localScale = new Vector3(0.28f, 0.75f, 0.28f);
                bar.transform.localPosition = new Vector3(0f, 0.75f, 0f);
                var dot = new GameObject("Dot");
                dot.transform.SetParent(go.transform, false);
                dot.AddComponent<MeshFilter>().sharedMesh = sphere;
                dot.AddComponent<MeshRenderer>().sharedMaterial = content != null ? content.toyMaterial : null;
                dot.transform.localScale = Vector3.one * 0.3f;
                SetColour(bar, new Color32(255, 196, 40, 0));
                SetColour(dot, new Color32(255, 196, 40, 0));
                deadEnd = go.transform;
            }
            deadEnd.gameObject.SetActive(true);
            deadEnd.position = at + Vector3.up * 1.4f;
            deadEndTime = 0f;
            Juice.PopIn(deadEnd, 0.3f);
        }

        public void HideDeadEnd()
        {
            if (deadEnd != null) deadEnd.gameObject.SetActive(false);
        }

        private static void SetColour(GameObject go, Color32 c)
        {
            MeshFilter mf = go.GetComponent<MeshFilter>();
            Mesh m = Instantiate(mf.sharedMesh);
            var cols = new Color32[m.vertexCount];
            for (int i = 0; i < cols.Length; i++) cols[i] = c;
            m.colors32 = cols;
            mf.sharedMesh = m;
        }

        /// <summary>Low-poly smooth sphere with white vertex colour (the ToyLit shader reads vertex colour).</summary>
        private static Mesh BuildSphere()
        {
            GameObject tmp = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            Mesh src = tmp.GetComponent<MeshFilter>().sharedMesh;
            Mesh m = Instantiate(src);
            m.name = "PuffSphere";
            Destroy(tmp);
            var cols = new Color32[m.vertexCount];
            for (int i = 0; i < cols.Length; i++) cols[i] = new Color32(250, 250, 250, 0);
            m.colors32 = cols;
            return m;
        }
    }
}
