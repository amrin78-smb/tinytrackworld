using System.Collections;
using System.Collections.Generic;
using NUnit.Framework;
using TinyTracks.Core;
using TinyTracks.SaveSystem;
using TinyTracks.Stations;
using TinyTracks.Tracks;
using TinyTracks.Trains;
using TinyTracks.UI;
using TinyTracks.World;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace TinyTracks.Tests
{
    /// <summary>Milestones 12-15: passengers & cargo, several trains, Snowy Valley, paint & surprises.</summary>
    public class ExpansionTests
    {
        private readonly Dictionary<string, string> backup = new Dictionary<string, string>();
        private static readonly string[] Files = { "world.json", "world.bak.json", "world_snowy_valley.json", "world_snowy_valley.bak.json", "settings.json" };

        [UnitySetUp]
        public IEnumerator Load()
        {
            backup.Clear();
            foreach (string f in Files)
            {
                string p = System.IO.Path.Combine(SaveManager.Folder, f);
                if (System.IO.File.Exists(p)) { backup[p] = System.IO.File.ReadAllText(p); System.IO.File.Delete(p); }
            }
            SaveManager.WorldId = "sunny_valley";
            UIManager.AutoStartTutorial = false;
            SceneManager.LoadScene("Assets/_Project/Scenes/Main.unity");
            yield return null;
            yield return null;
        }

        [UnityTearDown]
        public IEnumerator Restore()
        {
            Time.timeScale = 1f;
            if (SaveManager.Instance != null) SaveManager.Instance.enabled = false;
            foreach (string f in Files)
            {
                string p = System.IO.Path.Combine(SaveManager.Folder, f);
                if (backup.TryGetValue(p, out string text)) System.IO.File.WriteAllText(p, text);
                else if (System.IO.File.Exists(p)) System.IO.File.Delete(p);
            }
            SaveManager.WorldId = "sunny_valley";
            UIManager.AutoStartTutorial = true;
            yield return null;
        }

        private static IEnumerator RunUntil(System.Func<bool> done, float seconds, float timeScale = 3f)
        {
            Time.timeScale = timeScale;
            float end = Time.realtimeSinceStartup + seconds;
            while (!done() && Time.realtimeSinceStartup < end) yield return null;
            Time.timeScale = 1f;
        }

        // ------------------------------------------------------------------------------------------------ passengers
        [UnityTest]
        public IEnumerator Passengers_BoardAPassengerCarriage_AtTheStation()
        {
            GameManager gm = GameManager.Instance;
            StationManager st = gm.stations;
            Assert.IsNotNull(st, "StationManager missing from the scene");
            int stationNode = -1;
            foreach (TrackNode n in gm.network.Graph.Nodes.Values) if (n.type == TrackType.Station) stationNode = n.id;
            Assert.GreaterOrEqual(stationNode, 0);
            // Passengers gather on the platform.
            yield return RunUntil(() => st.WaitingAt(stationNode) >= 2, 20f);
            Assert.GreaterOrEqual(st.WaitingAt(stationNode), 2, "passengers should gather at the station");

            gm.Play();
            gm.trains.AddCarriage("Car_Passenger");
            TrainController t = gm.trains.Current;
            TrainVehicle car = null;
            foreach (TrainVehicle v in t.Vehicles) if (v.IsPassengerCar) car = v;
            Assert.IsNotNull(car, "passenger carriage");
            bool finished = false;
            st.ActivityFinished += (tr, node) => { if (tr == t && node == stationNode) finished = true; };
            t.SetSpeedLevel(2);
            gm.TrainGo();
            yield return RunUntil(() => finished, 60f);
            Assert.IsTrue(finished, "the train never finished a station stop");
            Assert.Greater(st.RidersIn(car), 0, "nobody boarded the carriage");
        }

        [UnityTest]
        public IEnumerator Cargo_IsLoadedAtTheCargoYard_ThenDelivered()
        {
            GameManager gm = GameManager.Instance;
            gm.ClearRailway();
            yield return null;
            WorldManager.BuildStarterLayout(gm.network, withCargoYard: true);
            yield return null;
            int yard = -1;
            foreach (TrackNode n in gm.network.Graph.Nodes.Values) if (n.type == TrackType.CargoStation) yard = n.id;
            Assert.GreaterOrEqual(yard, 0, "cargo station not placed");
            Assert.AreEqual(0, gm.network.Graph.Validate().openEnds, "cargo loop should be closed");

            gm.trains.AutoPlace(new Vector3(-2f, 0f, -8f));
            gm.SetMode(GameMode.Train);
            gm.trains.AddCarriage("Car_Cargo");
            TrainController t = gm.trains.Current;
            TrainVehicle wagon = null;
            foreach (TrainVehicle v in t.Vehicles) if (v.IsCargoCar) wagon = v;
            Assert.IsNotNull(wagon);
            int stops = 0;
            gm.stations.ActivityFinished += (tr, node) => { if (tr == t && node == yard) stops++; };
            t.SetSpeedLevel(2);
            gm.TrainGo();
            yield return RunUntil(() => stops >= 1, 60f);
            Assert.GreaterOrEqual(stops, 1, "never stopped at the cargo yard");
            Assert.IsTrue(gm.stations.IsLoaded(wagon), "the wagon should have been loaded");
            yield return RunUntil(() => stops >= 2, 80f);
            Assert.GreaterOrEqual(stops, 2, "second lap never reached the yard");
            Assert.IsFalse(gm.stations.IsLoaded(wagon), "the cargo should have been delivered on the next visit");
            Assert.GreaterOrEqual(gm.stations.PileAt(yard), 1, "delivered cargo should be on the platform");
        }

        // ------------------------------------------------------------------------------------------------ trains
        [UnityTest]
        public IEnumerator ThreeTrains_KeepTheirDistance_AndSurviveSaveLoad()
        {
            GameManager gm = GameManager.Instance;
            gm.Play();
            Assert.IsNotNull(gm.AddTrain() ? gm.trains.Current : null, "second train");
            Assert.IsTrue(gm.AddTrain(), "third train");
            Assert.IsFalse(gm.AddTrain(), "a fourth train must be refused");
            Assert.AreEqual(3, gm.trains.All.Count);
            var locos = new HashSet<string>();
            foreach (TrainController t in gm.trains.All) { locos.Add(t.LocoDefinition.id); t.SetSpeedLevel(2); t.Go(); }
            Assert.AreEqual(3, locos.Count, "each new train should be a different locomotive");

            float minGap = float.MaxValue, end = Time.realtimeSinceStartup + 25f;
            Time.timeScale = 3f;
            while (Time.realtimeSinceStartup < end)
            {
                for (int i = 0; i < gm.trains.All.Count; i++)
                    for (int j = i + 1; j < gm.trains.All.Count; j++)
                        foreach (TrainVehicle a in gm.trains.All[i].Vehicles)
                            foreach (TrainVehicle b in gm.trains.All[j].Vehicles)
                                minGap = Mathf.Min(minGap, Vector3.Distance(a.transform.TransformPoint(a.bogieMidLocal), b.transform.TransformPoint(b.bogieMidLocal)));
                yield return null;
            }
            Time.timeScale = 1f;
            Debug.Log($"[TT Test] closest approach between trains: {minGap:0.00} m");
            Assert.Greater(minGap, 1.6f, "two trains drove into each other");
            float travelled = 0f;
            foreach (TrainController t in gm.trains.All) travelled += t.Spine.TotalTravelled;
            Assert.Greater(travelled, 20f, "the trains should keep moving (no permanent jam)");

            // Save and reload: all three come back.
            gm.save.SaveWorld();
            WorldSave w = SaveManager.ReadWorld(out string problem);
            Assert.IsNull(problem);
            Assert.AreEqual(2, w.moreTrains.Count);
            gm.save.Apply(w);
            yield return null;
            Assert.AreEqual(3, gm.trains.All.Count, "trains after reload");
        }

        // ------------------------------------------------------------------------------------------------ worlds
        [UnityTest]
        public IEnumerator SnowyValley_HasItsOwnRailway_AndSunnyValleyIsKept()
        {
            GameManager gm = GameManager.Instance;
            int sunnyPieces = gm.network.Graph.Count;
            gm.Play();
            gm.SetMode(GameMode.Build);
            gm.placement.Select(TrackType.Straight);
            yield return null;
            Assert.IsTrue(gm.placement.Confirm());
            gm.SetMode(GameMode.Menu);
            sunnyPieces = gm.network.Graph.Count;

            gm.SwitchWorld("snowy_valley");
            yield return null;
            Assert.AreEqual("snowy_valley", gm.world.world.id);
            Assert.IsTrue(gm.world.world.snowy);
            Assert.IsNotNull(Object.FindAnyObjectByType<SnowFall>(), "snowfall missing");
            Assert.Greater(gm.network.Graph.Count, 6, "snowy starter railway");
            Assert.AreEqual(0, gm.network.Graph.Validate().openEnds);
            Assert.IsNotNull(gm.trains.Current, "snowy starter train");
            Assert.IsTrue(System.IO.File.Exists(System.IO.Path.Combine(SaveManager.Folder, "world_snowy_valley.json")), "snowy save");

            gm.SwitchWorld("sunny_valley");
            yield return null;
            Assert.AreEqual("sunny_valley", gm.world.world.id);
            Assert.IsNull(Object.FindAnyObjectByType<SnowFall>(), "no snow in Sunny Valley");
            Assert.AreEqual(sunnyPieces, gm.network.Graph.Count, "Sunny Valley's railway (with the added piece) should come back");
            Assert.AreEqual("sunny_valley", gm.save.Settings.lastWorld);
        }

        // ------------------------------------------------------------------------------------------------ paint & surprises
        [UnityTest]
        public IEnumerator Paint_RecoloursTheBody_AndCanBeUndone()
        {
            GameManager gm = GameManager.Instance;
            gm.Play();
            TrainVehicle loco = gm.trains.Current.Locomotive;
            Assert.Greater(loco.definition.paintColor.a, 0f, "loco has no paint colour");
            MeshFilter body = null;
            foreach (MeshFilter mf in loco.GetComponentsInChildren<MeshFilter>())
            {
                var uv2 = new List<Vector2>();
                mf.sharedMesh.GetUVs(1, uv2);
                if (uv2.Exists(u => u.x > 0.5f)) { body = mf; break; }
            }
            Assert.IsNotNull(body, "no mesh with a paint mask (uv2) on the loco");
            Mesh original = body.sharedMesh;
            gm.PaintTrain(new Color(0.2f, 0.4f, 1f));
            Assert.AreNotSame(original, body.sharedMesh, "painting should use a mesh copy");
            Color32[] painted = body.sharedMesh.colors32, before = original.colors32;
            var mask = new List<Vector2>();
            original.GetUVs(1, mask);
            int changed = 0;
            for (int i = 0; i < mask.Count; i++) if (mask[i].x > 0.5f && painted[i].b > before[i].b) changed++;
            Assert.Greater(changed, 10, "masked vertices should turn blue");
            gm.PaintTrain(null);
            Assert.AreSame(original, body.sharedMesh, "original colours should come back");
            yield return null;
        }

        [UnityTest]
        public IEnumerator Surprises_ArriveInOrder_AsAGift()
        {
            GameManager gm = GameManager.Instance;
            Discoveries d = Discoveries.Instance;
            Assert.IsNotNull(d);
            Assert.IsFalse(Discoveries.IsUnlocked("Duck"));
            Assert.IsFalse(Discoveries.IsUnlocked("Loco_PurpleStarlight"));
            Assert.IsTrue(Discoveries.IsUnlocked("Loco_RedExpress"));
            Assert.IsNull(d.PendingGift);
            gm.Play();
            d.AddPoints(6.5f);
            Assert.AreEqual("Duck", d.PendingGift);
            int decorBefore = gm.decorations.Count;
            d.OpenGift();
            Assert.IsTrue(Discoveries.IsUnlocked("Duck"));
            Assert.AreEqual(decorBefore + 1, gm.decorations.Count, "the duck should arrive in the world");
            Assert.IsNull(d.PendingGift, "the loco isn't due yet");
            d.AddPoints(8f);
            Assert.AreEqual("Loco_PurpleStarlight", d.PendingGift);
            d.OpenGift();
            Assert.AreEqual(2, gm.trains.All.Count, "Purple Starlight should arrive as a second train");
            Assert.AreEqual("Loco_PurpleStarlight", gm.trains.Current.LocoDefinition.id);
            yield return null;
        }
    }
}
