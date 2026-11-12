using System.Collections;
using System.Collections.Generic;
using NUnit.Framework;
using TinyTracks.Core;
using TinyTracks.SaveSystem;
using TinyTracks.UI;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace TinyTracks.Tests
{
    /// <summary>The narrator and the first-play tour in the real scene.</summary>
    public class GuideTests
    {
        private string savedWorld, savedSettings;

        [UnitySetUp]
        public IEnumerator Load()
        {
            savedWorld = System.IO.File.Exists(SaveManager.WorldPath) ? System.IO.File.ReadAllText(SaveManager.WorldPath) : null;
            savedSettings = System.IO.File.Exists(SaveManager.SettingsPath) ? System.IO.File.ReadAllText(SaveManager.SettingsPath) : null;
            if (savedWorld != null) System.IO.File.Delete(SaveManager.WorldPath);
            if (System.IO.File.Exists(SaveManager.BackupPath)) System.IO.File.Delete(SaveManager.BackupPath);
            UIManager.AutoStartTutorial = false;
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
            if (savedSettings != null) System.IO.File.WriteAllText(SaveManager.SettingsPath, savedSettings);
            else if (System.IO.File.Exists(SaveManager.SettingsPath)) System.IO.File.Delete(SaveManager.SettingsPath);
            UIManager.AutoStartTutorial = true;
            yield return null;
        }

        [UnityTest]
        public IEnumerator EveryNarratorLine_HasCaptionsAndClipsInBothLanguages()
        {
            ContentLibrary lib = GameManager.Instance.content;
            Assert.GreaterOrEqual(lib.voice.Count, 20);
            foreach (VoiceLine v in lib.voice)
            {
                Assert.IsFalse(string.IsNullOrEmpty(v.en), v.key + " en text");
                Assert.IsFalse(string.IsNullOrEmpty(v.th), v.key + " th text");
                Assert.IsNotNull(v.enClip, v.key + " en clip");
                Assert.IsNotNull(v.thClip, v.key + " th clip");
            }
            Assert.IsNotNull(lib.captionFont, "caption font");
            yield return null;
        }

        /// <summary>
        /// A child who does nothing at all still gets through the whole tour: the guide repeats each hint and then
        /// does the step itself. Proves the tour can never soft-lock.
        /// </summary>
        [UnityTest]
        public IEnumerator Tutorial_CompletesEvenIfTheChildNeverTouches()
        {
            GameManager gm = GameManager.Instance;
            UIManager ui = Object.FindAnyObjectByType<UIManager>();
            Assert.IsNotNull(ui);
            yield return null;
            var said = new List<string>();
            ui.Narrator.Said += k => said.Add(k);
            bool finished = false;
            ui.Guide.TutorialFinished += () => finished = true;
            int decorBefore = gm.decorations.Count;
            gm.save.Settings.tutorialSeen = false;

            ui.Guide.StartTutorial();
            Assert.IsTrue(ui.Guide.TutorialRunning);
            Assert.AreEqual("welcome", said[0]);

            float timeout = Time.realtimeSinceStartup + 90f;
            while (ui.Guide.TutorialRunning && Time.realtimeSinceStartup < timeout)
            {
                ui.Guide.Tick(0.5f); // fast-forward the idle timers
                yield return null;
            }
            Assert.IsTrue(finished, "tour did not finish; lines so far: " + string.Join(", ", said));
            Assert.IsTrue(gm.save.Settings.tutorialSeen);
            CollectionAssert.IsSubsetOf(new[] { "welcome", "press_go", "tap_train", "go_faster", "open_build", "pick_track",
                "place_track", "open_decorate", "pick_decor", "place_decor", "open_train", "well_done" }, said);
            Assert.AreEqual(GameMode.Train, gm.Mode);
            Assert.IsNotNull(gm.trains.Current);
            Assert.IsTrue(gm.trains.Current.Running, "the guide should have started the train");
            Assert.Greater(gm.decorations.Count, decorBefore, "the guide should have placed a decoration");
            Debug.Log("[TT Test] tour lines: " + string.Join(", ", said));
        }

        [UnityTest]
        public IEnumerator HelpButton_SpeaksTheTipForTheCurrentMode()
        {
            GameManager gm = GameManager.Instance;
            UIManager ui = Object.FindAnyObjectByType<UIManager>();
            yield return null;
            var said = new List<string>();
            ui.Narrator.Said += k => said.Add(k);
            gm.SetMode(GameMode.Build);
            yield return null;
            said.Clear();
            ui.Guide.Help();
            Assert.AreEqual("hint_build", said[0]);
            Assert.IsTrue(ui.Narrator.HandVisible, "help should also show the hand");
            gm.SetMode(GameMode.Decorate);
            yield return null;
            said.Clear();
            ui.Guide.Help();
            Assert.AreEqual("hint_decorate", said[0]);
            Localization.Set("th");
            ui.Guide.Help();
            Localization.Set("en");
            yield return null;
        }
    }
}
