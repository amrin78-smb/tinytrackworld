using System.Collections.Generic;
using UnityEngine;

namespace TinyTracks.Tracks
{
    /// <summary>One path of one piece, traversed in a direction.</summary>
    public struct Span
    {
        public int node;
        public int path;
        public bool forward;
        public float length;

        public int ExitConnector(TrackGraph g) { TrackPath p = g.Get(node).shape.paths[path]; return forward ? p.to : p.from; }
        public int EntryConnector(TrackGraph g) { TrackPath p = g.Get(node).shape.paths[path]; return forward ? p.from : p.to; }

        /// <summary>World position at distance s from the span's entry, in travel direction.</summary>
        public Vector3 Point(TrackGraph g, float s)
        {
            TrackNode n = g.Get(node);
            TrackPath p = n.shape.paths[path];
            return n.pose.TransformPoint(p.Evaluate(forward ? s : p.Length - s));
        }
    }

    /// <summary>What lies ahead of the train within the look-ahead distance.</summary>
    public struct LookAhead
    {
        public float deadEndDistance;   // +inf if none found
        public float stationDistance;   // distance to the middle of the next station platform, +inf if none
        public int stationNode;
        public float crossingDistance;
        public int crossingNode;
    }

    /// <summary>
    /// The route a train occupies: a list of traversed spans (oldest first) plus the head position in the last span.
    /// The locomotive and every carriage are sampled at fixed distances behind the head, so carriages always follow
    /// the exact route the locomotive took (through junctions too) and never slide. Pure C#; tested in EditMode.
    /// </summary>
    public sealed class TrainSpine
    {
        private readonly List<Span> spans = new List<Span>();
        private readonly List<int> scratch = new List<int>();
        public float headS;

        public IReadOnlyList<Span> Spans => spans;
        public Span Head => spans[spans.Count - 1];
        public bool IsValid => spans.Count > 0;
        public float TotalTravelled { get; private set; }

        public void Clear() { spans.Clear(); headS = 0f; TotalTravelled = 0f; }

        /// <summary>Places the head on a path at s (measured from the path's 'from' end), facing forward or backward.</summary>
        public void Place(TrackGraph g, int node, int path, float s, bool forward)
        {
            spans.Clear();
            TrackPath p = g.Get(node).shape.paths[path];
            spans.Add(new Span { node = node, path = path, forward = forward, length = p.Length });
            headS = forward ? s : p.Length - s;
            TotalTravelled = 0f;
        }

        /// <summary>Fills the history behind the head (walking backwards through the graph) up to the given length.
        /// Returns how much track was actually available behind the head.</summary>
        public float ExtendBehind(TrackGraph g, float needed)
        {
            float have = headS;
            for (int i = spans.Count - 2; i >= 0; i--) have += spans[i].length;
            int guard = 0;
            while (have < needed && guard++ < 64)
            {
                Span first = spans[0];
                if (!PrevSpan(g, first, out Span prev)) break;
                spans.Insert(0, prev);
                have += prev.length;
            }
            return Mathf.Min(have, needed);
        }

        /// <summary>The next span after <paramref name="from"/> following links and switch states, or false at a dead end.</summary>
        public bool NextSpan(TrackGraph g, Span from, out Span next)
        {
            next = default;
            TrackNode n = g.Get(from.node);
            if (n == null) return false;
            int exit = from.ExitConnector(g);
            int nb = n.linkNode[exit];
            if (nb < 0) return false;
            TrackNode o = g.Get(nb);
            if (o == null) return false;
            int entry = n.linkConnector[exit];
            o.shape.PathsAt(entry, scratch);
            if (scratch.Count == 0) return false;
            int pick = scratch.Count == 1 ? scratch[0] : scratch[Mathf.Clamp(o.switchState, 0, scratch.Count - 1)];
            TrackPath tp = o.shape.paths[pick];
            next = new Span { node = nb, path = pick, forward = tp.from == entry, length = tp.Length };
            return true;
        }

        /// <summary>The span a train would have come from before <paramref name="to"/>.</summary>
        public bool PrevSpan(TrackGraph g, Span to, out Span prev)
        {
            prev = default;
            TrackNode n = g.Get(to.node);
            if (n == null) return false;
            int entry = to.EntryConnector(g);
            int nb = n.linkNode[entry];
            if (nb < 0) return false;
            TrackNode o = g.Get(nb);
            if (o == null) return false;
            int exit = n.linkConnector[entry];
            o.shape.PathsAt(exit, scratch);
            if (scratch.Count == 0) return false;
            int pick = scratch.Count == 1 ? scratch[0] : scratch[Mathf.Clamp(o.switchState, 0, scratch.Count - 1)];
            TrackPath tp = o.shape.paths[pick];
            prev = new Span { node = nb, path = pick, forward = tp.to == exit, length = tp.Length };
            return true;
        }

