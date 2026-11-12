using System;
using System.Collections.Generic;
using TinyTracks.Audio;
using TinyTracks.Core;
using TinyTracks.Trains;
using UnityEngine;

namespace TinyTracks.UI
{
    /// <summary>The on-screen things the guide points at (implemented by <see cref="UIManager"/>).</summary>
    public interface IGuideTargets
    {
        Component PlayButton { get; }
        Component GoButton { get; }
        Component FastButton { get; }
        Component Tab(GameMode mode);
        Component FirstTrackButton { get; }
        Component FirstDecoButton { get; }
        string FirstDecoId { get; }
    }

    /// <summary>
    /// Teaches the game without reading, the way a grown-up sitting next to the child would:
    ///  - a first-play tour (drive, whistle, faster, build a piece, decorate, back to the train), spoken by the
    ///    narrator with a hand showing exactly where to tap;
    ///  - in free play, a short spoken tip on entering each mode, and again (with the hand) when the child seems stuck;
    ///  - little spoken reactions to what happens (end of the track, a finished loop, a station stop).
    /// Never stuck: a step already done counts at once, hints repeat while the child is idle, and after a few hints
    /// the guide gently does the step itself. The tour can be replayed from the grown-ups' panel.
    /// </summary>
    public class Guide : MonoBehaviour
    {
        public const float HintRepeat = 9f;       // seconds of idleness between repeated hints
        public const int AssistAfterHints = 3;    // then the guide does the step itself
        public const float FreeIdleHint = 14f;    // free play: idle seconds before a spoken tip
        private const float StepPause = 0.9f;

        private class Step
        {
            public string voice;
            public GameMode mode;                 // the step needs this mode (else the guide leads there first)
            public Func<Vector2> target;
            public Func<bool> done;               // null = information only (advances after the line)
            public Func<bool> assist;
            public Action enter;
        }

        private GameManager game;
        private Narrator narrator;
        private IGuideTargets ui;
        private readonly List<Step> steps = new List<Step>();
        private int index = -1;
        private float idle, stepTime, pause;
        private int hints, assistFails;
        private bool navigating;
        private GameMode navMode, spokenInMode;

        // counters the steps watch
        private int whistles, tracksPlaced, decorPlaced;
        private int startSpeed, startTracks, startDecor, startWhistles;

        // free play
        private readonly HashSet<GameMode> greeted = new HashSet<GameMode>();
        private readonly Dictionary<string, float> lastSaid = new Dictionary<string, float>();
        private int freeHints;
        private TrainController watchedTrain;

        public bool TutorialRunning => index >= 0;
        public int StepIndex => index;
        public int StepCount => steps.Count;
        public event Action TutorialFinished;

        public void Init(GameManager gm, Narrator n, IGuideTargets targets)
        {
            game = gm;
            narrator = n;
            ui = targets;
            game.ModeChanged += OnModeChanged;
            game.Whistled += () => whistles++;
            game.placement.Placed += OnTrackPlaced;
            game.placement.Rejected += () => React("doesnt_fit", 12f);
            game.placement.StateChanged += () => { if (game.placement.DeleteMode && !TutorialRunning) React("hint_delete", 40f); };
            game.decorations.Changed += () => decorPlaced = game.decorations.Count;
            game.decoPlacement.Rejected += () => React("doesnt_fit", 12f);
            game.trains.TrainChanged += OnTrainChanged;
            decorPlaced = game.decorations.Count;
            OnTrainChanged();
            BuildTour();
        }

