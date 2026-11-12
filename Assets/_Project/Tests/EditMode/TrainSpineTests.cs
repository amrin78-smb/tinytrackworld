using System.Collections.Generic;
using NUnit.Framework;
using TinyTracks.Tracks;
using UnityEngine;
using static TinyTracks.Tests.TrackGraphTests;

namespace TinyTracks.Tests
{
    public class TrainSpineTests
    {
        private static TrackGraph Oval(out List<TrackNode> pieces)
        {
            var g = new TrackGraph();
            pieces = new List<TrackNode>();
            TrackNode cur = g.Add(TrackType.Straight, new TrackPose(Vector3.zero, 0f));
            pieces.Add(cur);
            TrackType[] seq = { TrackType.Straight, TrackType.TightRight, TrackType.TightRight, TrackType.Straight,
                                TrackType.Straight, TrackType.TightRight, TrackType.TightRight };
            foreach (TrackType t in seq) { cur = Extend(g, cur, 1, t); pieces.Add(cur); }
            return g;
        }

        private static float LoopLength(List<TrackNode> pieces)
        {
            float l = 0f;
            foreach (TrackNode n in pieces) l += n.shape.paths[0].Length;
            return l;
        }

        [Test]
        public void Locomotive_CompletesClosedLoop_Smoothly()
        {
            TrackGraph g = Oval(out var pieces);
            var spine = new TrainSpine();
            spine.Place(g, pieces[0].id, 0, 0f, true);
            float loop = LoopLength(pieces);
            Vector3 start = spine.PointBehind(g, 0f);
            Vector3 prev = start;
            float step = 0.05f;
            var visited = new HashSet<int>();
            for (float d = 0f; d < loop - 1e-3f; d += step)
            {
                float moved = spine.Advance(g, step, 10f);
                Assert.That(moved, Is.EqualTo(step).Within(1e-4), "train stopped on a closed loop");
                Vector3 p = spine.PointBehind(g, 0f);
                // Continuous: no jump bigger than the step (allowing chord shortening on curves).
                Assert.LessOrEqual(Vector3.Distance(prev, p), step + 1e-3f, "position jumped at " + d);
                prev = p;
                visited.Add(spine.Head.node);
            }
            Assert.AreEqual(pieces.Count, visited.Count, "did not visit every piece");
            Assert.That(Vector3.Distance(start, spine.PointBehind(g, 0f)), Is.LessThan(0.06f), "did not return to start");
            Assert.That(spine.TotalTravelled, Is.EqualTo(loop).Within(0.06f));
        }

        [Test]
        public void Loop_CanBeTravelledBackwards()
        {
            TrackGraph g = Oval(out var pieces);
            var spine = new TrainSpine();
            spine.Place(g, pieces[3].id, 0, 1f, false);
            float loop = LoopLength(pieces);
            Assert.That(spine.Advance(g, loop * 2f, 10f), Is.EqualTo(loop * 2f).Within(1e-3));
        }

        [Test]
        public void DeadEnd_StopsTrainSafely()
        {
            var g = new TrackGraph();
            TrackNode a = g.Add(TrackType.Straight, new TrackPose(Vector3.zero, 0f));
            Extend(g, a, 1, TrackType.TightLeft);
            var spine = new TrainSpine();
            spine.Place(g, a.id, 0, 0f, true);
            LookAhead la = spine.Scan(g, 50f, -1);
            float total = 4f + TrackShapeLibrary.TightRadius * Mathf.PI / 2f;
            Assert.That(la.deadEndDistance, Is.EqualTo(total).Within(0.01));
            float moved = spine.Advance(g, 100f, 10f);
            Assert.That(moved, Is.EqualTo(total).Within(0.01), "train must stop exactly at the end, never beyond");
            Assert.That(spine.Advance(g, 1f, 10f), Is.EqualTo(0f).Within(1e-5));
        }

        [Test]
        public void BufferStop_IsADeadEnd()
        {
            var g = new TrackGraph();
            TrackNode a = g.Add(TrackType.Straight, new TrackPose(Vector3.zero, 0f));
            Extend(g, a, 1, TrackType.EndPiece);
            var spine = new TrainSpine();
            spine.Place(g, a.id, 0, 0f, true);
            Assert.That(spine.Scan(g, 50f, -1).deadEndDistance, Is.EqualTo(4f + TrackShapeLibrary.EndLength).Within(0.01));
        }

        [Test]
        public void Junction_FollowsSwitchState_AndTrailsThrough()
        {
            var g = new TrackGraph();
            TrackNode j = g.Add(TrackType.JunctionRight, new TrackPose(Vector3.zero, 0f));
            TrackNode straight = Extend(g, j, 1, TrackType.Straight);
            TrackNode branch = Extend(g, j, 2, TrackType.Straight);
            var spine = new TrainSpine();

            spine.Place(g, j.id, 0, 0f, true);
            spine.Advance(g, 5f, 10f);
            Assert.AreEqual(straight.id, spine.Head.node, "default switch state is the straight route");

            g.ToggleSwitch(j.id);
            spine.Place(g, j.id, 1, 0f, true);
            spine.Advance(g, TrackShapeLibrary.TightRadius * Mathf.PI / 2f + 1f, 10f);
            Assert.AreEqual(branch.id, spine.Head.node, "flipped switch takes the branch");

            // Trailing move from the branch back through the junction must come out at connector 0's side.
            spine.Place(g, branch.id, 0, 2f, false);
            float moved = spine.Advance(g, 20f, 10f);
            Assert.That(moved, Is.EqualTo(2f + TrackShapeLibrary.TightRadius * Mathf.PI / 2f).Within(0.01));
        }

