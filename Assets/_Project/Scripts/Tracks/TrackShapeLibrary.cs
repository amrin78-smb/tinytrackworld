using System;
using System.Collections.Generic;
using UnityEngine;

namespace TinyTracks.Tracks
{
    /// <summary>
    /// The single source of truth for track geometry. Unity uses it for the railway graph and train movement; the
    /// editor exports it (sampled) to Tools/blender/track_shapes.json so the Blender track models match exactly.
    /// Local space: entry connector 0 at the origin pointing -Z (out of the piece); the track runs along +Z.
    /// </summary>
    public static class TrackShapeLibrary
    {
        public const float StraightLength = 4f;
        public const float ShortLength = 2f;
        public const float TightRadius = 4f;
        public const float GentleRadius = 8f;
        public const float SCurveRadius = 5f;
        public const float SCurveAngle = 36.8698976f; // 2*atan(1/3): forward 6 m, sideways 2 m
        public const float BridgeLength = 8f;
        public const float BridgeHump = 0.8f;
        public const float TunnelLength = 6f;
        public const float RampLength = 8f;
        public const float ElevatedHeight = 2f;
        public const float StationLength = 6f;
        public const float EndLength = 1f;
        public const float DepotLength = 4f;
        public const float SampleStep = 0.1f;

        private static Dictionary<TrackType, TrackShape> shapes;

        public static TrackShape Get(TrackType type)
        {
            if (shapes == null) Build();
            return shapes[type];
        }

        public static IEnumerable<TrackType> AllTypes => (TrackType[])Enum.GetValues(typeof(TrackType));

        private static void Build()
        {
            shapes = new Dictionary<TrackType, TrackShape>();
            Add(Simple(TrackType.Straight, new PathBuilder().Straight(StraightLength)));
            Add(Simple(TrackType.ShortStraight, new PathBuilder().Straight(ShortLength)));
            Add(Simple(TrackType.ElevatedStraight, new PathBuilder().Straight(StraightLength)));
            Add(Simple(TrackType.GentleLeft, new PathBuilder().Turn(GentleRadius, -45f)));
            Add(Simple(TrackType.GentleRight, new PathBuilder().Turn(GentleRadius, 45f)));
            Add(Simple(TrackType.TightLeft, new PathBuilder().Turn(TightRadius, -90f)));
            Add(Simple(TrackType.TightRight, new PathBuilder().Turn(TightRadius, 90f)));
            Add(Simple(TrackType.SCurveLeft, new PathBuilder().Turn(SCurveRadius, -SCurveAngle).Turn(SCurveRadius, SCurveAngle)));
            Add(Simple(TrackType.SCurveRight, new PathBuilder().Turn(SCurveRadius, SCurveAngle).Turn(SCurveRadius, -SCurveAngle)));
            Add(Simple(TrackType.WoodenBridge, new PathBuilder().Straight(BridgeLength).Hump(BridgeHump)));
            Add(Simple(TrackType.StoneBridge, new PathBuilder().Straight(BridgeLength).Hump(BridgeHump)));
            Add(Simple(TrackType.Tunnel, new PathBuilder().Straight(TunnelLength)));
            Add(Simple(TrackType.Ramp, new PathBuilder().Straight(RampLength).Rise(ElevatedHeight)));
            Add(Simple(TrackType.Station, new PathBuilder().Straight(StationLength)));
            Add(Simple(TrackType.CargoStation, new PathBuilder().Straight(StationLength)));
            Add(Simple(TrackType.Crossing, new PathBuilder().Straight(StraightLength)));
            Add(Simple(TrackType.EndPiece, new PathBuilder().Straight(EndLength), deadEnd: true));
            Add(Simple(TrackType.Depot, new PathBuilder().Straight(DepotLength), deadEnd: true));

            Add(Multi(TrackType.JunctionRight, new PathBuilder().Straight(StraightLength), new PathBuilder().Turn(TightRadius, 90f)));
            Add(Multi(TrackType.JunctionLeft, new PathBuilder().Straight(StraightLength), new PathBuilder().Turn(TightRadius, -90f)));
            Add(Multi(TrackType.JunctionY, new PathBuilder().Turn(GentleRadius, -45f), new PathBuilder().Turn(GentleRadius, 45f)));

            // Cross: two straights through the centre at right angles.
            var cross = new List<TrackConnector>
            {
                new TrackConnector(Vector3.zero, 180f),
                new TrackConnector(new Vector3(0f, 0f, StraightLength), 0f),
                new TrackConnector(new Vector3(-StraightLength / 2f, 0f, StraightLength / 2f), 270f),
                new TrackConnector(new Vector3(StraightLength / 2f, 0f, StraightLength / 2f), 90f),
            };
            Vector3[] a = new PathBuilder().Straight(StraightLength).Points();
            Vector3[] b = new PathBuilder(new Vector3(-StraightLength / 2f, 0f, StraightLength / 2f), 90f).Straight(StraightLength).Points();
            Add(new TrackShape(TrackType.Cross, cross.ToArray(), new[] { new TrackPath(0, 1, a), new TrackPath(2, 3, b) }));
        }

