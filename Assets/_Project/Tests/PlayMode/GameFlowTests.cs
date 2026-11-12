using System.Collections;
using NUnit.Framework;
using TinyTracks.Core;
using TinyTracks.SaveSystem;
using TinyTracks.Tracks;
using TinyTracks.Trains;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace TinyTracks.Tests
{
    /// <summary>End-to-end checks in the real scene (world, starter railway, train, building, saving).</summary>
    public class GameFlowTests
    {
        private string savedWorld;

        [UnitySetUp]
        public IEnumerator Load()
        {
            // Run against a clean world but keep any real save of the tester untouched.
            savedWorld = System.IO.File.Exists(SaveManager.WorldPath) ? System.IO.File.ReadAllText(SaveManager.WorldPath) : null;
            if (savedWorld != null) System.IO.File.Delete(SaveManager.WorldPath);
            if (System.IO.File.Exists(SaveManager.BackupPath)) System.IO.File.Delete(SaveManager.BackupPath);
            TinyTracks.UI.UIManager.AutoStartTutorial = false;
            SceneManager.LoadScene("Assets/_Project/Scenes/Main.unity");
            yield return null;
            yield return null;
        }

        [UnityTearDown]
        public IEnumerator Restore()
        {
            // Put the tester's own world back (or remove the one the test made).
            if (SaveManager.Instance != null) SaveManager.Instance.enabled = false;
            if (savedWorld != null) System.IO.File.WriteAllText(SaveManager.WorldPath, savedWorld);
            else if (System.IO.File.Exists(SaveManager.WorldPath)) System.IO.File.Delete(SaveManager.WorldPath);
            if (System.IO.File.Exists(SaveManager.BackupPath)) System.IO.File.Delete(SaveManager.BackupPath);
            yield return null;
        }

        [UnityTest]
        public IEnumerator StarterWorld_HasClosedLoopAndTrain()
        {
            GameManager gm = GameManager.Instance;
            Assert.IsNotNull(gm);
            TrackValidationReport r = gm.network.Graph.Validate();
            Assert.Greater(gm.network.Graph.Count, 6);
            Assert.AreEqual(0, r.openEnds, r.ToString());
            Assert.IsTrue(r.IsConsistent, r.ToString());
            Assert.IsNotNull(gm.trains.Current, "starter train missing");
            // The starter train must be a real, visible locomotive (regression: a fresh world once got a model-less train).
            TrainVehicle loco = gm.trains.Current.Locomotive;
            Assert.IsNotNull(loco.definition, "starter locomotive has no definition");
            Assert.IsNotNull(loco.body, "starter locomotive has no model");
            Assert.Greater(loco.GetComponentsInChildren<Renderer>().Length, 3, "starter locomotive has no renderers");
            Assert.GreaterOrEqual(System.Linq.Enumerable.Count(gm.content.Locomotives()), 4);
            yield return null;
        }

        /// <summary>The starter loop has no open end: picking a piece must still offer a ghost that fits (green).</summary>
        [UnityTest]
        public IEnumerator ClosedLoop_PickingAPiece_OffersAPlaceableGhost()
        {
            GameManager gm = GameManager.Instance;
            gm.Play();
            gm.SetMode(GameMode.Build);
            yield return null;
            Assert.AreEqual(0, gm.network.Graph.Validate().openEnds, "starter loop should be closed");
            foreach (TrackType t in new[] { TrackType.Straight, TrackType.TightLeft, TrackType.Station, TrackType.JunctionRight })
            {
                gm.placement.Select(t);
                yield return null;
                Assert.IsTrue(gm.placement.HasGhost, t + " ghost");
                Assert.IsTrue(gm.placement.GhostValid, t + " ghost should fit somewhere near the view");
                int before = gm.network.Graph.Count;
                Assert.IsTrue(gm.placement.Confirm(), t + " confirm");
                Assert.AreEqual(before + 1, gm.network.Graph.Count);
                gm.placement.Deselect();
            }
        }

        [UnityTest]
        public IEnumerator Train_DrivesAFullLap()
        {
            GameManager gm = GameManager.Instance;
            gm.Play();
            Time.timeScale = 4f;
            TrainController t = gm.trains.Current;
            t.SetSpeedLevel(2);
            gm.TrainGo();
            float loop = 0f;
            foreach (TrackNode n in gm.network.Graph.Nodes.Values) loop += n.shape.paths[0].Length;
            float timeout = Time.realtimeSinceStartup + 60f;
            while (t.Spine.TotalTravelled < loop * 1.1f && Time.realtimeSinceStartup < timeout) yield return null;
            Time.timeScale = 1f;
            Assert.GreaterOrEqual(t.Spine.TotalTravelled, loop * 1.1f, "train did not complete the loop (it may have stopped at the station only briefly)");
            Assert.IsTrue(t.IsOnTrackIntact());
            Vector3 p = t.Locomotive.transform.position;
            Assert.That(p.y, Is.EqualTo(TrainController.RideHeight).Within(0.25f), "train is not riding on the track bed");
            gm.TrainStop();
            yield return new WaitForSeconds(2.5f);
            Assert.That(t.Speed, Is.LessThan(0.05f), "train did not stop");
        }

        [UnityTest]
        public IEnumerator Build_LoopWithPlacementController_ThenSaveAndLoad()
        {
            GameManager gm = GameManager.Instance;
            gm.SetMode(GameMode.Build);
            gm.ClearRailway();
            yield return null;
            Assert.AreEqual(0, gm.network.Graph.Count);
            // A child taps "tight curve" then keeps tapping the same button: four taps make a circle.
            gm.placement.Select(TrackType.TightRight);
            for (int i = 0; i < 4; i++) gm.placement.Select(TrackType.TightRight);
            yield return null;
            TrackValidationReport r = gm.network.Graph.Validate();
            Assert.AreEqual(4, gm.network.Graph.Count, "four taps should place four curves");
            Assert.AreEqual(0, r.openEnds, "the circle should close: " + r);
            Assert.IsTrue(gm.Undo());
            Assert.AreEqual(3, gm.network.Graph.Count);
            Assert.IsTrue(gm.Redo());
            Assert.AreEqual(0, gm.network.Graph.Validate().openEnds);

            gm.decorations.Place("Tree_Round", new Vector3(10f, 0f, 10f), 45f);
            gm.trains.PlaceNear(gm.network.Graph.Get(System.Linq.Enumerable.First(gm.network.Graph.Nodes.Keys)).pose.position + Vector3.right);
            WorldSave w = gm.save.Capture();
            string json = JsonUtility.ToJson(w);
            WorldSave back = SaveManager.Parse(json);
            gm.save.Apply(back);
            yield return null;
            Assert.AreEqual(4, gm.network.Graph.Count);
            Assert.AreEqual(0, gm.network.Graph.Validate().openEnds, "links rebuilt from saved poses");
            Assert.AreEqual(w.decorations.Count, gm.decorations.Count);
            Assert.IsNotNull(gm.trains.Current);
        }
    }
}