        [Test]
        public void Carriages_FollowTheRouteTheLocoTook()
        {
            var g = new TrackGraph();
            TrackNode a = g.Add(TrackType.Straight, new TrackPose(Vector3.zero, 0f));
            TrackNode j = Extend(g, a, 1, TrackType.JunctionRight);
            Extend(g, j, 1, TrackType.Straight);
            TrackNode branch = Extend(g, j, 2, TrackType.Straight);
            g.ToggleSwitch(j.id);

            var spine = new TrainSpine();
            spine.Place(g, a.id, 0, 3f, true);
            spine.ExtendBehind(g, 4f);
            spine.Advance(g, 1f + TrackShapeLibrary.TightRadius * Mathf.PI / 2f + 2f, 12f);
            Assert.AreEqual(branch.id, spine.Head.node);
            g.ToggleSwitch(j.id); // child flips the switch while the carriages are still on it

            Vector3 behind = spine.PointBehind(g, 3f);
            // 3 m behind the head is on the curve of the junction (the branch), not on the straight route.
            Assert.That(behind.x, Is.GreaterThan(0.5f), "carriage jumped to the other route: " + behind);
        }

        [Test]
        public void Reverse_TurnsTheTrainAround()
        {
            var g = new TrackGraph();
            TrackNode a = g.Add(TrackType.Straight, new TrackPose(Vector3.zero, 0f));
            Extend(g, a, 1, TrackType.Straight);
            var spine = new TrainSpine();
            spine.Place(g, a.id, 0, 0f, true);
            spine.Advance(g, 100f, 10f); // to the far dead end at z = 8
            Assert.That(spine.PointBehind(g, 0f).z, Is.EqualTo(8f).Within(0.01));
            spine.Reverse(g, 3f);
            Assert.That(spine.PointBehind(g, 0f).z, Is.EqualTo(5f).Within(0.01), "new head is the old tail");
            Assert.That(spine.PointBehind(g, 3f).z, Is.EqualTo(8f).Within(0.01));
            float moved = spine.Advance(g, 100f, 10f);
            Assert.That(moved, Is.EqualTo(5f).Within(0.01));
            Assert.That(spine.PointBehind(g, 0f).z, Is.EqualTo(0f).Within(0.01));
        }

        [Test]
        public void RemovingTrackAhead_BecomesDeadEnd_AndTrackUnderTrainBreaksIntegrity()
        {
            TrackGraph g = Oval(out var pieces);
            var spine = new TrainSpine();
            spine.Place(g, pieces[0].id, 0, 1f, true);
            spine.ExtendBehind(g, 3f);
            Assert.IsTrue(float.IsPositiveInfinity(spine.Scan(g, 20f, -1).deadEndDistance));
            g.Remove(pieces[2].id);
            Assert.That(spine.Scan(g, 20f, -1).deadEndDistance, Is.EqualTo(7f).Within(0.01));
            Assert.IsTrue(spine.IsIntact(g));
            g.Remove(pieces[0].id);
            Assert.IsFalse(spine.IsIntact(g));
        }

        [Test]
        public void Station_IsFoundAhead()
        {
            var g = new TrackGraph();
            TrackNode a = g.Add(TrackType.Straight, new TrackPose(Vector3.zero, 0f));
            TrackNode st = Extend(g, a, 1, TrackType.Station);
            var spine = new TrainSpine();
            spine.Place(g, a.id, 0, 0f, true);
            LookAhead la = spine.Scan(g, 30f, -1);
            Assert.AreEqual(st.id, la.stationNode);
            Assert.That(la.stationDistance, Is.EqualTo(4f + TrackShapeLibrary.StationLength / 2f).Within(0.01));
        }

        [Test]
        public void Ramp_And_Bridge_AreTraversable_WithHeight()
        {
            var g = new TrackGraph();
            TrackNode r = g.Add(TrackType.Ramp, new TrackPose(Vector3.zero, 0f));
            TrackNode e = Extend(g, r, 1, TrackType.ElevatedStraight);
            TrackNode down = Extend(g, e, 1, TrackType.Ramp, 1);
            TrackNode bridge = Extend(g, down, 0, TrackType.WoodenBridge);
            TrackNode tunnel = Extend(g, bridge, 1, TrackType.Tunnel);
            var spine = new TrainSpine();
            spine.Place(g, r.id, 0, 0f, true);
            float total = 0f;
            foreach (TrackNode n in new[] { r, e, down, bridge, tunnel }) total += n.shape.paths[0].Length;
            float maxY = 0f;
            float moved = 0f;
            for (int i = 0; i < 2000 && moved < total - 1e-3f; i++)
            {
                moved += spine.Advance(g, 0.1f, 5f);
                maxY = Mathf.Max(maxY, spine.PointBehind(g, 0f).y);
            }
            Assert.That(moved, Is.EqualTo(total).Within(0.02));
            Assert.That(maxY, Is.EqualTo(TrackShapeLibrary.ElevatedHeight).Within(0.01));
            Assert.That(spine.PointBehind(g, 0f).y, Is.EqualTo(0f).Within(0.01));
        }
    }
}