        /// <summary>Moves the head forward. Returns the distance actually moved (less than asked at a dead end).</summary>
        public float Advance(TrackGraph g, float distance, float keepBehind)
        {
            float moved = 0f;
            int guard = 0;
            while (distance > 0f && guard++ < 64)
            {
                Span h = Head;
                float room = h.length - headS;
                if (distance <= room)
                {
                    headS += distance;
                    moved += distance;
                    distance = 0f;
                    break;
                }
                if (!NextSpan(g, h, out Span next))
                {
                    moved += room;
                    headS = h.length;
                    break;
                }
                moved += room;
                distance -= room;
                spans.Add(next);
                headS = 0f;
            }
            TotalTravelled += moved;
            Trim(keepBehind);
            return moved;
        }

        /// <summary>Drops spans that are entirely further than keepBehind behind the head.</summary>
        public void Trim(float keepBehind)
        {
            float acc = headS;
            for (int i = spans.Count - 2; i >= 0; i--)
            {
                if (acc >= keepBehind) { spans.RemoveRange(0, i + 1); return; }
                acc += spans[i].length;
            }
        }

        /// <summary>World point at a distance behind the head (clamped to the oldest span's start).</summary>
        public Vector3 PointBehind(TrackGraph g, float behind)
        {
            float s = headS - behind;
            int i = spans.Count - 1;
            while (s < 0f && i > 0)
            {
                i--;
                s += spans[i].length;
            }
            if (s < 0f) s = 0f;
            return spans[i].Point(g, s);
        }

        /// <summary>World point ahead of the head along the currently set route (clamped at a dead end).</summary>
        public Vector3 PointAhead(TrackGraph g, float ahead)
        {
            Span cur = Head;
            float s = headS + ahead;
            int guard = 0;
            while (s > cur.length && guard++ < 16)
            {
                if (!NextSpan(g, cur, out Span next)) return cur.Point(g, cur.length);
                s -= cur.length;
                cur = next;
            }
            return cur.Point(g, s);
        }

        /// <summary>Looks along the route for dead ends, stations and level crossings.</summary>
        public LookAhead Scan(TrackGraph g, float maxDistance, int ignoreStation)
        {
            var la = new LookAhead
            {
                deadEndDistance = float.PositiveInfinity,
                stationDistance = float.PositiveInfinity,
                stationNode = -1,
                crossingDistance = float.PositiveInfinity,
                crossingNode = -1,
            };
            Span cur = Head;
            float dist = -headS; // distance from head to the start of cur
            int guard = 0;
            while (dist < maxDistance && guard++ < 32)
            {
                TrackNode n = g.Get(cur.node);
                if (n == null) { la.deadEndDistance = Mathf.Max(0f, dist); break; }
                if (n.type == TrackType.Station && n.id != ignoreStation && la.stationNode < 0)
                {
                    float mid = dist + cur.length * 0.5f;
                    if (mid >= -0.05f) { la.stationDistance = mid; la.stationNode = n.id; }
                }
                if (n.type == TrackType.Crossing && la.crossingNode < 0 && dist + cur.length >= 0f)
                {
                    la.crossingDistance = Mathf.Max(0f, dist + cur.length * 0.5f);
                    la.crossingNode = n.id;
                }
                if (!NextSpan(g, cur, out Span next)) { la.deadEndDistance = dist + cur.length; break; }
                dist += cur.length;
                cur = next;
            }
            return la;
        }

        /// <summary>Turns the train round: the point <paramref name="trainLength"/> behind the head becomes the new head.</summary>
        public void Reverse(TrackGraph g, float trainLength)
        {
            ExtendBehind(g, trainLength);
            float s = headS - trainLength;
            int i = spans.Count - 1;
            while (s < 0f && i > 0) { i--; s += spans[i].length; }
            if (s < 0f) s = 0f;
            var reversed = new List<Span>();
            for (int k = spans.Count - 1; k >= i; k--)
            {
                Span sp = spans[k];
                sp.forward = !sp.forward;
                reversed.Add(sp);
            }
            float newHeadS = spans[i].length - s;
            spans.Clear();
            spans.AddRange(reversed);
            headS = newHeadS;
        }

        /// <summary>True if any span under the train (within length behind the head) uses the node.</summary>
        public bool Occupies(int nodeId)
        {
            foreach (Span s in spans) if (s.node == nodeId) return true;
            return false;
        }

        /// <summary>True when every span still exists and is still linked to the next one.</summary>
        public bool IsIntact(TrackGraph g)
        {
            for (int i = 0; i < spans.Count; i++)
            {
                if (g.Get(spans[i].node) == null) return false;
                if (i == spans.Count - 1) break;
                if (!NextSpan(g, spans[i], out Span next) || next.node != spans[i + 1].node)
                {
                    // A switch may have been flipped behind the loco; that is fine as long as the pieces stay linked.
                    TrackNode n = g.Get(spans[i].node);
                    if (n.linkNode[spans[i].ExitConnector(g)] != spans[i + 1].node) return false;
                }
            }
            return true;
        }
    }
}
