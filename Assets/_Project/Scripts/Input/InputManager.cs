using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.EnhancedTouch;
using Touch = UnityEngine.InputSystem.EnhancedTouch.Touch;

namespace TinyTracks.Inputs
{
    /// <summary>Something that wants first claim on single-finger drags in the world (ghost pieces, moving objects).</summary>
    public interface IDragHandler
    {
        /// <summary>Return true to take this drag (the camera will not pan).</summary>
        bool TryBeginDrag(Vector2 screen, bool longPress);
        void Drag(Vector2 screen);
        void EndDrag(Vector2 screen);
    }

    /// <summary>
    /// Touch + mouse gestures for toddlers: tap, one-finger drag, two-finger pinch/twist/pan, long press. Touches that
    /// start on UI never reach the world. Tolerant thresholds (small fingers wobble).
    /// </summary>
    public class InputManager : MonoBehaviour
    {
        public static InputManager Instance { get; private set; }

        public float tapMaxMove = 28f;      // pixels at 1080p, scaled by screen height
        public float tapMaxTime = 0.6f;
        public float longPressTime = 0.55f;

        public event Action<Vector2> Tap;
        public event Action<Vector2> LongPress;
        public event Action<Vector2> PanDelta;            // one finger drag not claimed by a handler (screen delta)
        public event Action<float, Vector2> Pinch;        // scale factor (>1 = fingers apart), centre
        public event Action<float> Twist;                 // degrees
        public event Action<Vector2> TwoFingerPan;        // centre delta

        private readonly List<IDragHandler> handlers = new List<IDragHandler>();
        private IDragHandler activeHandler;

        private bool pointerDown;
        private bool overUi;
        private Vector2 downPos, lastPos;
        private float downTime;
        private bool moved, longFired, dragging;
        private bool multi;
        private float lastPinchDist, lastAngle;
        private Vector2 lastCentre;

        public bool IsDragging => dragging;
        public bool InputEnabled { get; set; } = true;

        private float Scale => Mathf.Max(0.5f, Screen.height / 1080f);

        private void Awake()
        {
            Instance = this;
            EnhancedTouchSupport.Enable();
        }

        private void OnDestroy()
        {
            if (Instance == this) Instance = null;
        }

        public void Register(IDragHandler h) { if (!handlers.Contains(h)) handlers.Add(h); }
        public void Unregister(IDragHandler h) { handlers.Remove(h); if (activeHandler == h) activeHandler = null; }

        private void Update()
        {
            if (!InputEnabled) { Cancel(); return; }
            var touches = Touch.activeTouches;
            if (touches.Count >= 2) { HandleMulti(touches[0].screenPosition, touches[1].screenPosition, touches[0].touchId, touches[1].touchId); return; }
            if (multi && touches.Count < 2) { multi = false; pointerDown = false; }

            if (touches.Count == 1)
            {
                Touch t = touches[0];
                HandleSingle(t.screenPosition, t.phase == UnityEngine.InputSystem.TouchPhase.Began, t.phase == UnityEngine.InputSystem.TouchPhase.Ended || t.phase == UnityEngine.InputSystem.TouchPhase.Canceled, t.touchId);
                return;
            }

            Mouse mouse = Mouse.current;
            if (mouse == null) return;
            Vector2 mp = mouse.position.ReadValue();
            HandleSingle(mp, mouse.leftButton.wasPressedThisFrame, mouse.leftButton.wasReleasedThisFrame, -1);
            float scroll = mouse.scroll.ReadValue().y;
            if (Mathf.Abs(scroll) > 0.01f && !OverUi(mp)) Pinch?.Invoke(scroll > 0 ? 1.1f : 1f / 1.1f, mp);
            if (mouse.rightButton.isPressed)
            {
                Vector2 d = mouse.delta.ReadValue();
                if (d.sqrMagnitude > 0.01f) Twist?.Invoke(d.x * 0.3f);
            }
        }

