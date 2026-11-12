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
            SceneManager.LoadScene("Assets/_Project/Scenes/Main.unity");
            yield return new WaitForSeconds(1.5f);
            GameManager gm = GameManager.Instance;
            yield return Shot("01_menu");

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
            Assert.Pass();
        }
    }
}
