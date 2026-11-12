using System.Collections.Generic;
using TinyTracks.Interaction;
using UnityEngine;

namespace TinyTracks.World
{
    /// <summary>
    /// One Update loop for every gentle looping animation in the world: trees sway, windmill sails turn, animals
    /// nod and swish tails, clouds drift, birds circle. On Low graphics only the nearest few sway/nod.
    /// </summary>
    public class AmbientAnimator : MonoBehaviour
    {
        private class Entry
        {
            public Interactable owner;
            public Transform head, tail, canopy, sails;
            public Quaternion headRot, tailRot, canopyRot, sailsRot;
            public float phase, spin, spinBoost;
        }

        private struct Drifter
        {
            public Transform t;
            public Vector3 velocity;
            public float wrap;
        }

        private struct Flyer
        {
            public Transform t, wingL, wingR;
            public Vector3 centre;
            public float radius, speed, phase, height;
        }

        private static AmbientAnimator instance;
        private readonly List<Entry> entries = new List<Entry>();
        private readonly Dictionary<Interactable, Entry> lookup = new Dictionary<Interactable, Entry>();
        private readonly List<Drifter> drifters = new List<Drifter>();
        private readonly List<Flyer> flyers = new List<Flyer>();

        public static bool LowDetail { get; set; }
        public float maxAnimatedDistance = 40f;

        private void Awake() => instance = this;

        private static AmbientAnimator I
        {
            get
            {
                if (instance == null) instance = new GameObject("[AmbientAnimator]").AddComponent<AmbientAnimator>();
                return instance;
            }
        }

        public static void Register(Interactable owner, Transform head, Transform tail, Transform canopy, Transform sails)
        {
            if (head == null && tail == null && canopy == null && sails == null) return;
            AmbientAnimator a = I;
            if (a.lookup.ContainsKey(owner)) return;
            var e = new Entry
            {
                owner = owner, head = head, tail = tail, canopy = canopy, sails = sails,
                headRot = head != null ? head.localRotation : Quaternion.identity,
                tailRot = tail != null ? tail.localRotation : Quaternion.identity,
                canopyRot = canopy != null ? canopy.localRotation : Quaternion.identity,
                sailsRot = sails != null ? sails.localRotation : Quaternion.identity,
                phase = Random.value * 10f,
                spin = sails != null ? 40f : 0f,
            };
            a.entries.Add(e);
            a.lookup[owner] = e;
        }

        public static void Unregister(Interactable owner)
        {
            if (instance == null || !instance.lookup.TryGetValue(owner, out Entry e)) return;
            instance.lookup.Remove(owner);
            instance.entries.Remove(e);
        }

        public static void BoostSpin(Interactable owner, float seconds)
        {
            if (instance != null && instance.lookup.TryGetValue(owner, out Entry e)) e.spinBoost = seconds;
        }

        public static void AddDrifter(Transform t, Vector3 velocity, float wrap) =>
            I.drifters.Add(new Drifter { t = t, velocity = velocity, wrap = wrap });

        public static void AddFlyer(Transform t, Vector3 centre, float radius, float height, float speed)
        {
            Transform wl = null, wr = null;
            foreach (Transform c in t.GetComponentsInChildren<Transform>(true))
            {
                if (c.name == "WingL") wl = c;
                else if (c.name == "WingR") wr = c;
            }
            I.flyers.Add(new Flyer { t = t, wingL = wl, wingR = wr, centre = centre, radius = radius, speed = speed, height = height, phase = Random.value * 6.28f });
        }

        private void Update()
        {
            float time = Time.time, dt = Time.deltaTime;
            Camera cam = Camera.main;
            Vector3 camPos = cam != null ? cam.transform.position : Vector3.zero;
            float maxD2 = (LowDetail ? maxAnimatedDistance * 0.6f : maxAnimatedDistance * 1.5f);
            maxD2 *= maxD2;

            for (int i = 0; i < entries.Count; i++)
            {
                Entry e = entries[i];
                if (e.owner == null) continue;
                if (e.sails != null)
                {
                    e.spinBoost = Mathf.Max(0f, e.spinBoost - dt);
                    float speed = e.spin * (1f + 4f * Mathf.Min(1f, e.spinBoost));
                    e.sails.localRotation *= Quaternion.Euler(0f, 0f, speed * dt);
                }
                if ((e.owner.transform.position - camPos).sqrMagnitude > maxD2) continue;
                float t = time + e.phase;
                if (e.canopy != null) e.canopy.localRotation = e.canopyRot * Quaternion.Euler(Mathf.Sin(t * 1.1f) * 1.6f, 0f, Mathf.Sin(t * 0.8f) * 1.8f);
                if (e.head != null)
                {
                    // Occasional nod / graze.
                    float nod = Mathf.Max(0f, Mathf.Sin(t * 0.45f)) ;
                    e.head.localRotation = e.headRot * Quaternion.Euler(nod * nod * 14f, Mathf.Sin(t * 0.3f) * 8f, 0f);
                }
                if (e.tail != null) e.tail.localRotation = e.tailRot * Quaternion.Euler(0f, Mathf.Sin(t * 3.1f) * 14f, 0f);
            }

            for (int i = 0; i < drifters.Count; i++)
            {
                Drifter d = drifters[i];
                if (d.t == null) continue;
                Vector3 p = d.t.position + d.velocity * dt;
                if (p.x > d.wrap) p.x = -d.wrap;
                if (p.x < -d.wrap) p.x = d.wrap;
                d.t.position = p;
            }

            for (int i = 0; i < flyers.Count; i++)
            {
                Flyer f = flyers[i];
                if (f.t == null) continue;
                float a = f.phase + time * f.speed / f.radius;
                Vector3 p = f.centre + new Vector3(Mathf.Cos(a) * f.radius, f.height + Mathf.Sin(time * 0.7f + f.phase) * 0.8f, Mathf.Sin(a) * f.radius * 0.7f);
                Vector3 dir = p - f.t.position;
                f.t.position = p;
                if (dir.sqrMagnitude > 1e-6f) f.t.rotation = Quaternion.LookRotation(dir.normalized);
                float flap = Mathf.Sin(time * 14f + f.phase) * 35f;
                if (f.wingL != null) f.wingL.localRotation = Quaternion.Euler(0f, 0f, flap);
                if (f.wingR != null) f.wingR.localRotation = Quaternion.Euler(0f, 0f, -flap);
            }
        }
    }
}
