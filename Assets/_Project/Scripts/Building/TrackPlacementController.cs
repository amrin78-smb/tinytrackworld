using System;
using System.Collections.Generic;
using TinyTracks.Audio;
using TinyTracks.Cameras;
using TinyTracks.Core;
using TinyTracks.Inputs;
using TinyTracks.Tracks;
using UnityEngine;

namespace TinyTracks.Building
{
    /// <summary>
    /// Toddler-friendly track building.
    ///  * Pick a piece: a ghost appears attached to the active open end (or under the screen centre).
    ///  * Tap the ghost (or the same piece button again) to place it; the next ghost appears at the new end, so
    ///    tap-tap-tap grows the railway.
    ///  * Drag the ghost anywhere: it snaps to nearby open ends; release to place (if it fits).
    ///  * Rotate cycles which end of the piece attaches (left/right) or turns a free piece by 45 degrees.
    ///  * Long-press an existing piece to pick it up and move it. Delete mode: tap a piece to remove it.
    ///  * Tap a junction to flip it. Everything is undoable.
    /// </summary>
    public class TrackPlacementController : MonoBehaviour, IDragHandler
    {
        public static TrackPlacementController Instance { get; private set; }

        public TrackNetworkManager network;
        public ContentLibrary content;
        public Camera cam;
        public float snapRadius = TrackSnapping.DefaultSnapRadius;
        public float tapGhostRadius = 3f;
        public Vector2 buildableHalfSize = new Vector2(30f, 22f);

        public CommandStack Commands { get; set; }
        public bool Active { get; private set; }
        public bool DeleteMode { get; private set; }
        public TrackType? Selected { get; private set; }
        public bool HasGhost => ghost != null;
        public bool GhostValid => current.valid && InBounds(current.pose);

        /// <summary>Raised after a piece is placed: (node, connectedCount, closedLoop).</summary>
        public event Action<TrackNode, int, bool> Placed;
        public event Action StateChanged;

        private GhostView ghost;
        private SnapResult current;
        private int rotation;
        private bool freePlaced;           // ghost moved by the child to a free spot (don't jump back to the end)
        private int activeNode = -1, activeConnector = -1;
        private bool draggingGhost;
        private readonly List<(TrackNode, int)> openScratch = new List<(TrackNode, int)>();

        // moving an existing piece
        private bool moving;
        private int moveId;
        private TrackType moveType;
        private TrackPose moveFrom;
        private int moveSwitch;

        private void Awake() => Instance = this;

        private void Start()
        {
            InputManager.Instance?.Register(this);
            if (network != null) network.NetworkChanged += OnNetworkChanged;
        }

        private void OnDestroy()
        {
            InputManager.Instance?.Unregister(this);
        }

        public void SetActive(bool on)
        {
            Active = on;
            if (!on) { Deselect(); DeleteMode = false; }
            network.ShowOpenEnds(on);
            StateChanged?.Invoke();
        }

        // ------------------------------------------------------------------------------------------------ selection
        public void Select(TrackType type)
        {
            if (!Active) return;
            DeleteMode = false;
            if (Selected == type && ghost != null)
            {
                // Tapping the same button again places the piece (one-tap building).
                Confirm();
                return;
            }
            DestroyGhost();
            Selected = type;
            rotation = 0;
            freePlaced = false;
            TrackPieceDefinition def = content.Track(type);
            ghost = new GhostView(def != null ? def.prefab : null, content.ghostMaterial, "Ghost_" + type);
            if (def != null && def.accessory != null) ghost.Add(def.accessory, def.accessoryOffset, def.accessoryYaw);
            Reposition();
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
            rotation++;
            if (current.snapped)
            {
                TrackNode n = network.Graph.Get(current.targetNode);
                if (n != null) current = TrackSnapping.AttachTo(network.Graph, TrackShapeLibrary.Get(Selected.Value), n, current.targetConnector, rotation);
            }
            else
            {
                Vector3 centre = current.pose.TransformPoint(TrackShapeLibrary.Get(Selected.Value).localCenter);
                current = TrackSnapping.FindPlacement(network.Graph, TrackShapeLibrary.Get(Selected.Value), centre, rotation, 0f, openScratch);
            }
            ApplyGhost();
            Juice.Squash(ghost.Root.transform, 0.12f);
            AudioManager.Sfx(AudioManager.Clips?.buttonToggle);
        }

