using System;
using System.Collections.Generic;
using UnityEngine;

namespace TinyTracks.Tracks
{
    /// <summary>Where a piece sits: position (Y = elevation) and yaw in multiples of 45 degrees.</summary>
    [Serializable]
    public struct TrackPose : IEquatable<TrackPose>
    {
        public Vector3 position;
        public float yaw;

        public TrackPose(Vector3 position, float yaw)
        {
            this.position = TrackMath.Quantize(position);
            this.yaw = TrackMath.SnapYaw(yaw);
        }

        public Quaternion Rotation => Quaternion.Euler(0f, yaw, 0f);
        public Vector3 TransformPoint(Vector3 local) => position + Rotation * local;
        public Vector3 InverseTransformPoint(Vector3 world) => Quaternion.Inverse(Rotation) * (world - position);
        public float TransformHeading(float local) => TrackMath.NormalizeHeading(local + yaw);

        public bool Equals(TrackPose o) => (position - o.position).sqrMagnitude < 1e-4f && TrackMath.AngleDiff(yaw, o.yaw) < 0.5f;
        public override bool Equals(object obj) => obj is TrackPose p && Equals(p);
        public override int GetHashCode() => position.GetHashCode() ^ yaw.GetHashCode();
    }

    /// <summary>One piece in the railway graph (a node). Links are the edges to neighbouring pieces.</summary>
    public sealed class TrackNode
    {
        public readonly int id;
        public readonly TrackType type;
        public readonly TrackShape shape;
        public readonly TrackPose pose;
        public readonly Vector3[] worldConnectorPos;
        public readonly float[] worldConnectorHeading;
        /// <summary>Per connector: neighbour node id or -1 (open end).</summary>
        public readonly int[] linkNode;
        /// <summary>Per connector: the neighbour's connector index.</summary>
        public readonly int[] linkConnector;
        /// <summary>For switches: index into the paths at connector 0 that a train takes when entering there.</summary>
        public int switchState;

        public TrackNode(int id, TrackType type, TrackPose pose)
        {
            this.id = id;
            this.type = type;
            this.pose = pose;
            shape = TrackShapeLibrary.Get(type);
            int n = shape.connectors.Length;
            worldConnectorPos = new Vector3[n];
            worldConnectorHeading = new float[n];
            linkNode = new int[n];
            linkConnector = new int[n];
            for (int i = 0; i < n; i++)
            {
                worldConnectorPos[i] = TrackMath.Quantize(pose.TransformPoint(shape.connectors[i].position));
                worldConnectorHeading[i] = pose.TransformHeading(shape.connectors[i].heading);
                linkNode[i] = -1;
                linkConnector[i] = -1;
            }
        }

        public bool IsConnectable(int connector) => TrackShapeLibrary.IsConnectable(type, connector);
        public bool IsOpen(int connector) => IsConnectable(connector) && linkNode[connector] < 0;

        public Vector3 WorldPoint(int path, float s) => pose.TransformPoint(shape.paths[path].Evaluate(s));
    }

    /// <summary>
    /// The railway network: pieces are nodes, matching connectors are edges. Pure C# (no scene dependency) so it is
    /// fully covered by EditMode tests. Connections are always reconstructable from (type, pose), which is what the
    /// save file stores.
    /// </summary>
    public sealed class TrackGraph
    {
        public const float ConnectTolerance = 0.15f;
        public const float HeadingTolerance = 5f;
        public const float BedHalfWidth = 0.5f;
        /// <summary>Two track beds closer than this (horizontally) overlap unless they are at different levels.</summary>
        public const float OverlapDistance = 0.95f;
        public const float VerticalClearance = 1.6f;

        private readonly Dictionary<int, TrackNode> nodes = new Dictionary<int, TrackNode>();
        private int nextId = 1;

        public event Action<TrackNode> NodeAdded;
        public event Action<TrackNode> NodeRemoved;
        public event Action Changed;

        public IReadOnlyDictionary<int, TrackNode> Nodes => nodes;
        public int Count => nodes.Count;

