using System;
using System.Collections.Generic;
using UnityEngine;

namespace TinyTracks.Core
{
    /// <summary>
    /// Tiny tween runner for friendly feedback (pop-in, wobble, bounce, squash). One Update loop for all tweens; no
    /// per-object MonoBehaviours, no allocations per frame after warm-up.
    /// </summary>
    public class Juice : MonoBehaviour
    {
        private enum Kind { PopIn, Wobble, Bounce, Squash, ShrinkOut, Spin }

        private struct Tween
        {
            public Transform t;
            public Kind kind;
            public float start, duration, amount;
            public Vector3 baseScale, basePos;
            public Quaternion baseRot;
            public Action done;
        }

        private static Juice instance;
        private readonly List<Tween> tweens = new List<Tween>(64);

        private static Juice I
        {
            get
            {
                if (instance == null)
                {
                    var go = new GameObject("[Juice]");
                    DontDestroyOnLoad(go);
                    instance = go.AddComponent<Juice>();
                }
                return instance;
            }
        }

        private static void Add(Transform t, Kind k, float duration, float amount, Action done = null)
        {
            if (t == null) return;
            Juice j = I;
            // Restore and replace an existing tween on the same transform so effects never accumulate.
            for (int i = j.tweens.Count - 1; i >= 0; i--)
            {
                if (j.tweens[i].t != t) continue;
                Restore(j.tweens[i]);
                j.tweens.RemoveAt(i);
            }
            j.tweens.Add(new Tween
            {
                t = t, kind = k, start = Time.unscaledTime, duration = duration, amount = amount,
                baseScale = t.localScale, basePos = t.localPosition, baseRot = t.localRotation, done = done,
            });
        }

        public static void PopIn(Transform t, float duration = 0.35f) { Add(t, Kind.PopIn, duration, 1f); if (t != null) t.localScale = Vector3.zero; }
        public static void Wobble(Transform t, float degrees = 10f, float duration = 0.5f) => Add(t, Kind.Wobble, duration, degrees);
        public static void Bounce(Transform t, float height = 0.35f, float duration = 0.45f) => Add(t, Kind.Bounce, duration, height);
        public static void Squash(Transform t, float amount = 0.15f, float duration = 0.3f) => Add(t, Kind.Squash, duration, amount);
        public static void Spin(Transform t, float turns = 1f, float duration = 0.6f) => Add(t, Kind.Spin, duration, turns);
        public static void ShrinkOut(Transform t, Action done, float duration = 0.22f) => Add(t, Kind.ShrinkOut, duration, 1f, done);

        public static void Kill(Transform t)
        {
            if (instance == null) return;
            for (int i = instance.tweens.Count - 1; i >= 0; i--)
                if (instance.tweens[i].t == t) { Restore(instance.tweens[i]); instance.tweens.RemoveAt(i); }
        }

        private static void Restore(Tween tw)
        {
            if (tw.t == null) return;
            if (tw.kind == Kind.PopIn || tw.kind == Kind.Squash) tw.t.localScale = tw.baseScale;
            if (tw.kind == Kind.Wobble || tw.kind == Kind.Spin) tw.t.localRotation = tw.baseRot;
            if (tw.kind == Kind.Bounce) tw.t.localPosition = tw.basePos;
        }

        private void Update()
        {
            float now = Time.unscaledTime;
            for (int i = tweens.Count - 1; i >= 0; i--)
            {
                Tween tw = tweens[i];
                if (tw.t == null) { tweens.RemoveAt(i); continue; }
                float p = Mathf.Clamp01((now - tw.start) / tw.duration);
                switch (tw.kind)
                {
                    case Kind.PopIn:
                        tw.t.localScale = tw.baseScale * BackOut(p);
                        break;
                    case Kind.Wobble:
                        tw.t.localRotation = tw.baseRot * Quaternion.Euler(0f, 0f, Mathf.Sin(p * Mathf.PI * 4f) * tw.amount * (1f - p));
                        break;
                    case Kind.Bounce:
                        tw.t.localPosition = tw.basePos + Vector3.up * (Mathf.Sin(p * Mathf.PI) * tw.amount);
                        break;
                    case Kind.Squash:
                        float s = Mathf.Sin(p * Mathf.PI * 2f) * tw.amount * (1f - p);
                        tw.t.localScale = Vector3.Scale(tw.baseScale, new Vector3(1f + s, 1f - s, 1f + s));
                        break;
                    case Kind.Spin:
                        tw.t.localRotation = tw.baseRot * Quaternion.Euler(0f, EaseInOut(p) * 360f * tw.amount, 0f);
                        break;
                    case Kind.ShrinkOut:
                        tw.t.localScale = tw.baseScale * (1f - EaseInOut(p));
                        break;
                }
                if (p >= 1f)
                {
                    tweens.RemoveAt(i);
                    if (tw.kind != Kind.ShrinkOut) Restore(tw);
                    tw.done?.Invoke();
                }
            }
        }

        private static float BackOut(float t)
        {
            const float c1 = 1.70158f, c3 = c1 + 1f;
            return 1f + c3 * Mathf.Pow(t - 1f, 3f) + c1 * Mathf.Pow(t - 1f, 2f);
        }

        private static float EaseInOut(float t) => t * t * (3f - 2f * t);
    }
}