        /// <summary>Places the ghost if valid; otherwise a gentle "no" and a wiggle.</summary>
        public bool Confirm()
        {
            if (ghost == null || Selected == null) return false;
            if (!GhostValid)
            {
                AudioManager.Sfx(AudioManager.Clips?.invalid);
                Juice.Wobble(ghost.Root.transform, 8f, 0.35f);
                return false;
            }
            TrackType type = Selected.Value;
            var cmd = new AddTrackCommand(network, type, current.pose);
            Commands.Execute(cmd);
            TrackNode n = network.Graph.Get(cmd.Id);
            if (n == null) return false;
            int linked = 0;
            for (int c = 0; c < n.linkNode.Length; c++) if (n.linkNode[c] >= 0) linked++;
            bool closedLoop = linked >= 2 && AllLinked(n);
            AudioManager.Sfx(linked > 0 ? AudioManager.Clips?.trackSnap : AudioManager.Clips?.trackPlace);
            if (closedLoop) AudioManager.Sfx(AudioManager.Clips?.tada, 0.8f);

            // Continue from the new piece's free end (the one furthest from where we attached).
            ChooseActiveEndAfterPlacing(n);
            freePlaced = false;
            Placed?.Invoke(n, linked, closedLoop);
            Reposition();
            return true;
        }

        private static bool AllLinked(TrackNode n)
        {
            for (int c = 0; c < n.linkNode.Length; c++) if (n.IsConnectable(c) && n.linkNode[c] < 0) return false;
            return true;
        }

        private void ChooseActiveEndAfterPlacing(TrackNode n)
        {
            activeNode = -1;
            activeConnector = -1;
            // Prefer connector 1 (the natural "exit"), then any other open one.
            if (n.IsOpen(1 < n.linkNode.Length ? 1 : 0)) { activeNode = n.id; activeConnector = 1 < n.linkNode.Length ? 1 : 0; return; }
            for (int c = 0; c < n.linkNode.Length; c++)
                if (n.IsOpen(c)) { activeNode = n.id; activeConnector = c; return; }
        }

        private void OnNetworkChanged()
        {
            // Keep the active end valid when pieces are removed/undone.
            TrackNode n = activeNode >= 0 ? network.Graph.Get(activeNode) : null;
            if (n == null || activeConnector < 0 || activeConnector >= n.linkNode.Length || !n.IsOpen(activeConnector))
            {
                activeNode = -1;
                activeConnector = -1;
            }
            if (ghost != null && !draggingGhost && !moving) Reposition();
        }

        /// <summary>Puts the ghost at the active end, or the nearest open end to the view centre, or free in view.</summary>
        private void Reposition()
        {
            if (ghost == null || Selected == null) return;
            TrackShape shape = TrackShapeLibrary.Get(Selected.Value);
            if (freePlaced)
            {
                Vector3 c = current.pose.TransformPoint(shape.localCenter);
                current = TrackSnapping.FindPlacement(network.Graph, shape, c, rotation, snapRadius, openScratch);
                ApplyGhost();
                return;
            }
            TrackNode target = activeNode >= 0 ? network.Graph.Get(activeNode) : null;
            if (target == null || !target.IsOpen(activeConnector)) PickEndNearView(out target);
            if (target != null)
            {
                current = TrackSnapping.AttachTo(network.Graph, shape, target, activeConnector, rotation);
                // If this orientation does not fit, try the others before showing red.
                if (!current.valid)
                {
                    int count = TrackSnapping.AttachableConnectorCount(shape);
                    for (int k = 1; k < count && !current.valid; k++)
                    {
                        SnapResult alt = TrackSnapping.AttachTo(network.Graph, shape, target, activeConnector, rotation + k);
                        if (alt.valid) { current = alt; rotation += k; }
                    }
                }
            }
            else
            {
                Vector3 centre = CameraController.Instance != null ? CameraController.Instance.Target : Vector3.zero;
                current = TrackSnapping.FindPlacement(network.Graph, shape, centre, rotation, 0f, openScratch);
            }
            ApplyGhost();
        }