        private void HandleSingle(Vector2 pos, bool began, bool ended, int id)
        {
            if (began)
            {
                pointerDown = true;
                overUi = OverUi(pos);
                downPos = lastPos = pos;
                downTime = Time.unscaledTime;
                moved = longFired = dragging = false;
                activeHandler = null;
                return;
            }
            if (!pointerDown) return;
            if (overUi) { if (ended) pointerDown = false; return; }

            if (!moved && (pos - downPos).magnitude > tapMaxMove * Scale)
            {
                moved = true;
                dragging = true;
                foreach (IDragHandler h in handlers)
                    if (h != null && h.TryBeginDrag(downPos, false)) { activeHandler = h; break; }
            }

            if (!moved && !longFired && Time.unscaledTime - downTime > longPressTime)
            {
                longFired = true;
                LongPress?.Invoke(pos);
                // A long press may start a drag (pick up a piece).
                foreach (IDragHandler h in handlers)
                    if (h != null && h.TryBeginDrag(pos, true)) { activeHandler = h; moved = true; dragging = true; break; }
            }

            if (moved)
            {
                if (activeHandler != null) activeHandler.Drag(pos);
                else PanDelta?.Invoke(pos - lastPos);
            }
            lastPos = pos;

            if (ended)
            {
                pointerDown = false;
                if (activeHandler != null) activeHandler.EndDrag(pos);
                else if (!moved && !longFired && Time.unscaledTime - downTime <= tapMaxTime) Tap?.Invoke(pos);
                activeHandler = null;
                dragging = false;
            }
        }

        private void HandleMulti(Vector2 a, Vector2 b, int ida, int idb)
        {
            Vector2 centre = (a + b) * 0.5f;
            float dist = Vector2.Distance(a, b);
            float angle = Mathf.Atan2(b.y - a.y, b.x - a.x) * Mathf.Rad2Deg;
            if (!multi)
            {
                multi = true;
                if (activeHandler != null) { activeHandler.EndDrag(lastPos); activeHandler = null; }
                pointerDown = false;
                dragging = false;
                overUi = OverUi(a) || OverUi(b);
                lastPinchDist = dist;
                lastAngle = angle;
                lastCentre = centre;
                return;
            }
            if (overUi) return;
            if (lastPinchDist > 1f && dist > 1f) Pinch?.Invoke(dist / lastPinchDist, centre);
            Twist?.Invoke(Mathf.DeltaAngle(lastAngle, angle));
            TwoFingerPan?.Invoke(centre - lastCentre);
            lastPinchDist = dist;
            lastAngle = angle;
            lastCentre = centre;
        }

        private void Cancel()
        {
            if (activeHandler != null) activeHandler.EndDrag(lastPos);
            activeHandler = null;
            pointerDown = dragging = multi = false;
        }

        private static readonly List<RaycastResult> uiHits = new List<RaycastResult>();

        private static PointerEventData uiProbe;

        /// <summary>True when a raycastable UI element is under the screen position.</summary>
        public static bool OverUi(Vector2 screen)
        {
            EventSystem es = EventSystem.current;
            if (es == null) return false;
            if (uiProbe == null || uiProbe.currentInputModule == null) uiProbe = new PointerEventData(es);
            uiProbe.position = screen;
            uiHits.Clear();
            es.RaycastAll(uiProbe, uiHits);
            return uiHits.Count > 0;
        }

        /// <summary>Screen point to the ground plane at the given height.</summary>
        public static bool ScreenToGround(Camera cam, Vector2 screen, float height, out Vector3 world)
        {
            Ray r = cam.ScreenPointToRay(screen);
            var plane = new Plane(Vector3.up, new Vector3(0f, height, 0f));
            if (plane.Raycast(r, out float d) && d < 500f)
            {
                world = r.GetPoint(d);
                return true;
            }
            world = Vector3.zero;
            return false;
        }
    }
}
