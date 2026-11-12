using System;
using System.Collections.Generic;
using UnityEngine;

namespace TinyTracks.Tracks
{
    /// <summary>Every track piece the game knows. Values are saved by name, so only append.</summary>
    public enum TrackType
    {
        Straight,
        ShortStraight,
        GentleLeft,
        GentleRight,
        TightLeft,
        TightRight,
        SCurveLeft,
        SCurveRight,
        JunctionLeft,
        JunctionRight,
        JunctionY,
        Cross,
        EndPiece,
        WoodenBridge,
        StoneBridge,
        Tunnel,
        Ramp,
        Station,
        Depot,
        Crossing,
        ElevatedStraight,
    }

    /// <summary>A connection point in a piece's local space. Heading points OUT of the piece (degrees, 0 = +Z, 90 = +X).</summary>
    [Serializable]
    public struct TrackConnector
    {
        public Vector3 position;
        public float heading;

        public TrackConnector(Vector3 position, float heading)
        {
            this.position = position;
            this.heading = TrackMath.NormalizeHeading(heading);
        }
    }

    /// <summary>
    /// One traversable route through a piece, from connector <see cref="from"/> to connector <see cref="to"/>,
    /// as a densely sampled polyline in local space with cumulative 3D arc length.
    /// </summary>
    public sealed class TrackPath
    {
        public readonly int from;
        public readonly int to;
        public readonly Vector3[] points;
        public readonly float[] cumulative;
        public float Length => cumulative[cumulative.Length - 1];

        public TrackPath(int from, int to, Vector3[] points)
        {
            this.from = from;
            this.to = to;
            this.points = points;
            cumulative = new float[points.Length];
            for (int i = 1; i < points.Length; i++) cumulative[i] = cumulative[i - 1] + Vector3.Distance(points[i - 1], points[i]);
        }

        /// <summary>Local position at arc distance s measured from the <see cref="from"/> end.</summary>
        public Vector3 Evaluate(float s)
        {
            if (s <= 0f) return points[0];
            int last = points.Length - 1;
            if (s >= cumulative[last]) return points[last];
            int lo = 0, hi = last;
            while (hi - lo > 1)
            {
                int mid = (lo + hi) >> 1;
                if (cumulative[mid] <= s) lo = mid; else hi = mid;
            }
            float seg = cumulative[hi] - cumulative[lo];
            float t = seg > 1e-6f ? (s - cumulative[lo]) / seg : 0f;
            return Vector3.LerpUnclamped(points[lo], points[hi], t);
        }

        public bool Touches(int connector) => from == connector || to == connector;
        public int Other(int connector) => connector == from ? to : from;
    }

    /// <summary>Immutable geometry of a track type: connectors + paths. Built by <see cref="TrackShapeLibrary"/>.</summary>
    public sealed class TrackShape
    {
        public readonly TrackType type;
        public readonly TrackConnector[] connectors;
        public readonly TrackPath[] paths;
        /// <summary>True when one connector leads to two paths (a switch the child can flip).</summary>
        public readonly bool isSwitch;
        public readonly Vector3 localCenter;
        public readonly float radius;

        public TrackShape(TrackType type, TrackConnector[] connectors, TrackPath[] paths)
        {
            this.type = type;
            this.connectors = connectors;
            this.paths = paths;
            var count = new int[connectors.Length];
            foreach (TrackPath p in paths) { count[p.from]++; count[p.to]++; }
            foreach (int c in count) if (c > 1) isSwitch = true;

            Vector3 min = new Vector3(float.MaxValue, float.MaxValue, float.MaxValue), max = -min;
            foreach (TrackPath p in paths)
            foreach (Vector3 v in p.points) { min = Vector3.Min(min, v); max = Vector3.Max(max, v); }
            localCenter = new Vector3((min.x + max.x) * 0.5f, 0f, (min.z + max.z) * 0.5f);
            float r = 0f;
            foreach (TrackPath p in paths)
            foreach (Vector3 v in p.points) r = Mathf.Max(r, new Vector2(v.x - localCenter.x, v.z - localCenter.z).magnitude);
            radius = r;
        }

        /// <summary>Paths that start or end at the given connector.</summary>
        public void PathsAt(int connector, List<int> result)
        {
            result.Clear();
            for (int i = 0; i < paths.Length; i++) if (paths[i].Touches(connector)) result.Add(i);
        }

        public int PathCountAt(int connector)
        {
            int n = 0;
            foreach (TrackPath p in paths) if (p.Touches(connector)) n++;
            return n;
        }
    }

    public static class TrackMath
    {
        public static float NormalizeHeading(float h)
        {
            h %= 360f;
            if (h < 0f) h += 360f;
            if (h >= 359.999f) h = 0f;
            return h;
        }

        /// <summary>Snaps a yaw to a multiple of 45 degrees: every connector heading is one, so this removes drift.</summary>
        public static float SnapYaw(float yaw) => NormalizeHeading(Mathf.Round(yaw / 45f) * 45f);

        public static Vector3 HeadingToDir(float heading)
        {
            float r = heading * Mathf.Deg2Rad;
            return new Vector3(Mathf.Sin(r), 0f, Mathf.Cos(r));
        }

        public static float AngleDiff(float a, float b) => Mathf.Abs(Mathf.DeltaAngle(a, b));

        /// <summary>Rounds a position to a millimetre so long chains of pieces cannot accumulate float error.</summary>
        public static Vector3 Quantize(Vector3 v) =>
            new Vector3(Mathf.Round(v.x * 1000f) / 1000f, Mathf.Round(v.y * 1000f) / 1000f, Mathf.Round(v.z * 1000f) / 1000f);
    }
}