        private void PickEndNearView(out TrackNode target)
        {
            target = null;
            Vector3 centre = CameraController.Instance != null ? CameraController.Instance.Target : Vector3.zero;
            network.Graph.OpenEnds(openScratch);
            float best = 22f;
            foreach ((TrackNode n, int c) in openScratch)
            {
                float d = Vector3.Distance(n.worldConnectorPos[c], centre);
                if (d < best) { best = d; target = n; activeNode = n.id; activeConnector = c; }
            }
        }

        private void ApplyGhost()
        {
            if (ghost == null) return;
            ghost.SetPose(current.pose.position, current.pose.Rotation);
            ghost.SetValid(GhostValid);
            if (CameraController.Instance != null && Selected.HasValue)
                CameraController.Instance.KeepInView(current.pose.TransformPoint(TrackShapeLibrary.Get(Selected.Value).localCenter));
        }

        private bool InBounds(TrackPose pose)
        {
            if (Selected == null) return true;
            TrackShape s = TrackShapeLibrary.Get(Selected.Value);
            foreach (TrackConnector c in s.connectors)
            {
                Vector3 w = pose.TransformPoint(c.position);
                if (Mathf.Abs(w.x) > buildableHalfSize.x || Mathf.Abs(w.z) > buildableHalfSize.y) return false;
            }
            return true;
        }

        private void DestroyGhost()
        {
            ghost?.Destroy();
            ghost = null;
            draggingGhost = false;
        }

        // ------------------------------------------------------------------------------------------------ taps
        /// <summary>World tap while building. Returns true if consumed.</summary>
        public bool HandleTap(Vector2 screen)
        {
            if (!Active || !InputManager.ScreenToGround(cam, screen, 0f, out Vector3 world)) return false;

            if (DeleteMode)
            {
                if (network.Graph.NearestPoint(world, 1.2f, out TrackNode n, out _, out _)
                    || NearestElevated(screen, out n))
                {
                    Commands.Execute(new RemoveTrackCommand(network, n.id));
                    AudioManager.Sfx(AudioManager.Clips?.trackRemove);
                    return true;
                }
                return false;
            }

            if (ghost != null && Selected.HasValue)
            {
                Vector3 gc = current.pose.TransformPoint(TrackShapeLibrary.Get(Selected.Value).localCenter);
                if (Flat(gc - world) < tapGhostRadius) { Confirm(); return true; }
                if (network.NearestOpenEnd(world, 2.2f, out TrackNode en, out int ec))
                {
                    activeNode = en.id; activeConnector = ec; freePlaced = false; rotation = 0;
                    Reposition();
                    AudioManager.Sfx(AudioManager.Clips?.button);
                    return true;
                }
                // Move the ghost to where the child tapped.
                current = TrackSnapping.FindPlacement(network.Graph, TrackShapeLibrary.Get(Selected.Value), world, rotation, snapRadius, openScratch);
                freePlaced = !current.snapped;
                if (current.snapped) { activeNode = current.targetNode; activeConnector = current.targetConnector; }
                ApplyGhost();
                return true;
            }

            if (network.TryFlipSwitchNear(world, 1.6f)) return true;
            if (network.NearestOpenEnd(world, 2.2f, out TrackNode e2, out int c2))
            {
                activeNode = e2.id; activeConnector = c2;
                AudioManager.Sfx(AudioManager.Clips?.button);
                return true;
            }
            if (network.Graph.NearestPoint(world, 1f, out TrackNode hit, out _, out _))
            {
                network.Wiggle(hit.id);
                return true;
            }
            return false;
        }

