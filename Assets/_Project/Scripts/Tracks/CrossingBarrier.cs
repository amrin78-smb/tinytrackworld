using System.Collections.Generic;
using TinyTracks.Audio;
using UnityEngine;

namespace TinyTracks.Tracks
{
    /// <summary>Level-crossing barriers: arms lower (with a gentle ding-ding) while a train is near, then rise.</summary>
    public class CrossingBarrier : MonoBehaviour
    {
        private static readonly Dictionary<int, CrossingBarrier> registry = new Dictionary<int, CrossingBarrier>();

        public int nodeId = -1;
        public float raisedAngle = 80f;
        public float speed = 120f;

        private readonly List<Transform> arms = new List<Transform>();
        private readonly List<Quaternion> downRot = new List<Quaternion>();
        private float closedUntil;
        private float angle; // 0 = down (closed), raisedAngle = up (open)
        private bool wasClosed;

        private void Awake()
        {
            foreach (Transform t in GetComponentsInChildren<Transform>(true))
                if (t.name == "Arm") { arms.Add(t); downRot.Add(t.localRotation); }
            angle = raisedAngle;
            Apply();
        }

        public void Bind(int id)
        {
            if (nodeId >= 0 && registry.TryGetValue(nodeId, out CrossingBarrier b) && b == this) registry.Remove(nodeId);
            nodeId = id;
            if (id >= 0) registry[id] = this;
        }

        private void OnDisable()
        {
            if (nodeId >= 0 && registry.TryGetValue(nodeId, out CrossingBarrier b) && b == this) registry.Remove(nodeId);
            angle = raisedAngle;
            Apply();
        }

        private void OnEnable()
        {
            if (nodeId >= 0) registry[nodeId] = this;
        }

        public static void KeepClosed(int node)
        {
            if (registry.TryGetValue(node, out CrossingBarrier b)) b.closedUntil = Time.time + 1.2f;
        }

        private void Update()
        {
            bool closed = Time.time < closedUntil;
            if (closed && !wasClosed) AudioManager.Sfx(AudioManager.Clips?.crossingBell, 0.5f);
            wasClosed = closed;
            float target = closed ? 0f : raisedAngle;
            if (Mathf.Approximately(angle, target)) return;
            angle = Mathf.MoveTowards(angle, target, speed * Time.deltaTime);
            Apply();
        }

        private void Apply()
        {
            // Arms lie along their local -X (Blender +X) when down; raising rotates them about the local Z axis.
            for (int i = 0; i < arms.Count; i++) arms[i].localRotation = downRot[i] * Quaternion.Euler(0f, 0f, -angle);
        }
    }
}
