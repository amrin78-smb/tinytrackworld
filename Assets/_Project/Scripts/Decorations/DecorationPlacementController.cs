using System;
using TinyTracks.Audio;
using TinyTracks.Building;
using TinyTracks.Cameras;
using TinyTracks.Core;
using TinyTracks.Inputs;
using TinyTracks.Tracks;
using UnityEngine;

namespace TinyTracks.Decorations
{
    /// <summary>
    /// Decorate mode: pick an item, a ghost appears in the middle of the view; tap the ground to move it there, tap the
    /// ghost (or the same button again) to place it. Drag the ghost and release to place. Long-press a placed item to
    /// move it; delete mode removes with a tap. Items may not sit on the track bed.
    /// </summary>
    public class DecorationPlacementController : MonoBehaviour, IDragHandler
    {
        public static DecorationPlacementController Instance { get; private set; }

        public DecorationManager decorations;
        public TrackNetworkManager network;
        public ContentLibrary content;
        public Camera cam;
        public Vector2 buildableHalfSize = new Vector2(30f, 22f);

        public CommandStack Commands { get; set; }
        public bool Active { get; private set; }
        public bool DeleteMode { get; private set; }
        public string Selected { get; private set; }
        public event Action StateChanged;

        private GhostView ghost;
        private Vector3 ghostPos;
        private float yaw;
        private bool dragging;
        private bool moving;
        private PlacedDecoration moveItem;
        private Vector3 moveFromPos;
        private float moveFromYaw;

        private void Awake() => Instance = this;
        private void Start() => InputManager.Instance?.Register(this);
        private void OnDestroy() => InputManager.Instance?.Unregister(this);

        public void SetActive(bool on)
        {
            Active = on;
            if (!on) { Deselect(); DeleteMode = false; }
            StateChanged?.Invoke();
        }

        public void Select(string defId)
        {
            if (!Active) return;
            DeleteMode = false;
            if (Selected == defId && ghost != null) { Confirm(); return; }
            DestroyGhost();
            DecorationDefinition def = content.Decoration(defId);
            if (def == null) return;
            Selected = defId;
            ghost = new GhostView(def.prefab, content.ghostMaterial, "Ghost_" + defId);
            Vector3 c = CameraController.Instance != null ? CameraController.Instance.Target : Vector3.zero;
            // Start a little to the side of the view centre so it does not land on the track every time.
            ghostPos = FindFreeSpot(c + new Vector3(UnityEngine.Random.Range(-2f, 2f), 0f, UnityEngine.Random.Range(-1.5f, 1.5f)), def);
            yaw = UnityEngine.Random.Range(0, 8) * 45f;
            Apply();
            AudioManager.Sfx(AudioManager.Clips?.button);
            StateChanged?.Invoke();
        }

        public void Deselect()
        {
            DestroyGhost();
            Selected = null;
            StateChanged?.Invoke();
        }

        public void ToggleDeleteMode()
        {
            DeleteMode = !DeleteMode;
            if (DeleteMode) Deselect();
            AudioManager.Sfx(AudioManager.Clips?.buttonToggle);
            StateChanged?.Invoke();
        }

        public void Rotate()
        {
            if (ghost == null) return;
            yaw = (yaw + 45f) % 360f;
            Apply();
            Juice.Squash(ghost.Root.transform, 0.12f);
            AudioManager.Sfx(AudioManager.Clips?.buttonToggle);
        }

        public bool Confirm()
        {
            if (ghost == null || Selected == null) return false;
            if (!IsValid(ghostPos, content.Decoration(Selected)))
            {
                AudioManager.Sfx(AudioManager.Clips?.invalid);
                Juice.Wobble(ghost.Root.transform, 8f, 0.35f);
                return false;
            }
            Commands.Execute(new AddDecorationCommand(decorations, Selected, ghostPos, yaw));
            AudioManager.Sfx(AudioManager.Clips?.placeDecor);
            DecorationDefinition def = content.Decoration(Selected);
            if (def != null && def.sound != null) AudioManager.Sfx(def.sound, 0.7f);
            // Offer the next one nearby so tapping again keeps decorating.
            ghostPos = FindFreeSpot(ghostPos + Quaternion.Euler(0f, UnityEngine.Random.Range(0f, 360f), 0f) * Vector3.forward * (def != null ? def.footprintRadius * 2.4f + 0.5f : 1.5f), def);
            Apply();
            return true;
        }

        private Vector3 FindFreeSpot(Vector3 near, DecorationDefinition def)
        {
            near.y = 0f;
            if (IsValid(near, def)) return near;
            for (int ring = 1; ring < 8; ring++)
                for (int k = 0; k < 8; k++)
                {
                    Vector3 p = near + Quaternion.Euler(0f, k * 45f + ring * 13f, 0f) * Vector3.forward * (ring * 1.2f);
                    if (IsValid(p, def)) return p;
                }
            return near;
        }