        // ------------------------------------------------------------------------------------------------ tour
        private void BuildTour()
        {
            Camera Cam() => game.cameraController.Cam;
            steps.Clear();
            steps.Add(new Step
            {
                voice = "welcome", mode = GameMode.Menu, target = Narrator.Of(() => ui.PlayButton),
                done = () => game.Mode != GameMode.Menu,
                assist = () => { game.Play(); return true; },
            });
            steps.Add(new Step
            {
                voice = "press_go", mode = GameMode.Train, target = Narrator.Of(() => ui.GoButton),
                done = () => game.trains.Current != null && game.trains.Current.Running,
                assist = () => { game.TrainGo(); return game.trains.Current != null; },
            });
            steps.Add(new Step
            {
                voice = "tap_train", mode = GameMode.Train,
                target = () => game.trains.Current != null && game.trains.Current.Locomotive != null
                    ? Narrator.WorldToScreen(Cam(), game.trains.Current.Locomotive.transform.position + Vector3.up * 0.9f)
                    : new Vector2(Narrator.Offscreen, Narrator.Offscreen),
                enter = () => startWhistles = whistles,
                done = () => whistles > startWhistles,
                assist = () => { game.Whistle(); return true; },
            });
            steps.Add(new Step
            {
                voice = "go_faster", mode = GameMode.Train, target = Narrator.Of(() => ui.FastButton),
                enter = () => startSpeed = game.trains.Current != null ? game.trains.Current.SpeedLevel : 0,
                done = () => game.trains.Current == null || game.trains.Current.SpeedLevel > startSpeed
                             || game.trains.Current.SpeedLevel == TrainController.SpeedLevels.Length - 1,
                assist = () => { game.ChangeSpeed(1); return true; },
            });
            steps.Add(new Step
            {
                voice = "open_build", mode = GameMode.Train, target = Narrator.Of(() => ui.Tab(GameMode.Build)),
                done = () => game.Mode == GameMode.Build,
                assist = () => { game.SetMode(GameMode.Build); return true; },
            });
            steps.Add(new Step
            {
                voice = "pick_track", mode = GameMode.Build, target = Narrator.Of(() => ui.FirstTrackButton),
                done = () => game.placement.Selected != null,
                assist = () => { game.placement.Select(Tracks.TrackType.Straight); return game.placement.HasGhost; },
            });
            steps.Add(new Step
            {
                voice = "place_track", mode = GameMode.Build,
                target = () => game.placement.HasGhost ? Narrator.WorldToScreen(Cam(), game.placement.GhostCenter) : Narrator.Of(() => ui.FirstTrackButton)(),
                enter = () => startTracks = tracksPlaced,
                done = () => tracksPlaced > startTracks,
                assist = () => game.placement.Confirm(),
            });
            steps.Add(new Step { voice = "more_track", mode = GameMode.Build });
            steps.Add(new Step
            {
                voice = "open_decorate", mode = GameMode.Build, target = Narrator.Of(() => ui.Tab(GameMode.Decorate)),
                done = () => game.Mode == GameMode.Decorate,
                assist = () => { game.SetMode(GameMode.Decorate); return true; },
            });
            steps.Add(new Step
            {
                voice = "pick_decor", mode = GameMode.Decorate, target = Narrator.Of(() => ui.FirstDecoButton),
                done = () => game.decoPlacement.Selected != null,
                assist = () => { game.decoPlacement.Select(ui.FirstDecoId); return game.decoPlacement.HasGhost; },
            });
            steps.Add(new Step
            {
                voice = "place_decor", mode = GameMode.Decorate,
                target = () => game.decoPlacement.HasGhost ? Narrator.WorldToScreen(Cam(), game.decoPlacement.GhostPosition + Vector3.up * 0.5f) : Narrator.Of(() => ui.FirstDecoButton)(),
                enter = () => startDecor = decorPlaced,
                done = () => decorPlaced > startDecor,
                assist = () => game.decoPlacement.Confirm(),
            });
            steps.Add(new Step
            {
                voice = "open_train", mode = GameMode.Decorate, target = Narrator.Of(() => ui.Tab(GameMode.Train)),
                done = () => game.Mode == GameMode.Train,
                assist = () => { game.SetMode(GameMode.Train); return true; },
            });
            steps.Add(new Step { voice = "well_done", mode = GameMode.Train, enter = () => AudioManager.Sfx(AudioManager.Clips?.tada, 0.8f) });
        }

        public void StartTutorial()
        {
            if (steps.Count == 0) return;
            index = -1;
            whistles = 0;
            tracksPlaced = 0;
            Next();
        }

        public void StopTutorial(bool completed)
        {
            if (index < 0) return;
            index = -1;
            navigating = false;
            narrator.HideHand();
            narrator.HideBubble();
            if (completed)
            {
                game.save.Settings.tutorialSeen = true;
                game.save.SaveSettings();
                TutorialFinished?.Invoke();
            }
        }

