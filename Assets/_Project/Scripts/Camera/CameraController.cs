using TinyTracks.Inputs;
using UnityEngine;

namespace TinyTracks.Cameras
{
    /// <summary>
    /// Elevated toy-table camera: orbits a ground target. One finger pans, pinch zooms, twist rotates gently.
    /// Follow mode tracks a transform (the train) but the child can still zoom/rotate; panning leaves follow mode.
    /// Everything is smoothed (no sudden moves) and clamped to configurable bounds.
    /// </summary>
    [RequireComponent(typeof(Camera))]
    public class CameraController : MonoBehaviour
    {
        public static CameraController Instance { get; private set; }

        [Header("Framing")]
        public float minDistance = 9f;
        public float maxDistance = 46f;
        public float defaultDistance = 26f;
        public float minPitch = 38f;
        public float maxPitch = 62f;
        public float defaultYaw = 0f;
        public Vector3 defaultTarget = new Vector3(0f, 0f, -2f);

        [Header("Feel")]
        public float smoothTime = 0.18f;
        public float followSmoothTime = 0.35f;
        public float panSpeed = 1f;
        public bool allowRotation = true;

        [Header("Bounds (half extents around origin)")]
        public Vector2 bounds = new Vector2(34f, 26f);

        private Camera cam;
        private Vector3 target, targetGoal, targetVel;
        private float distance, distanceGoal, distanceVel;
        private float yaw, yawGoal, yawVel;
        private float pitch;
        private Transform follow;
        private Vector3 followOffset;

        public Camera Cam => cam;
        public bool IsFollowing => follow != null;
        public Transform FollowTarget => follow;

        private void Awake()
        {
            Instance = this;
            cam = GetComponent<Camera>();
            ResetView(true);
        }

        private void OnEnable()
        {
            InputManager im = InputManager.Instance;
            if (im == null) return;
            im.PanDelta += OnPan;
            im.TwoFingerPan += OnPan;
            im.Pinch += OnPinch;
            im.Twist += OnTwist;
        }

        private void Start()
        {
            // InputManager may wake after us.
            OnDisable();
            OnEnable();
        }

        private void OnDisable()
        {
            InputManager im = InputManager.Instance;
            if (im == null) return;
            im.PanDelta -= OnPan;
            im.TwoFingerPan -= OnPan;
            im.Pinch -= OnPinch;
            im.Twist -= OnTwist;
        }

        public void ResetView(bool instant = false)
        {
            follow = null;
            targetGoal = defaultTarget;
            distanceGoal = defaultDistance;
            yawGoal = defaultYaw;
            if (instant)
            {
                target = targetGoal;
                distance = distanceGoal;
                yaw = yawGoal;
                Apply();
            }
        }

        public void Follow(Transform t, float zoom = 16f)
        {
            follow = t;
            if (t != null) distanceGoal = Mathf.Clamp(zoom, minDistance, maxDistance);
        }

        public void StopFollowing() => follow = null;

        /// <summary>Gently moves the view to look at a world point (e.g. a newly placed piece) without changing zoom.</summary>
        public void FocusOn(Vector3 p, float? zoom = null)
        {
            follow = null;
            targetGoal = ClampTarget(new Vector3(p.x, 0f, p.z));
            if (zoom.HasValue) distanceGoal = Mathf.Clamp(zoom.Value, minDistance, maxDistance);
        }

        /// <summary>Nudges the view so a world point stays comfortably on screen (used while building).</summary>
        public void KeepInView(Vector3 p, float margin = 0.18f)
        {
            if (follow != null) return;
            Vector3 vp = cam.WorldToViewportPoint(p);
            if (vp.z < 0) return;
            Vector3 shift = Vector3.zero;
            if (vp.x < margin || vp.x > 1 - margin || vp.y < margin + 0.1f || vp.y > 1 - margin)
            {
                Vector3 flat = new Vector3(p.x, 0f, p.z);
                shift = (flat - targetGoal) * 0.5f;
            }
            targetGoal = ClampTarget(targetGoal + shift);
        }

        private void OnPan(Vector2 delta)
        {
            if (follow != null) follow = null;
            // Convert screen delta into a ground move at the current distance.
            float worldPerPixel = 2f * distance * Mathf.Tan(cam.fieldOfView * 0.5f * Mathf.Deg2Rad) / Mathf.Max(1, Screen.height);
            Quaternion yr = Quaternion.Euler(0f, yaw, 0f);
            Vector3 right = yr * Vector3.right;
            Vector3 fwd = yr * Vector3.forward;
            float pitchFactor = 1f / Mathf.Sin(Mathf.Max(20f, pitch) * Mathf.Deg2Rad);
            Vector3 move = -(right * delta.x + fwd * delta.y * pitchFactor) * worldPerPixel * panSpeed;
            targetGoal = ClampTarget(targetGoal + move);
            target = ClampTarget(target + move); // direct feel under the finger
        }

        private void OnPinch(float scale, Vector2 centre)
        {
            if (scale <= 0f) return;
            distanceGoal = Mathf.Clamp(distanceGoal / scale, minDistance, maxDistance);
        }

        private void OnTwist(float degrees)
        {
            if (!allowRotation) return;
            yawGoal += Mathf.Clamp(degrees, -10f, 10f);
        }

        private Vector3 ClampTarget(Vector3 t)
        {
            t.x = Mathf.Clamp(t.x, -bounds.x, bounds.x);
            t.z = Mathf.Clamp(t.z, -bounds.y, bounds.y);
            t.y = 0f;
            return t;
        }

        private void LateUpdate()
        {
            float dt = Time.unscaledDeltaTime;
            if (follow != null)
            {
                Vector3 f = follow.position;
                targetGoal = ClampTarget(new Vector3(f.x, 0f, f.z));
                target = Vector3.SmoothDamp(target, targetGoal, ref targetVel, followSmoothTime, Mathf.Infinity, dt);
            }
            else
            {
                target = Vector3.SmoothDamp(target, targetGoal, ref targetVel, smoothTime, Mathf.Infinity, dt);
            }
            distance = Mathf.SmoothDamp(distance, distanceGoal, ref distanceVel, smoothTime, Mathf.Infinity, dt);
            yaw = Mathf.SmoothDampAngle(yaw, yawGoal, ref yawVel, smoothTime * 1.5f, Mathf.Infinity, dt);
            Apply();
        }

        private void Apply()
        {
            // Closer = lower and more cinematic; further = more top-down for building overview.
            float t = Mathf.InverseLerp(minDistance, maxDistance, distance);
            pitch = Mathf.Lerp(minPitch, maxPitch, t);
            Quaternion rot = Quaternion.Euler(pitch, yaw, 0f);
            transform.position = target + rot * new Vector3(0f, 0f, -distance);
            transform.rotation = rot;
        }

        public float Distance => distance;
        public Vector3 Target => target;
    }
}