        /// <summary>Elevated pieces sit 2 m up: test the tap against that level too.</summary>
        private bool NearestElevated(Vector2 screen, out TrackNode n)
        {
            n = null;
            return InputManager.ScreenToGround(cam, screen, TrackShapeLibrary.ElevatedHeight, out Vector3 w2)
                   && network.Graph.NearestPoint(w2, 1.2f, out n, out _, out _) && n.pose.position.y > 0.5f;
        }

        private static float Flat(Vector3 v) { v.y = 0f; return v.magnitude; }

        // ------------------------------------------------------------------------------------------------ drags
        public bool TryBeginDrag(Vector2 screen, bool longPress)
        {
            if (!Active || DeleteMode) return false;
            if (!InputManager.ScreenToGround(cam, screen, 0f, out Vector3 world)) return false;

            if (ghost != null && Selected.HasValue && !longPress)
            {
                Vector3 gc = current.pose.TransformPoint(TrackShapeLibrary.Get(Selected.Value).localCenter);
                if (Flat(gc - world) < tapGhostRadius) { draggingGhost = true; return true; }
                return false;
            }

            if (longPress && ghost == null && network.Graph.NearestPoint(world, 1.0f, out TrackNode n, out _, out _))
            {
                // Pick the piece up.
                moving = true;
                moveId = n.id;
                moveType = n.type;
                moveFrom = n.pose;
                moveSwitch = n.switchState;
                network.Remove(n.id);
                Selected = n.type;
                TrackPieceDefinition def = content.Track(n.type);
                ghost = new GhostView(def != null ? def.prefab : null, content.ghostMaterial, "Ghost_Move");
                if (def != null && def.accessory != null) ghost.Add(def.accessory, def.accessoryOffset, def.accessoryYaw);
                current = new SnapResult { pose = moveFrom, valid = true, targetNode = -1 };
                rotation = Mathf.RoundToInt(moveFrom.yaw / 45f);
                ApplyGhost();
                draggingGhost = true;
                AudioManager.Sfx(AudioManager.Clips?.button);
                StateChanged?.Invoke();
                return true;
            }
            return false;
        }

        public void Drag(Vector2 screen)
        {
            if (!draggingGhost || ghost == null || Selected == null) return;
            if (!InputManager.ScreenToGround(cam, screen, 0f, out Vector3 world)) return;
            // Lift the target a little above the finger so the child can see the piece.
            current = TrackSnapping.FindPlacement(network.Graph, TrackShapeLibrary.Get(Selected.Value), world, rotation, snapRadius, openScratch);
            freePlaced = !current.snapped;
            ApplyGhost();
        }

        public void EndDrag(Vector2 screen)
        {
            if (!draggingGhost) return;
            draggingGhost = false;
            if (moving)
            {
                moving = false;
                if (GhostValid)
                {
                    network.Place(moveType, current.pose, moveId, moveSwitch);
                    Commands.Push(new MoveTrackCommand(network, moveId, moveType, moveFrom, current.pose, moveSwitch));
                    AudioManager.Sfx(current.snapped ? AudioManager.Clips?.trackSnap : AudioManager.Clips?.trackPlace);
                }
                else
                {
                    network.Place(moveType, moveFrom, moveId, moveSwitch);
                    AudioManager.Sfx(AudioManager.Clips?.invalid);
                }
                Deselect();
                return;
            }
            if (current.snapped) { activeNode = current.targetNode; activeConnector = current.targetConnector; }
            Confirm();
        }

        public bool Undo()
        {
            if (Commands == null || !Commands.Undo()) return false;
            AudioManager.Sfx(AudioManager.Clips?.undo);
            return true;
        }

        public bool Redo()
        {
            if (Commands == null || !Commands.Redo()) return false;
            AudioManager.Sfx(AudioManager.Clips?.undo);
            return true;
        }
    }
}