        private static void Add(TrackShape s) => shapes[s.type] = s;

        private static TrackShape Simple(TrackType type, PathBuilder p, bool deadEnd = false)
        {
            Vector3[] pts = p.Points();
            if (deadEnd)
            {
                // A buffer stop: one connector. The path ends inside the piece; reaching its end is a dead end.
                var conns = new[] { new TrackConnector(pts[0], 180f), new TrackConnector(pts[pts.Length - 1], p.Heading) };
                return new TrackShape(type, conns, new[] { new TrackPath(0, 1, pts) }) ;
            }
            return new TrackShape(type,
                new[] { new TrackConnector(pts[0], 180f), new TrackConnector(Snap(pts[pts.Length - 1]), p.Heading) },
                new[] { new TrackPath(0, 1, pts) });
        }

        /// <summary>Several paths sharing entry connector 0 (switches).</summary>
        private static TrackShape Multi(TrackType type, params PathBuilder[] builders)
        {
            var conns = new List<TrackConnector> { new TrackConnector(Vector3.zero, 180f) };
            var paths = new List<TrackPath>();
            foreach (PathBuilder b in builders)
            {
                Vector3[] pts = b.Points();
                conns.Add(new TrackConnector(Snap(pts[pts.Length - 1]), b.Heading));
                paths.Add(new TrackPath(0, conns.Count - 1, pts));
            }
            return new TrackShape(type, conns.ToArray(), paths.ToArray());
        }

        private static Vector3 Snap(Vector3 v) => TrackMath.Quantize(v);

        /// <summary>True for pieces whose far connector is not a real connection point (buffer stops).</summary>
        public static bool IsDeadEndPiece(TrackType t) => t == TrackType.EndPiece || t == TrackType.Depot;

        /// <summary>Pieces where a train stops for a moment (passengers at stations, cargo at the cargo yard).</summary>
        public static bool IsStop(TrackType t) => t == TrackType.Station || t == TrackType.CargoStation;

        /// <summary>Connector indices a neighbour may attach to (dead-end pieces only connect at their entry).</summary>
        public static bool IsConnectable(TrackType t, int connector) => !IsDeadEndPiece(t) || connector == 0;

        /// <summary>Builds a planar route from straight and arc primitives, with an optional vertical profile.</summary>
        private sealed class PathBuilder
        {
            private readonly List<Vector3> pts = new List<Vector3>();
            private Vector3 pos;
            public float Heading { get; private set; }
            private float hump, rise;

            public PathBuilder() : this(Vector3.zero, 0f) { }

            public PathBuilder(Vector3 start, float heading)
            {
                pos = start;
                Heading = heading;
                pts.Add(pos);
            }

            public PathBuilder Straight(float length)
            {
                int n = Mathf.Max(1, Mathf.CeilToInt(length / SampleStep));
                Vector3 dir = TrackMath.HeadingToDir(Heading);
                Vector3 start = pos;
                for (int i = 1; i <= n; i++) pts.Add(start + dir * (length * i / n));
                pos = start + dir * length;
                return this;
            }

            /// <summary>Arc of the given radius; positive degrees turn right (clockwise seen from above).</summary>
            public PathBuilder Turn(float radius, float degrees)
            {
                float sign = Mathf.Sign(degrees);
                Vector3 right = TrackMath.HeadingToDir(Heading + 90f);
                Vector3 centre = pos + right * (radius * sign);
                float length = radius * Mathf.Abs(degrees) * Mathf.Deg2Rad;
                int n = Mathf.Max(2, Mathf.CeilToInt(length / SampleStep));
                float startHeading = Heading;
                for (int i = 1; i <= n; i++)
                {
                    float h = startHeading + degrees * i / n;
                    // Position on the circle: centre minus the "right" vector of the current heading.
                    Vector3 p = centre - TrackMath.HeadingToDir(h + 90f) * (radius * sign);
                    pts.Add(p);
                }
                Heading = TrackMath.NormalizeHeading(startHeading + degrees);
                pos = pts[pts.Count - 1];
                return this;
            }

            /// <summary>Smooth arch (bridge): height follows sin over the whole path.</summary>
            public PathBuilder Hump(float height) { hump = height; return this; }

            /// <summary>Smoothstep rise over the whole path (ramp).</summary>
            public PathBuilder Rise(float height) { rise = height; return this; }

            public Vector3[] Points()
            {
                var result = pts.ToArray();
                if (hump == 0f && rise == 0f) return result;
                float total = 0f;
                for (int i = 1; i < result.Length; i++) total += Vector3.Distance(result[i - 1], result[i]);
                float acc = 0f;
                for (int i = 0; i < result.Length; i++)
                {
                    if (i > 0) acc += Vector3.Distance(pts[i - 1], pts[i]);
                    float t = total > 0f ? acc / total : 0f;
                    float y = 0f;
                    if (hump != 0f) y += hump * Mathf.Sin(Mathf.PI * t);
                    if (rise != 0f) y += rise * t * t * (3f - 2f * t);
                    result[i].y += y;
                }
                return result;
            }
        }
    }
}
