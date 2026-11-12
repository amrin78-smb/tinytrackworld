using System.Collections.Generic;
using NUnit.Framework;
using TinyTracks.Tracks;
using UnityEngine;

namespace TinyTracks.Tests
{
    public class TrackGraphTests
    {
        /// <summary>Pose that attaches connector <paramref name="myConnector"/> of a new piece to an open connector.</summary>
        public static TrackPose Attach(TrackGraph g, TrackNode target, int targetConnector, TrackType type, int myConnector = 0)
        {
            return TrackSnapping.PoseForAttachment(TrackShapeLibrary.Get(type), myConnector,
                target.worldConnectorPos[targetConnector], target.worldConnectorHeading[targetConnector]);
        }

        public static TrackNode Extend(TrackGraph g, TrackNode from, int connector, TrackType type, int myConnector = 0)
        {
            TrackNode n = g.Add(type, Attach(g, from, connector, type, myConnector));
            Assert.IsNotNull(n, "piece not added: " + type);
            return n;
        }

        [Test]
        public void StraightToStraight_Connects()
        {
            var g = new TrackGraph();
            TrackNode a = g.Add(TrackType.Straight, new TrackPose(Vector3.zero, 0f));
            TrackNode b = Extend(g, a, 1, TrackType.Straight);
            Assert.AreEqual(b.id, a.linkNode[1]);
            Assert.AreEqual(a.id, b.linkNode[0]);
            Assert.AreEqual(0, a.linkConnector[1] == 0 ? 0 : 1);
            Assert.That(b.worldConnectorPos[1].z, Is.EqualTo(8f).Within(1e-3));
            Assert.IsTrue(g.Validate().IsConsistent);
            Assert.AreEqual(2, g.Validate().openEnds);
        }

        [Test]
        public void StraightToCurve_Connects_AndTurns()
        {
            var g = new TrackGraph();
            TrackNode a = g.Add(TrackType.Straight, new TrackPose(Vector3.zero, 0f));
            TrackNode c = Extend(g, a, 1, TrackType.TightRight);
            Assert.AreEqual(c.id, a.linkNode[1]);
            Assert.That(c.worldConnectorHeading[1], Is.EqualTo(90f).Within(0.01));
            Assert.That(c.worldConnectorPos[1].x, Is.EqualTo(4f).Within(1e-3));
            Assert.That(c.worldConnectorPos[1].z, Is.EqualTo(8f).Within(1e-3));
        }

        [Test]
        public void CurveToCurve_Connects()
        {
            var g = new TrackGraph();
            TrackNode a = g.Add(TrackType.GentleLeft, new TrackPose(Vector3.zero, 0f));
            TrackNode b = Extend(g, a, 1, TrackType.GentleLeft);
            Assert.AreEqual(b.id, a.linkNode[1]);
            Assert.That(b.worldConnectorHeading[1], Is.EqualTo(270f).Within(0.01));
            Assert.That(b.worldConnectorPos[1].x, Is.EqualTo(-8f).Within(1e-3));
            Assert.That(b.worldConnectorPos[1].z, Is.EqualTo(8f).Within(1e-3));
        }

        [TestCase(TrackType.TightRight, 4)]
        [TestCase(TrackType.TightLeft, 4)]
        [TestCase(TrackType.GentleRight, 8)]
        [TestCase(TrackType.GentleLeft, 8)]
        public void ClosedLoop_FromCurves(TrackType curve, int count)
        {
            var g = new TrackGraph();
            TrackNode first = g.Add(curve, new TrackPose(Vector3.zero, 0f));
            TrackNode cur = first;
            for (int i = 1; i < count; i++) cur = Extend(g, cur, 1, curve);
            Assert.AreEqual(first.id, cur.linkNode[1], "loop did not close");
            TrackValidationReport r = g.Validate();
            Assert.AreEqual(0, r.openEnds);
            Assert.AreEqual(1, r.networks);
            Assert.IsTrue(r.IsConsistent, r.ToString());
            Assert.AreEqual(0, r.overlaps, r.ToString());
        }