        public bool IsValid(Vector3 p, DecorationDefinition def)
        {
            float r = def != null ? def.footprintRadius : 0.6f;
            if (Mathf.Abs(p.x) > buildableHalfSize.x - r * 0.5f || Mathf.Abs(p.z) > buildableHalfSize.y - r * 0.5f) return false;
            // Not on the railway (ground-level track only; things may stand under elevated track).
            if (network.Graph.NearestPoint(p, r + TrackGraph.BedHalfWidth, out TrackNode n, out int path, out float s))
            {
                Vector3 w = n.WorldPoint(path, s);
                if (w.y < 1.2f) return false;
            }
            PlacedDecoration other = decorations.At(p, -0.1f);
            if (other != null && (moveItem == null || other.id != moveItem.id))
            {
                DecorationDefinition od = content.Decoration(other.defId);
                float or = od != null ? od.footprintRadius : 0.6f;
                if (Vector3.Distance(other.position, p) < (r + or) * 0.6f) return false;
            }
            return true;
        }

        private void Apply()
        {
            if (ghost == null) return;
            ghost.SetPose(ghostPos, Quaternion.Euler(0f, yaw, 0f));
            ghost.SetValid(IsValid(ghostPos, content.Decoration(Selected)));
            CameraController.Instance?.KeepInView(ghostPos);
        }

        private void DestroyGhost()
        {
            ghost?.Destroy();
            ghost = null;
            dragging = false;
        }

        public bool HandleTap(Vector2 screen)
        {
            if (!Active || !InputManager.ScreenToGround(cam, screen, 0f, out Vector3 world)) return false;
            if (DeleteMode)
            {
                PlacedDecoration p = decorations.At(world);
                if (p == null) return false;
                Commands.Execute(new RemoveDecorationCommand(decorations, p.id));
                AudioManager.Sfx(AudioManager.Clips?.trackRemove);
                return true;
            }
            if (ghost != null)
            {
                DecorationDefinition def = content.Decoration(Selected);
                float r = Mathf.Max(1.2f, def != null ? def.footprintRadius + 0.5f : 1.2f);
                if (Vector2.Distance(new Vector2(world.x, world.z), new Vector2(ghostPos.x, ghostPos.z)) < r) { Confirm(); return true; }
                ghostPos = new Vector3(world.x, 0f, world.z);
                Apply();
                return true;
            }
            return false;
        }

        public bool TryBeginDrag(Vector2 screen, bool longPress)
        {
            if (!Active || DeleteMode || !InputManager.ScreenToGround(cam, screen, 0f, out Vector3 world)) return false;
            if (ghost != null && !longPress)
            {
                DecorationDefinition def = content.Decoration(Selected);
                float r = Mathf.Max(1.5f, def != null ? def.footprintRadius + 0.8f : 1.5f);
                if (Vector2.Distance(new Vector2(world.x, world.z), new Vector2(ghostPos.x, ghostPos.z)) < r) { dragging = true; return true; }
                return false;
            }
            if (longPress && ghost == null)
            {
                PlacedDecoration p = decorations.At(world);
                if (p == null) return false;
                moving = true;
                moveItem = p;
                moveFromPos = p.position;
                moveFromYaw = p.yaw;
                Selected = p.defId;
                decorations.SetHidden(p.id, true);
                ghost = new GhostView(content.Decoration(p.defId)?.prefab, content.ghostMaterial, "Ghost_Move");
                ghostPos = p.position;
                yaw = p.yaw;
                Apply();
                dragging = true;
                AudioManager.Sfx(AudioManager.Clips?.button);
                return true;
            }
            return false;
        }

        public void Drag(Vector2 screen)
        {
            if (!dragging || ghost == null) return;
            if (!InputManager.ScreenToGround(cam, screen, 0f, out Vector3 world)) return;
            ghostPos = new Vector3(world.x, 0f, world.z);
            Apply();
        }

        public void EndDrag(Vector2 screen)
        {
            if (!dragging) return;
            dragging = false;
            if (moving)
            {
                moving = false;
                PlacedDecoration item = moveItem;
                bool ok = IsValid(ghostPos, content.Decoration(item.defId));
                if (ok)
                {
                    var cmd = new MoveDecorationCommand(decorations, item.id, moveFromPos, moveFromYaw, ghostPos, yaw);
                    Commands.Execute(cmd);
                    AudioManager.Sfx(AudioManager.Clips?.placeDecor);
                }
                else
                {
                    decorations.Move(item.id, moveFromPos, moveFromYaw);
                    AudioManager.Sfx(AudioManager.Clips?.invalid);
                }
                moveItem = null;
                Deselect();
                return;
            }
            Confirm();
        }
    }
}