        private Step Current => index >= 0 && index < steps.Count ? steps[index] : null;

        private void Next()
        {
            index++;
            narrator.HideHand();
            if (index >= steps.Count) { StopTutorial(true); return; }
            Step s = steps[index];
            hints = 0;
            assistFails = 0;
            idle = 0f;
            stepTime = 0f;
            pause = 0f;
            navigating = false;
            s.enter?.Invoke();
            // Already done ahead of time? Then move straight on.
            if (s.done != null && s.done()) { Next(); return; }
            Speak(s);
        }

        private void Speak(Step s)
        {
            GameMode m = game.Mode;
            spokenInMode = m;
            if (m == GameMode.Menu && s.voice != "welcome")
            {
                // Back on the menu mid-tour: first get them playing again.
                navigating = true;
                navMode = s.mode;
                narrator.Say("welcome", true);
                narrator.ShowTap(Narrator.Of(() => ui.PlayButton));
                return;
            }
            bool modeOk = m == s.mode || s.done == null || IsNavStep(s);
            if (!modeOk)
            {
                // The child wandered off: lead them back to the right place first.
                navigating = true;
                navMode = s.mode;
                string v = NavVoice(s.mode);
                narrator.Say(v, true);
                narrator.ShowTap(s.mode == GameMode.Menu ? null : Narrator.Of(() => ui.Tab(s.mode)));
                return;
            }
            navigating = false;
            narrator.Say(s.voice, s.done != null);
            if (s.target != null) narrator.ShowTap(s.target); else narrator.HideHand();
        }

        /// <summary>Steps whose job is to change mode can run from any mode.</summary>
        private static bool IsNavStep(Step s) => s.voice.StartsWith("open_") || s.voice == "welcome";

        private static string NavVoice(GameMode m)
        {
            switch (m)
            {
                case GameMode.Build: return "open_build";
                case GameMode.Decorate: return "open_decorate";
                case GameMode.Train: return "open_train";
                default: return "welcome";
            }
        }

        /// <summary>Advances the guide; called every frame (tests may call it with large steps).</summary>
        public void Tick(float dt)
        {
            bool touched = game.IdleTime < 0.25f;
            if (TutorialRunning) TickTutorial(dt, touched);
            else TickFree(dt, touched);
        }

        private void Update() => Tick(Time.unscaledDeltaTime);

        private void TickTutorial(float dt, bool touched)
        {
            Step s = Current;
            if (s == null) return;
            stepTime += dt;

            if (pause > 0f)
            {
                pause -= dt;
                if (pause <= 0f) Next();
                return;
            }

            if (s.done == null)
            {
                // Information step: move on once the line has been heard.
                bool talking = AudioManager.Instance != null && AudioManager.Instance.VoicePlaying;
                if (stepTime > 1.2f && !talking) { pause = 0.4f; }
                return;
            }
            else if (s.done())
            {
                narrator.HideHand();
                narrator.HideBubble();
                AudioManager.Sfx(AudioManager.Clips?.buttonToggle, 0.6f);
                pause = StepPause;
                return;
            }
            else if (game.Mode != spokenInMode)
            {
                Speak(s); // changed mode: re-evaluate (lead back, or carry on now they are there)
                idle = 0f;
                return;
            }

            idle = touched ? 0f : idle + dt;
            if (idle < HintRepeat) return;
            idle = 0f;
            hints++;
            if (hints >= AssistAfterHints && !navigating && s.assist != null)
            {
                // Gently do it for them (and keep hinting if that could not work yet).
                bool ok = s.assist();
                if (!ok && ++assistFails >= 2) { pause = 0.2f; return; } // never get stuck
                hints = 1;
                return;
            }
            if (navigating && hints >= AssistAfterHints)
            {
                if (game.Mode == GameMode.Menu) game.Play(); else game.SetMode(navMode);
                return;
            }
            Speak(s);
        }

        // ------------------------------------------------------------------------------------------------ free play
        private void OnModeChanged(GameMode m)
        {
            if (TutorialRunning) { greeted.Add(m); return; }
            narrator.HideHand();
            freeHints = 0;
            if (m == GameMode.Menu) { narrator.Quiet(); return; }
            if (greeted.Add(m)) Tip(m, false);
        }