        public TrackNode Get(int id) => nodes.TryGetValue(id, out TrackNode n) ? n : null;

        public enum AddResult { Ok, Duplicate, Overlap }

        /// <summary>Adds a piece and links every connector that meets an open neighbour connector.</summary>
        public TrackNode Add(TrackType type, TrackPose pose, int forcedId = 0, bool allowOverlap = true)
        {
            return TryAdd(type, pose, out _, forcedId, allowOverlap);
        }

        public TrackNode TryAdd(TrackType type, TrackPose pose, out AddResult result, int forcedId = 0, bool allowOverlap = true)
        {
            var probe = new TrackNode(0, type, pose);
            if (IsDuplicate(probe)) { result = AddResult.Duplicate; return null; }
            if (!allowOverlap && Overlaps(probe, null)) { result = AddResult.Overlap; return null; }

            int id = forcedId > 0 ? forcedId : nextId;
            if (nodes.ContainsKey(id)) id = nextId;
            nextId = Mathf.Max(nextId, id + 1);
            var node = new TrackNode(id, type, pose);
            nodes.Add(id, node);
            LinkNode(node);
            result = AddResult.Ok;
            NodeAdded?.Invoke(node);
            Changed?.Invoke();
            return node;
        }

        public bool Remove(int id)
        {
            if (!nodes.TryGetValue(id, out TrackNode node)) return false;
            for (int c = 0; c < node.linkNode.Length; c++)
            {
                if (node.linkNode[c] < 0) continue;
                TrackNode other = nodes[node.linkNode[c]];
                int oc = node.linkConnector[c];
                other.linkNode[oc] = -1;
                other.linkConnector[oc] = -1;
            }
            nodes.Remove(id);
            NodeRemoved?.Invoke(node);
            Changed?.Invoke();
            return true;
        }

        public void Clear()
        {
            var ids = new List<int>(nodes.Keys);
            foreach (int id in ids)
            {
                TrackNode n = nodes[id];
                nodes.Remove(id);
                NodeRemoved?.Invoke(n);
            }
            nextId = 1;
            Changed?.Invoke();
        }

        /// <summary>Drops all links and recomputes them from geometry (used after load and by tests).</summary>
        public void RebuildLinks()
        {
            foreach (TrackNode n in nodes.Values)
                for (int c = 0; c < n.linkNode.Length; c++) { n.linkNode[c] = -1; n.linkConnector[c] = -1; }
            foreach (TrackNode n in nodes.Values) LinkNode(n);
            Changed?.Invoke();
        }

        public void SetSwitch(int id, int state)
        {
            TrackNode n = Get(id);
            if (n == null || !n.shape.isSwitch) return;
            n.switchState = Mathf.Clamp(state, 0, n.shape.PathCountAt(0) - 1);
            Changed?.Invoke();
        }

        public void ToggleSwitch(int id)
        {
            TrackNode n = Get(id);
            if (n == null || !n.shape.isSwitch) return;
            n.switchState = (n.switchState + 1) % n.shape.PathCountAt(0);
            Changed?.Invoke();
        }

        private void LinkNode(TrackNode node)
        {
            for (int c = 0; c < node.worldConnectorPos.Length; c++)
            {
                if (!node.IsOpen(c)) continue;
                if (FindMate(node.worldConnectorPos[c], node.worldConnectorHeading[c], node.id, out TrackNode other, out int oc))
                {
                    node.linkNode[c] = other.id;
                    node.linkConnector[c] = oc;
                    other.linkNode[oc] = node.id;
                    other.linkConnector[oc] = c;
                }
            }
        }

        /// <summary>Finds an OPEN connector on another piece that meets this one (same place, facing the opposite way).</summary>
        public bool FindMate(Vector3 pos, float heading, int excludeId, out TrackNode mate, out int mateConnector)
        {
            mate = null;
            mateConnector = -1;
            float best = ConnectTolerance;
            foreach (TrackNode n in nodes.Values)
            {
                if (n.id == excludeId) continue;
                for (int c = 0; c < n.worldConnectorPos.Length; c++)
                {
                    if (!n.IsOpen(c)) continue;
                    float d = Vector3.Distance(n.worldConnectorPos[c], pos);
                    if (d > best) continue;
                    if (TrackMath.AngleDiff(n.worldConnectorHeading[c], heading + 180f) > HeadingTolerance) continue;
                    best = d;
                    mate = n;
                    mateConnector = c;
                }
            }
            return mate != null;
        }

