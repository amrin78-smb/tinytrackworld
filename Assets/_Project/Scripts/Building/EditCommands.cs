using System;
using System.Collections.Generic;
using TinyTracks.Decorations;
using TinyTracks.Tracks;
using UnityEngine;

namespace TinyTracks.Building
{
    public interface IEditCommand
    {
        void Do();
        void Undo();
    }

    /// <summary>Undo / redo history for every building and decorating action.</summary>
    public class CommandStack
    {
        public const int MaxHistory = 100;
        private readonly LinkedList<IEditCommand> undo = new LinkedList<IEditCommand>();
        private readonly Stack<IEditCommand> redo = new Stack<IEditCommand>();

        public event Action Changed;
        public bool CanUndo => undo.Count > 0;
        public bool CanRedo => redo.Count > 0;

        public void Execute(IEditCommand c)
        {
            c.Do();
            Push(c);
        }

        /// <summary>Records a command whose effect already happened (e.g. a drag that moved a piece).</summary>
        public void Push(IEditCommand c)
        {
            undo.AddLast(c);
            if (undo.Count > MaxHistory) undo.RemoveFirst();
            redo.Clear();
            Changed?.Invoke();
        }

        public bool Undo()
        {
            if (undo.Count == 0) return false;
            IEditCommand c = undo.Last.Value;
            undo.RemoveLast();
            c.Undo();
            redo.Push(c);
            Changed?.Invoke();
            return true;
        }

        public bool Redo()
        {
            if (redo.Count == 0) return false;
            IEditCommand c = redo.Pop();
            c.Do();
            undo.AddLast(c);
            Changed?.Invoke();
            return true;
        }

        public void Clear()
        {
            undo.Clear();
            redo.Clear();
            Changed?.Invoke();
        }
    }

    public sealed class AddTrackCommand : IEditCommand
    {
        private readonly TrackNetworkManager net;
        private readonly TrackType type;
        private readonly TrackPose pose;
        private readonly int switchState;
        public int Id { get; private set; }

        public AddTrackCommand(TrackNetworkManager net, TrackType type, TrackPose pose, int id = 0, int switchState = 0)
        {
            this.net = net; this.type = type; this.pose = pose; Id = id; this.switchState = switchState;
        }

        public void Do()
        {
            TrackNode n = net.Place(type, pose, Id, switchState);
            if (n != null) Id = n.id;
        }

        public void Undo() => net.Remove(Id);
    }

    public sealed class RemoveTrackCommand : IEditCommand
    {
        private readonly TrackNetworkManager net;
        private readonly int id;
        private TrackType type;
        private TrackPose pose;
        private int switchState;

        public RemoveTrackCommand(TrackNetworkManager net, int id) { this.net = net; this.id = id; }

        public void Do()
        {
            TrackNode n = net.Graph.Get(id);
            if (n == null) return;
            type = n.type; pose = n.pose; switchState = n.switchState;
            net.Remove(id);
        }

        public void Undo() => net.Place(type, pose, id, switchState);
    }

    public sealed class MoveTrackCommand : IEditCommand
    {
        private readonly TrackNetworkManager net;
        private readonly int id;
        private readonly TrackType type;
        private readonly TrackPose from, to;
        private readonly int switchState;

        public MoveTrackCommand(TrackNetworkManager net, int id, TrackType type, TrackPose from, TrackPose to, int switchState)
        {
            this.net = net; this.id = id; this.type = type; this.from = from; this.to = to; this.switchState = switchState;
        }

        public void Do() { net.Remove(id); net.Place(type, to, id, switchState); }
        public void Undo() { net.Remove(id); net.Place(type, from, id, switchState); }
    }

    public sealed class AddDecorationCommand : IEditCommand
    {
        private readonly DecorationManager deco;
        private readonly string defId;
        private readonly Vector3 pos;
        private readonly float yaw;
        public int Id { get; private set; }

        public AddDecorationCommand(DecorationManager deco, string defId, Vector3 pos, float yaw, int id = 0)
        {
            this.deco = deco; this.defId = defId; this.pos = pos; this.yaw = yaw; Id = id;
        }

        public void Do() => Id = deco.Place(defId, pos, yaw, Id);
        public void Undo() => deco.Remove(Id);
    }

    public sealed class RemoveDecorationCommand : IEditCommand
    {
        private readonly DecorationManager deco;
        private readonly int id;
        private PlacedDecoration saved;

        public RemoveDecorationCommand(DecorationManager deco, int id) { this.deco = deco; this.id = id; }

        public void Do()
        {
            PlacedDecoration p = deco.Get(id);
            if (p == null) return;
            saved = p;
            deco.Remove(id);
        }

        public void Undo() { if (saved != null) deco.Place(saved.defId, saved.position, saved.yaw, id); }
    }

    public sealed class MoveDecorationCommand : IEditCommand
    {
        private readonly DecorationManager deco;
        private readonly int id;
        private readonly Vector3 fromPos, toPos;
        private readonly float fromYaw, toYaw;

        public MoveDecorationCommand(DecorationManager deco, int id, Vector3 fromPos, float fromYaw, Vector3 toPos, float toYaw)
        {
            this.deco = deco; this.id = id; this.fromPos = fromPos; this.toPos = toPos; this.fromYaw = fromYaw; this.toYaw = toYaw;
        }

        public void Do() => deco.Move(id, toPos, toYaw);
        public void Undo() => deco.Move(id, fromPos, fromYaw);
    }

    /// <summary>Clears the whole railway and decorations (undoable).</summary>
    public sealed class ClearWorldCommand : IEditCommand
    {
        private readonly TrackNetworkManager net;
        private readonly DecorationManager deco;
        private readonly List<(int id, TrackType type, TrackPose pose, int sw)> tracks = new List<(int, TrackType, TrackPose, int)>();
        private readonly List<PlacedDecoration> decos = new List<PlacedDecoration>();

        public ClearWorldCommand(TrackNetworkManager net, DecorationManager deco) { this.net = net; this.deco = deco; }

        public void Do()
        {
            tracks.Clear();
            foreach (TrackNode n in net.Graph.Nodes.Values) tracks.Add((n.id, n.type, n.pose, n.switchState));
            decos.Clear();
            if (deco != null) decos.AddRange(deco.All);
            net.ClearAll();
            deco?.ClearAll();
        }

        public void Undo()
        {
            foreach (var t in tracks) net.Place(t.type, t.pose, t.id, t.sw);
            if (deco != null) foreach (PlacedDecoration d in decos) deco.Place(d.defId, d.position, d.yaw, d.id);
        }
    }
}