        [Test]
        public void ClosedLoop_Oval_WithStraightsAndSCurves()
        {
            var g = new TrackGraph();
            TrackNode first = g.Add(TrackType.Straight, new TrackPose(Vector3.zero, 0f));
            TrackNode cur = Extend(g, first, 1, TrackType.Straight);
            cur = Extend(g, cur, 1, TrackType.TightRight);
            cur = Extend(g, cur, 1, TrackType.TightRight);
            cur = Extend(g, cur, 1, TrackType.Straight);
            cur = Extend(g, cur, 1, TrackType.Straight);
            cur = Extend(g, cur, 1, TrackType.TightRight);
            cur = Extend(g, cur, 1, TrackType.TightRight);
            Assert.AreEqual(first.id, cur.linkNode[1]);
            Assert.AreEqual(0, g.Validate().openEnds);
            Assert.AreEqual(0, g.Validate().overlaps, g.Validate().ToString());
        }

        [Test]
        public void Junction_ConnectsBothBranches()
        {
            var g = new TrackGraph();
            TrackNode j = g.Add(TrackType.JunctionRight, new TrackPose(Vector3.zero, 0f));
            Assert.IsTrue(j.shape.isSwitch);
            Assert.AreEqual(3, j.shape.connectors.Length);
            TrackNode s = Extend(g, j, 1, TrackType.Straight);
            TrackNode c = Extend(g, j, 2, TrackType.Straight);
            TrackNode back = Extend(g, j, 0, TrackType.Straight);
            Assert.AreEqual(s.id, j.linkNode[1]);
            Assert.AreEqual(c.id, j.linkNode[2]);
            Assert.AreEqual(back.id, j.linkNode[0]);
            Assert.IsTrue(g.Validate().IsConsistent);
        }

        [Test]
        public void Cross_HasFourConnectorsAndTwoPaths()
        {
            var g = new TrackGraph();
            TrackNode x = g.Add(TrackType.Cross, new TrackPose(Vector3.zero, 0f));
            Assert.AreEqual(4, x.shape.connectors.Length);
            Assert.AreEqual(2, x.shape.paths.Length);
            Assert.IsFalse(x.shape.isSwitch);
            for (int c = 0; c < 4; c++) Extend(g, x, c, TrackType.ShortStraight);
            Assert.AreEqual(4, g.Validate().openEnds);
            Assert.AreEqual(0, g.Validate().overlaps, g.Validate().ToString());
        }

        [Test]
        public void Delete_UnlinksNeighbours()
        {
            var g = new TrackGraph();
            TrackNode a = g.Add(TrackType.Straight, new TrackPose(Vector3.zero, 0f));
            TrackNode b = Extend(g, a, 1, TrackType.Straight);
            TrackNode c = Extend(g, b, 1, TrackType.Straight);
            Assert.IsTrue(g.Remove(b.id));
            Assert.AreEqual(-1, a.linkNode[1]);
            Assert.AreEqual(-1, c.linkNode[0]);
            Assert.AreEqual(2, g.CountNetworks());
            Assert.IsTrue(g.Validate().IsConsistent);
            // Put it back: reconnects both sides.
            TrackNode b2 = g.Add(TrackType.Straight, b.pose);
            Assert.AreEqual(b2.id, a.linkNode[1]);
            Assert.AreEqual(b2.id, c.linkNode[0]);
            Assert.AreEqual(1, g.CountNetworks());
        }

        [Test]
        public void GraphReconstruction_FromTypesAndPoses()
        {
            var g = new TrackGraph();
            TrackNode first = g.Add(TrackType.TightLeft, new TrackPose(new Vector3(3f, 0f, -2f), 90f));
            TrackNode cur = first;
            for (int i = 1; i < 4; i++) cur = Extend(g, cur, 1, TrackType.TightLeft);
            Assert.AreEqual(first.id, cur.linkNode[1]);
            TrackNode spur = g.Add(TrackType.JunctionLeft, new TrackPose(new Vector3(30f, 0f, 0f), 0f));
            Extend(g, spur, 1, TrackType.EndPiece);
            Extend(g, spur, 2, TrackType.Straight);
            var saved = new List<(int, TrackType, TrackPose)>();
            foreach (TrackNode n in g.Nodes.Values) saved.Add((n.id, n.type, n.pose));

            var g2 = new TrackGraph();
            foreach (var (id, type, pose) in saved) g2.Add(type, pose, id);
            foreach (TrackNode n in g.Nodes.Values)
            {
                TrackNode m = g2.Get(n.id);
                Assert.IsNotNull(m);
                CollectionAssert.AreEqual(n.linkNode, m.linkNode, "links differ for " + n.id);
            }
            g2.RebuildLinks();
            Assert.IsTrue(g2.Validate().IsConsistent);
        }