        private string TipKey(GameMode m)
        {
            switch (m)
            {
                case GameMode.Build: return game.placement.DeleteMode ? "hint_delete" : "hint_build";
                case GameMode.Decorate: return "hint_decorate";
                case GameMode.Explore: return "hint_explore";
                case GameMode.Train:
                    if (game.trains.Current == null) return "no_train";
                    return game.trains.Current.Running ? "tap_train" : "press_go";
                default: return "welcome";
            }
        }

        private Func<Vector2> TipTarget(GameMode m)
        {
            switch (m)
            {
                case GameMode.Menu: return Narrator.Of(() => ui.PlayButton);
                case GameMode.Build:
                    if (game.placement.HasGhost) return () => Narrator.WorldToScreen(game.cameraController.Cam, game.placement.GhostCenter);
                    return game.placement.DeleteMode ? null : Narrator.Of(() => ui.FirstTrackButton);
                case GameMode.Decorate:
                    if (game.decoPlacement.HasGhost) return () => Narrator.WorldToScreen(game.cameraController.Cam, game.decoPlacement.GhostPosition + Vector3.up * 0.5f);
                    return Narrator.Of(() => ui.FirstDecoButton);
                case GameMode.Train:
                    if (game.trains.Current != null && !game.trains.Current.Running) return Narrator.Of(() => ui.GoButton);
                    if (game.trains.Current != null && game.trains.Current.Locomotive != null)
                        return () => Narrator.WorldToScreen(game.cameraController.Cam, game.trains.Current.Locomotive.transform.position + Vector3.up * 0.9f);
                    return null;
                default: return null;
            }
        }

        /// <summary>Speaks the tip for the current mode with the hand (the help button and idle hints).</summary>
        public void Tip(GameMode m, bool withHand = true)
        {
            string key = TipKey(m);
            narrator.Say(key);
            lastSaid[key] = Time.unscaledTime;
            Func<Vector2> t = withHand ? TipTarget(m) : null;
            if (t != null) narrator.ShowTap(t); else narrator.HideHand();
        }

        /// <summary>The help (conductor) button.</summary>
        public void Help()
        {
            if (TutorialRunning) { Step s = Current; if (s != null && pause <= 0f) Speak(s); return; }
            freeHints = 0;
            idle = 0f;
            Tip(game.Mode);
        }

        private void TickFree(float dt, bool touched)
        {
            if (touched)
            {
                idle = 0f;
                freeHints = 0;
                if (narrator.HandVisible && Time.unscaledTime - narrator.LastSpoke > 1.5f) narrator.HideHand();
                return;
            }
            idle += dt;
            if (game.Mode == GameMode.Menu || freeHints >= 2) return;
            if (idle < FreeIdleHint * (freeHints + 1)) return;
            freeHints++;
            Tip(game.Mode);
        }

        /// <summary>A spoken reaction, at most once per cooldown (never during the tour).</summary>
        private void React(string key, float cooldown)
        {
            if (TutorialRunning || game.Mode == GameMode.Menu) return;
            if (lastSaid.TryGetValue(key, out float t) && Time.unscaledTime - t < cooldown) return;
            lastSaid[key] = Time.unscaledTime;
            narrator.Say(key);
        }

        private void OnTrackPlaced(Tracks.TrackNode n, int linked, bool closedLoop)
        {
            tracksPlaced++;
            if (closedLoop) React("loop_done", 20f);
        }

        private void OnTrainChanged()
        {
            if (watchedTrain != null) watchedTrain.StateChanged -= OnTrainState;
            TrainController had = watchedTrain;
            watchedTrain = game.trains.Current;
            if (watchedTrain != null)
            {
                watchedTrain.StateChanged += OnTrainState;
                if (had == null && game.Mode == GameMode.Train) React("choo_choo", 30f);
            }
        }

        private void OnTrainState(TrainState s)
        {
            if (game.Mode == GameMode.Menu) return;
            if (s == TrainState.BlockedAtEnd) React("end_of_track", 25f);
            else if (s == TrainState.AtStation) React("all_aboard", 40f);
        }
    }
}
