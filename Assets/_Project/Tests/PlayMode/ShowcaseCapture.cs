using System.Collections;
using System.IO;
using NUnit.Framework;
using TinyTracks.Core;
using TinyTracks.Tracks;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace TinyTracks.Tests
{
    /// <summary>
    /// Visual QA: renders the real game (world, UI, trains) to Logs/Showcase/*.png. Explicit - run with
    /// Tools/showcase.sh. Uses the editor's renderer (xvfb + glcore), so it looks like the game, not the phone.
    /// </summary>
    [Explicit, Category("Showcase")]
    public class ShowcaseCapture
    {
        private const string Dir = "Logs/Showcase";

        private static IEnumerator Shot(string name, int w = 1600, int h = 900)
        {
            // Batch mode never reaches end-of-frame; render the camera (with the UI drawn through it) to a texture.
            yield return null;
            Directory.CreateDirectory(Dir);
            Camera cam = Camera.main;
            Canvas canvas = Object.FindAnyObjectByType<Canvas>();
            var rt = new RenderTexture(w, h, 24);
            if (canvas != null)
            {
                canvas.renderMode = RenderMode.ScreenSpaceCamera;
                canvas.worldCamera = cam;
                canvas.planeDistance = cam.nearClipPlane + 0.05f;
            }
            cam.targetTexture = rt;
            Canvas.ForceUpdateCanvases();
            cam.Render();
            cam.targetTexture = null;
            if (canvas != null) canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            RenderTexture.active = rt;
            var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
            tex.Apply();
            RenderTexture.active = null;
            File.WriteAllBytes($"{Dir}/{name}.png", tex.EncodeToPNG());
            Object.Destroy(rt);
            Debug.Log("[TT Showcase] " + name);
        }

        [UnityTest]
        public IEnumerator CaptureAll()
        {
            TinyTracks.UI.UIManager.AutoStartTutorial = false;
            SceneManager.LoadScene("Assets/_Project/Scenes/Main.unity");
            yield return new WaitForSeconds(1.5f);
            GameManager gm = GameManager.Instance;
            var ui = Object.FindAnyObjectByType<TinyTracks.UI.UIManager>();
            yield return Shot("01_menu");

            // The narrator: tour start on the menu (bubble + hand on Play).
            ui.Guide.StartTutorial();
            yield return new WaitForSecondsRealtime(1.85f);
            yield return Shot("10_guide_menu");
            ui.Guide.StopTutorial(false);

            gm.Play();
            gm.TrainGo();
            gm.cameraController.StopFollowing();
            gm.cameraController.ResetView(true);
            yield return new WaitForSeconds(3f);
            yield return Shot("02_train_overview");

            gm.cameraController.Follow(gm.trains.Current.Anchor, 10f);
            yield return new WaitForSeconds(2.5f);
            yield return Shot("03_train_follow");

            gm.trains.AddCarriage("Car_Passenger");
            gm.trains.AddCarriage("Car_Cargo");
            yield return new WaitForSeconds(3f);
            yield return Shot("04_train_carriages");

            gm.SetMode(GameMode.Build);
            gm.cameraController.ResetView(true);
            gm.placement.Select(TrackType.GentleRight);
            yield return new WaitForSeconds(1f);
            yield return Shot("05_build_ghost");
            ui.Guide.Help();
            yield return new WaitForSecondsRealtime(0.45f);
            yield return Shot("11_guide_build");
            Localization.Set("th");
            ui.Guide.Help();
            yield return new WaitForSecondsRealtime(0.45f);
            yield return Shot("12_guide_thai");
            Localization.Set("en");
            ui.Narrator.Quiet();
            gm.placement.Deselect();
            // A little showcase railway: bridge, tunnel, junction, ramp.
            TrackNode s = gm.network.Place(TrackType.Straight, new TrackPose(new Vector3(-24f, 0f, -16f), 90f));
            TrackNode cur = s;
            foreach (TrackType t in new[] { TrackType.WoodenBridge, TrackType.Tunnel, TrackType.JunctionRight, TrackType.Straight, TrackType.Ramp, TrackType.ElevatedStraight })
            {
                cur = gm.network.Place(t, TrackSnapping.PoseForAttachment(TrackShapeLibrary.Get(t), 0, cur.worldConnectorPos[1], cur.worldConnectorHeading[1]));
            }
            gm.network.Place(TrackType.Crossing, TrackSnapping.PoseForAttachment(TrackShapeLibrary.Get(TrackType.Crossing), 1, s.worldConnectorPos[0], s.worldConnectorHeading[0]));
            gm.cameraController.FocusOn(new Vector3(-8f, 0f, -14f), 22f);
            yield return new WaitForSeconds(1.5f);
            yield return Shot("06_build_pieces");

            gm.SetMode(GameMode.Decorate);
            gm.decorations.Place("Cow", new Vector3(-12f, 0f, 2f), 200f);
            gm.decorations.Place("House_A", new Vector3(8f, 0f, 8f), 180f);
            gm.decorations.Place("Tree_Round", new Vector3(12f, 0f, 4f), 0f);
            gm.decoPlacement.Select("Sheep");
            gm.cameraController.ResetView(true);
            yield return new WaitForSeconds(1.5f);
            yield return Shot("07_decorate");

            gm.SetMode(GameMode.Explore);
            gm.cameraController.FocusOn(new Vector3(-30f, 0f, 24f), 16f);
            yield return new WaitForSeconds(2f);
            yield return Shot("08_explore_farm");
            gm.cameraController.FocusOn(new Vector3(14f, 0f, 26f), 16f);
            yield return new WaitForSeconds(2f);
            yield return Shot("09_explore_village");
            ui.ShowSettings(true);
            yield return new WaitForSecondsRealtime(0.3f);
            yield return Shot("13_settings");
            ui.ShowSettings(false);
            TinyTracks.UI.UIManager.AutoStartTutorial = true;
            Assert.Pass();
        }

        /// <summary>Milestones 12-15: stations, cargo, three trains, paint, gift, Snowy Valley.</summary>
        [UnityTest]
        public IEnumerator CaptureExpansion()
        {
            foreach (string f in new[] { "world.json", "world.bak.json", "world_snowy_valley.json", "world_snowy_valley.bak.json" })
            {
                string p = System.IO.Path.Combine(TinyTracks.SaveSystem.SaveManager.Folder, f);
                if (File.Exists(p)) File.Delete(p);
            }
            TinyTracks.SaveSystem.SaveManager.WorldId = "sunny_valley";
            TinyTracks.UI.UIManager.AutoStartTutorial = false;
            SceneManager.LoadScene("Assets/_Project/Scenes/Main.unity");
            yield return new WaitForSeconds(1.5f);
            GameManager gm = GameManager.Instance;
            var ui = Object.FindAnyObjectByType<TinyTracks.UI.UIManager>();
            if (gm.world.world.id != "sunny_valley") gm.SwitchWorld("sunny_valley");

            // Cargo loop: station + cargo yard, a train with a passenger carriage and a cargo wagon.
            gm.ClearRailway();
            TinyTracks.World.WorldManager.BuildStarterLayout(gm.network, withCargoYard: true);
            gm.trains.AutoPlace(new Vector3(-2f, 0f, -8f));
            gm.SetMode(GameMode.Train);
            gm.trains.AddCarriage("Car_Passenger");
            gm.trains.AddCarriage("Car_Cargo");
            gm.cameraController.StopFollowing();
            gm.cameraController.FocusOn(new Vector3(-2f, 0f, -6f), 13f);
            yield return new WaitForSeconds(9f); // passengers gather
            yield return Shot("14_passengers_waiting");
            gm.trains.Current.SetSpeedLevel(1);
            gm.TrainGo();
            float until = Time.realtimeSinceStartup + 40f;
            bool boarding = false;
            while (Time.realtimeSinceStartup < until && gm.trains.Current.State != TinyTracks.Trains.TrainState.AtStation) yield return null;
            yield return new WaitForSeconds(1.4f);
            yield return Shot("15_passengers_boarding");
            // On to the cargo yard.
            int yard = -1;
            foreach (TrackNode n in gm.network.Graph.Nodes.Values) if (n.type == TrackType.CargoStation) yard = n.id;
            gm.stations.ActivityFinished += (t, n) => { if (n == yard) boarding = true; };
            Vector3 yardPos = gm.network.Graph.Get(yard).pose.position;
            gm.cameraController.FocusOn(yardPos, 13f);
            until = Time.realtimeSinceStartup + 60f;
            while (Time.realtimeSinceStartup < until && !(gm.trains.Current.State == TinyTracks.Trains.TrainState.AtStation && gm.trains.Current.StopNode == yard)) yield return null;
            yield return new WaitForSeconds(1.1f);
            yield return Shot("16_cargo_crane");
            until = Time.realtimeSinceStartup + 15f;
            while (Time.realtimeSinceStartup < until && !boarding) yield return null;
            yield return new WaitForSeconds(0.5f);
            yield return Shot("17_cargo_loaded");

            // Three trains, chips UI, paint palette.
            gm.AddTrain();
            gm.AddTrain();
            foreach (var t in gm.trains.All) t.Go();
            gm.cameraController.StopFollowing();
            gm.cameraController.ResetView(true);
            yield return new WaitForSeconds(4f);
            yield return Shot("18_three_trains");
            gm.PaintTrain(new Color32(255, 130, 190, 255));
            ui.ShowPalette(true);
            gm.cameraController.Follow(gm.trains.Current.Anchor, 9f);
            yield return new WaitForSeconds(2.5f);
            yield return Shot("19_paint");
            ui.ShowPalette(false);

            // A surprise gift.
            Discoveries.Instance.AddPoints(7f);
            yield return new WaitForSeconds(1f);
            yield return Shot("20_gift");
            Discoveries.Instance.OpenGift();
            yield return new WaitForSeconds(2f);
            yield return Shot("21_duck_arrived");

            // Snowy Valley.
            gm.SetMode(GameMode.Menu);
            gm.SwitchWorld("snowy_valley");
            yield return new WaitForSeconds(3f);
            yield return Shot("22_snowy_menu");
            gm.Play();
            gm.TrainGo();
            gm.cameraController.StopFollowing();
            gm.cameraController.ResetView(true);
            yield return new WaitForSeconds(4f);
            yield return Shot("23_snowy_world");
            gm.cameraController.FocusOn(new Vector3(-40f, 0f, 14f), 18f);
            yield return new WaitForSeconds(2f);
            yield return Shot("24_snowy_lake");
            gm.cameraController.FocusOn(new Vector3(16f, 0f, 28f), 16f);
            yield return new WaitForSeconds(2f);
            yield return Shot("25_snowy_village");
            gm.SwitchWorld("sunny_valley");
            TinyTracks.UI.UIManager.AutoStartTutorial = true;
            Assert.Pass();
        }
    }
}