        /// <summary>A piece of the same type at the same pose already exists (or a straight laid exactly over another).</summary>
        public bool IsDuplicate(TrackNode probe)
        {
            foreach (TrackNode n in nodes.Values)
            {
                if (n.type == probe.type && n.pose.Equals(probe.pose)) return true;
                // Same footprint reversed (a straight placed backwards on top of itself).
                if (n.shape.connectors.Length == probe.shape.connectors.Length && SameConnectorSet(n, probe)) return true;
            }
            return false;
        }

        private static bool SameConnectorSet(TrackNode a, TrackNode b)
        {
            if (a.type != b.type) return false;
            for (int i = 0; i < a.worldConnectorPos.Length; i++)
            {
                bool found = false;
                for (int j = 0; j < b.worldConnectorPos.Length && !found; j++)
                    found = Vector3.Distance(a.worldConnectorPos[i], b.worldConnectorPos[j]) < ConnectTolerance &&
                            TrackMath.AngleDiff(a.worldConnectorHeading[i], b.worldConnectorHeading[j]) < HeadingTolerance;
                if (!found) return false;
            }
            return true;
        }

        /// <summary>
        /// True when the probe's track bed runs into another piece's bed at the same level. Samples within a bed
        /// length of a connector that mates (or will mate) are ignored, so neighbours may touch end to end.
        /// </summary>
        public bool Overlaps(TrackNode probe, ICollection<int> ignoreIds)
        {
            foreach (TrackNode n in nodes.Values)
            {
                if (ignoreIds != null && ignoreIds.Contains(n.id)) continue;
                if (n.id == probe.id) continue;
                Vector3 d = n.pose.TransformPoint(n.shape.localCenter) - probe.pose.TransformPoint(probe.shape.localCenter);
                d.y = 0f;
                if (d.magnitude > n.shape.radius + probe.shape.radius + OverlapDistance) continue;
                if (PiecesOverlap(probe, n)) return true;
            }
            return false;
        }

        private static bool PiecesOverlap(TrackNode a, TrackNode b)
        {
            for (int pa = 0; pa < a.shape.paths.Length; pa++)
            {
                Vector3[] ptsA = a.shape.paths[pa].points;
                for (int i = 0; i < ptsA.Length; i += 2)
                {
                    Vector3 wa = a.pose.TransformPoint(ptsA[i]);
                    if (NearSharedConnector(a, b, wa)) continue;
                    for (int pb = 0; pb < b.shape.paths.Length; pb++)
                    {
                        Vector3[] ptsB = b.shape.paths[pb].points;
                        for (int j = 0; j < ptsB.Length; j += 2)
                        {
                            Vector3 wb = b.pose.TransformPoint(ptsB[j]);
                            if (Mathf.Abs(wa.y - wb.y) >= VerticalClearance) continue;
                            float dx = wa.x - wb.x, dz = wa.z - wb.z;
                            if (dx * dx + dz * dz < OverlapDistance * OverlapDistance && !NearSharedConnector(b, a, wb)) return true;
                        }
                    }
                }
            }
            return false;
        }

        /// <summary>Point is within one bed-width of a connector of <paramref name="self"/> that touches a connector of <paramref name="other"/>.</summary>
        private static bool NearSharedConnector(TrackNode self, TrackNode other, Vector3 p)
        {
            for (int c = 0; c < self.worldConnectorPos.Length; c++)
            {
                Vector3 cp = self.worldConnectorPos[c];
                bool touching = false;
                for (int k = 0; k < other.worldConnectorPos.Length && !touching; k++)
                    touching = Vector3.Distance(cp, other.worldConnectorPos[k]) < ConnectTolerance;
                if (!touching) continue;
                if ((p - cp).sqrMagnitude < 1.1f * 1.1f) return true;
            }
            return false;
        }