        [Test]
        public void Duplicate_IsRejected()
        {
            var g = new TrackGraph();
            g.Add(TrackType.Straight, new TrackPose(Vector3.zero, 0f));
            Assert.IsNull(g.TryAdd(TrackType.Straight, new TrackPose(Vector3.zero, 0f), out TrackGraph.AddResult r1));
            Assert.AreEqual(TrackGraph.AddResult.Duplicate, r1);
            // Same straight laid the other way round on top.
            Assert.IsNull(g.TryAdd(TrackType.Straight, new TrackPose(new Vector3(0f, 0f, 4f), 180f), out TrackGraph.AddResult r2));
            Assert.AreEqual(TrackGraph.AddResult.Duplicate, r2);
            Assert.AreEqual(1, g.Count);
        }

        [Test]
        public void Overlap_IsDetected_ButLevelsMayCross()
        {
            var g = new TrackGraph();
            g.Add(TrackType.Straight, new TrackPose(Vector3.zero, 0f));
            Assert.IsNull(g.TryAdd(TrackType.Straight, new TrackPose(new Vector3(-2f, 0f, 2f), 90f), out var r, 0, false));
            Assert.AreEqual(TrackGraph.AddResult.Overlap, r);
            Assert.IsNotNull(g.TryAdd(TrackType.ElevatedStraight, new TrackPose(new Vector3(-2f, 2f, 2f), 90f), out _, 0, false));
        }

        [Test]
        public void DuplicateConnections_NeverForm()
        {
            var g = new TrackGraph();
            TrackNode a = g.Add(TrackType.Straight, new TrackPose(Vector3.zero, 0f));
            Extend(g, a, 1, TrackType.Straight);
            // A third piece at the same joint must not steal or double-link connector 1 of a.
            g.Add(TrackType.TightLeft, Attach(g, a, 1, TrackType.TightLeft));
            TrackValidationReport r = g.Validate();
            Assert.AreEqual(0, r.duplicateLinks);
            Assert.IsTrue(r.IsConsistent, r.ToString());
        }

        [Test]
        public void DisconnectedEndpoints_AreReported()
        {
            var g = new TrackGraph();
            TrackNode a = g.Add(TrackType.Straight, new TrackPose(Vector3.zero, 0f));
            g.Add(TrackType.Straight, new TrackPose(new Vector3(0f, 0f, 4.6f), 0f)); // gap of 0.6 m
            Assert.AreEqual(-1, a.linkNode[1]);
            Assert.AreEqual(4, g.Validate().openEnds);
            Assert.AreEqual(2, g.Validate().networks);
        }

        [Test]
        public void EndPiece_OnlyConnectsAtEntry()
        {
            var g = new TrackGraph();
            TrackNode a = g.Add(TrackType.Straight, new TrackPose(Vector3.zero, 0f));
            TrackNode e = Extend(g, a, 1, TrackType.EndPiece);
            Assert.AreEqual(a.id, e.linkNode[0]);
            Assert.IsFalse(e.IsOpen(1));
            Assert.AreEqual(1, g.Validate().openEnds);
        }

        [Test]
        public void Ramp_RaisesConnectorToElevatedLevel()
        {
            var g = new TrackGraph();
            TrackNode r = g.Add(TrackType.Ramp, new TrackPose(Vector3.zero, 0f));
            Assert.That(r.worldConnectorPos[1].y, Is.EqualTo(TrackShapeLibrary.ElevatedHeight).Within(1e-3));
            TrackNode e = Extend(g, r, 1, TrackType.ElevatedStraight);
            Assert.That(e.pose.position.y, Is.EqualTo(TrackShapeLibrary.ElevatedHeight).Within(1e-3));
            Assert.AreEqual(e.id, r.linkNode[1]);
        }

        [Test]
        public void LongChain_StaysAligned()
        {
            var g = new TrackGraph();
            TrackNode first = g.Add(TrackType.GentleRight, new TrackPose(new Vector3(0.37f, 0f, -11.2f), 45f));
            TrackNode cur = first;
            // 10 full circles of gentle curves stacked on the same circle would duplicate; instead weave an S chain.
            for (int i = 0; i < 40; i++) cur = Extend(g, cur, 1, i % 2 == 0 ? TrackType.SCurveLeft : TrackType.SCurveRight);
            Assert.IsTrue(g.Validate().IsConsistent);
            Assert.AreEqual(2, g.Validate().openEnds);
        }
    }
}
