using System.Collections.Generic;
using UnityEngine;

namespace TinyTracks.Tracks
{
    /// <summary>A candidate placement for a ghost piece.</summary>
    public struct SnapResult
    {
        public bool snapped;
        public TrackPose pose;
        public int targetNode;
        public int targetConnector;
        public int myConnector;
        public bool valid;
        public TrackGraph.AddResult reason;
    }

    /// <summary>
    /// Forgiving snapping: finds the open connector nearest the finger and computes the exact pose that mates the
    /// new piece to it. Poses come from connector data (yaw snapped to 45 degrees, millimetre-quantised position),
    /// so even long chains close loops exactly.
    /// </summary>
    public static class TrackSnapping
    {
        public const float DefaultSnapRadius = 3.5f;

        public static TrackPose PoseForAttachment(TrackShape shape, int myConnector, Vector3 targetPos, float targetHeading)
        {
            TrackConnector mine = shape.connectors[myConnector];
            float yaw = TrackMath.SnapYaw(targetHeading + 180f - mine.heading);
            Vector3 pos = targetPos - Quaternion.Euler(0f, yaw, 0f) * mine.position;
            return new TrackPose(pos, yaw);
        }

        /// <summary>Connectors of a shape that can be used to attach to something (not the far end of a buffer stop).</summary>
        public static int AttachableConnectorCount(TrackShape shape) =>
            TrackShapeLibrary.IsDeadEndPiece(shape.type) ? 1 : shape.connectors.Length;

        /// <summary>Pose that attaches the piece to a specific open end, using the rotation index to pick which of the
        /// piece's connectors meets it (the "rotate" button cycles this).</summary>
        public static SnapResult AttachTo(TrackGraph g, TrackShape shape, TrackNode target, int targetConnector, int rotation,
            ICollection<int> ignore = null)
        {
            int count = AttachableConnectorCount(shape);
            int mine = ((rotation % count) + count) % count;
            var r = new SnapResult
            {
                snapped = true,
                targetNode = target.id,
                targetConnector = targetConnector,
                myConnector = mine,
                pose = PoseForAttachment(shape, mine, target.worldConnectorPos[targetConnector], target.worldConnectorHeading[targetConnector]),
            };
            Evaluate(g, shape, ref r, ignore);
            return r;
        }

        /// <summary>
        /// Best placement near a world point: snaps to the closest open end within the radius; otherwise a free
        /// placement centred under the finger on the ground (yaw = rotation * 45).
        /// </summary>
        public static SnapResult FindPlacement(TrackGraph g, TrackShape shape, Vector3 point, int rotation, float snapRadius,
            List<(TrackNode, int)> openEndsScratch, ICollection<int> ignore = null)
        {
            g.OpenEnds(openEndsScratch);
            float best = snapRadius;
            TrackNode bestNode = null;
            int bestConn = -1;
            foreach ((TrackNode n, int c) in openEndsScratch)
            {
                if (ignore != null && ignore.Contains(n.id)) continue;
                Vector3 cp = n.worldConnectorPos[c];
                // Measure to a point slightly outside the end so the finger can be "where the new piece goes".
                Vector3 outward = cp + TrackMath.HeadingToDir(n.worldConnectorHeading[c]) * 1.5f;
                float d = Mathf.Min(Flat(cp - point), Flat(outward - point));
                if (d < best) { best = d; bestNode = n; bestConn = c; }
            }
            if (bestNode != null) return AttachTo(g, shape, bestNode, bestConn, rotation, ignore);

            float yaw = TrackMath.SnapYaw(rotation * 45f);
            Vector3 centre = Quaternion.Euler(0f, yaw, 0f) * shape.localCenter;
            float level = shape.type == TrackType.ElevatedStraight ? TrackShapeLibrary.ElevatedHeight : 0f;
            Vector3 pos = new Vector3(point.x, level, point.z) - centre;
            pos.x = Mathf.Round(pos.x * 2f) / 2f;
            pos.z = Mathf.Round(pos.z * 2f) / 2f;
            var free = new SnapResult { snapped = false, pose = new TrackPose(pos, yaw), targetNode = -1, targetConnector = -1 };
            Evaluate(g, shape, ref free, ignore);
            return free;
        }

        private static float Flat(Vector3 v) { v.y = 0f; return v.magnitude; }

        private static void Evaluate(TrackGraph g, TrackShape shape, ref SnapResult r, ICollection<int> ignore)
        {
            var probe = new TrackNode(0, shape.type, r.pose);
            if (g.IsDuplicate(probe)) { r.valid = false; r.reason = TrackGraph.AddResult.Duplicate; return; }
            if (g.Overlaps(probe, ignore)) { r.valid = false; r.reason = TrackGraph.AddResult.Overlap; return; }
            r.valid = true;
            r.reason = TrackGraph.AddResult.Ok;
        }
    }
}