        // ------------------------------------------------------------------------------------------------ queries

        /// <summary>All connectors that are open (no neighbour).</summary>
        public void OpenEnds(List<(TrackNode node, int connector)> result)
        {
            result.Clear();
            foreach (TrackNode n in nodes.Values)
                for (int c = 0; c < n.linkNode.Length; c++)
                    if (n.IsOpen(c)) result.Add((n, c));
        }

        /// <summary>Number of separate railway networks (connected components).</summary>
        public int CountNetworks()
        {
            var seen = new HashSet<int>();
            var stack = new Stack<int>();
            int count = 0;
            foreach (int start in nodes.Keys)
            {
                if (!seen.Add(start)) continue;
                count++;
                stack.Push(start);
                while (stack.Count > 0)
                {
                    TrackNode n = nodes[stack.Pop()];
                    foreach (int l in n.linkNode) if (l >= 0 && seen.Add(l)) stack.Push(l);
                }
            }
            return count;
        }

        /// <summary>Nearest point on any track path to a world position (for placing trains and tapping switches).</summary>
        public bool NearestPoint(Vector3 world, float maxDistance, out TrackNode node, out int path, out float s)
        {
            node = null; path = -1; s = 0f;
            float best = maxDistance * maxDistance;
            foreach (TrackNode n in nodes.Values)
            {
                Vector3 local = n.pose.InverseTransformPoint(world);
                Vector2 lc = new Vector2(local.x - n.shape.localCenter.x, local.z - n.shape.localCenter.z);
                if (lc.magnitude > n.shape.radius + maxDistance) continue;
                for (int p = 0; p < n.shape.paths.Length; p++)
                {
                    TrackPath tp = n.shape.paths[p];
                    for (int i = 0; i < tp.points.Length; i++)
                    {
                        float dx = tp.points[i].x - local.x, dz = tp.points[i].z - local.z;
                        float d2 = dx * dx + dz * dz;
                        if (d2 < best) { best = d2; node = n; path = p; s = tp.cumulative[i]; }
                    }
                }
            }
            return node != null;
        }

        /// <summary>Validation report used by tests, the debug overlay and the build-mode hints.</summary>
        public TrackValidationReport Validate()
        {
            var r = new TrackValidationReport();
            var open = new List<(TrackNode, int)>();
            OpenEnds(open);
            r.openEnds = open.Count;
            r.networks = CountNetworks();
            foreach (TrackNode n in nodes.Values)
            {
                for (int c = 0; c < n.linkNode.Length; c++)
                {
                    int l = n.linkNode[c];
                    if (l < 0) continue;
                    TrackNode o = Get(l);
                    if (o == null || o.linkNode[n.linkConnector[c]] != n.id || o.linkConnector[n.linkConnector[c]] != c) r.brokenLinks++;
                    else if (Vector3.Distance(n.worldConnectorPos[c], o.worldConnectorPos[n.linkConnector[c]]) > ConnectTolerance) r.brokenLinks++;
                    for (int c2 = c + 1; c2 < n.linkNode.Length; c2++)
                        if (n.linkNode[c2] == l && n.linkConnector[c2] == n.linkConnector[c]) r.duplicateLinks++;
                }
                if (n.shape.isSwitch && (n.switchState < 0 || n.switchState >= n.shape.PathCountAt(0))) r.invalidSwitches++;
                if (Overlaps(n, null)) r.overlaps++;
            }
            r.overlaps /= 2;
            return r;
        }
    }

    public struct TrackValidationReport
    {
        public int openEnds;
        public int networks;
        public int brokenLinks;
        public int duplicateLinks;
        public int invalidSwitches;
        public int overlaps;
        public bool IsConsistent => brokenLinks == 0 && duplicateLinks == 0 && invalidSwitches == 0;
        public override string ToString() =>
            $"open={openEnds} networks={networks} broken={brokenLinks} dupLinks={duplicateLinks} badSwitch={invalidSwitches} overlaps={overlaps}";
    }
}
