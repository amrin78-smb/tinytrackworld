using System.Collections.Generic;
using TinyTracks.Core;
using TinyTracks.Performance;
using TinyTracks.Tracks;
using TinyTracks.Trains;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem.UI;
using UnityEngine.UI;

namespace TinyTracks.UI
{
    /// <summary>
    /// The whole interface, built in code for a 1920x1080 reference: picture buttons only for the child, text only on
    /// the grown-up settings panel (reached by holding the gear). Big targets (>= 130 px), generous spacing, nothing
    /// covers the middle of the railway.
    /// </summary>
    public class UIManager : MonoBehaviour, IGuideTargets
    {
        /// <summary>Tests switch this off so the first-play tour does not run during automated flows.</summary>
        public static bool AutoStartTutorial = true;

        public ContentLibrary content;
        public GameManager game;

        private Canvas canvas;
        private RectTransform menuRoot, hudRoot, settingsRoot;
        private RectTransform buildPanel, trainPanel, decoPanel, trayRoot;
        private readonly Dictionary<GameMode, ToyButton> modeTabs = new Dictionary<GameMode, ToyButton>();
        private readonly List<(ToyButton button, TrackType type)> trackButtons = new List<(ToyButton, TrackType)>();
        private readonly List<(ToyButton button, string id)> decoButtons = new List<(ToyButton, string)>();
        private readonly List<(ToyButton button, TrackCategory cat)> trackCats = new List<(ToyButton, TrackCategory)>();
        private readonly List<(ToyButton button, DecorationCategory cat)> decoCats = new List<(ToyButton, DecorationCategory)>();
        private readonly List<(ToyButton button, string id)> locoButtons = new List<(ToyButton, string)>();
        private readonly List<(ToyButton button, string id)> menuLocoButtons = new List<(ToyButton, string)>();
        private ToyButton confirmBtn, cancelBtn, rotateBtn, deleteBtn, undoBtn, redoBtn;
        private ToyButton decoRotate, decoDelete, decoUndo, decoCancel;
        private ToyButton goBtn, stopBtn, followBtn, slowBtn, fastBtn, playBtn;
        private Image[] speedDots;
        private RectTransform carsRow;
        private TrackCategory? openTrackCat;
        private DecorationCategory? openDecoCat;
        private Narrator narrator;
        private Guide guide;
        private ToyButton helpBtn;
        public Narrator Narrator => narrator;
        public Guide Guide => guide;
        private readonly List<ToyButton> qualityButtons = new List<ToyButton>();
        private Slider musicSlider, sfxSlider, ambientSlider, voiceSlider;
        private readonly List<(ToyButton button, string lang)> languageButtons = new List<(ToyButton, string)>();

        private Sprite Icon(string n) => content.Icon(n);

        private void Start()
        {
            BuildCanvas();
            BuildMenu();
            BuildHud();
            BuildSettings();
            BuildGuide();
            game.ModeChanged += OnModeChanged;
            OnModeChanged(game.Mode);
            if (AutoStartTutorial && !game.save.Settings.tutorialSeen) guide.StartTutorial();
        }

        // ------------------------------------------------------------------------------------------------ guide targets
        public Component PlayButton => playBtn;
        public Component GoButton => goBtn;
        public Component FastButton => fastBtn;
        public Component Tab(GameMode mode) => modeTabs.TryGetValue(mode, out ToyButton b) ? b : null;
        public Component FirstTrackButton => trackButtons.Count > 0 ? trackButtons[0].button : (trackCats.Count > 0 ? trackCats[0].button : null);
        public Component FirstDecoButton => decoButtons.Count > 0 ? decoButtons[0].button : (decoCats.Count > 0 ? decoCats[0].button : null);
        public string FirstDecoId => decoButtons.Count > 0 ? decoButtons[0].id : (FirstDeco(DecorationCategory.Nature)?.id);

        private void BuildGuide()
        {
            narrator = canvas.gameObject.AddComponent<Narrator>();
            narrator.Build(content, (RectTransform)canvas.transform, canvas.transform.Find("Safe"));
            guide = canvas.gameObject.AddComponent<Guide>();
            guide.Init(game, narrator, this);

            // The conductor: tap to hear what to do (in the menu and in every mode).
            helpBtn = UIFactory.Button("Help", canvas.transform.Find("Safe"), Icon("narrator") ?? Icon("sound"), UIFactory.Cream, 120f, 0.92f);
            helpBtn.Clicked += () => guide.Help();
            settingsRoot.SetAsLastSibling(); // the grown-ups' panel covers the bubble and the conductor
        }

        private void BuildCanvas()
        {
            if (FindAnyObjectByType<EventSystem>() == null)
            {
                var es = new GameObject("EventSystem", typeof(EventSystem), typeof(InputSystemUIInputModule));
                es.transform.SetParent(transform, false);
            }
            var go = new GameObject("Canvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            go.transform.SetParent(transform, false);
            canvas = go.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 10;
            var scaler = go.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920f, 1080f);
            // Expand: the whole 1920x1080 layout always fits (16:10 tablets get extra height, 20:9 phones extra width).
            scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.Expand;
            // Keep everything inside the safe area (notches, rounded corners).
            RectTransform safe = UIFactory.Rect("Safe", go.transform);
            UIFactory.Stretch(safe);
            safe.gameObject.AddComponent<SafeArea>();
            menuRoot = UIFactory.Rect("Menu", safe); UIFactory.Stretch(menuRoot);
            hudRoot = UIFactory.Rect("Hud", safe); UIFactory.Stretch(hudRoot);
            settingsRoot = UIFactory.Rect("Settings", safe); UIFactory.Stretch(settingsRoot);
        }

        // ------------------------------------------------------------------------------------------------ menu
        private void BuildMenu()
        {
            Image veil = UIFactory.Image("Veil", menuRoot, null, new Color(0.55f, 0.8f, 1f, 0.18f));
            UIFactory.Stretch(veil.rectTransform);

            Text title = UIFactory.Label("Title", menuRoot, "Tiny Tracks World", 118, Color.white);
            UIFactory.Anchor(title.rectTransform, new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -70f), new Vector2(1400f, 150f));
            title.GetComponent<Outline>().effectDistance = new Vector2(5f, -5f);
            Text tag = UIFactory.Label("Tagline", menuRoot, "Build it. Connect it. Ride it. Explore it.", 44, new Color(1f, 0.97f, 0.8f));
            UIFactory.Anchor(tag.rectTransform, new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -215f), new Vector2(1400f, 60f));

            playBtn = UIFactory.Button("Play", menuRoot, Icon("play"), UIFactory.Green, 300f, 0.62f);
            UIFactory.Anchor((RectTransform)playBtn.transform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0f, 10f), new Vector2(300f, 300f));
            playBtn.Clicked += () => game.Play();
            playBtn.Selected = true;

            // Pick your train.
            RectTransform locos = UIFactory.Row("Locos", menuRoot, 34f);
            UIFactory.Anchor(locos, new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0f, 70f), new Vector2(900f, 170f));
            foreach (TrainDefinition d in content.Locomotives())
            {
                ToyButton b = UIFactory.Button("Loco_" + d.id, locos, d.icon, Color.Lerp(d.uiColor, Color.white, 0.55f), 165f, 0.9f);
                string id = d.id;
                b.Clicked += () => { game.trains.SelectLoco(id); RefreshLocoSelection(); };
                menuLocoButtons.Add((b, id));
            }

            ToyButton newWorld = UIFactory.Button("NewWorld", menuRoot, Icon("new_world"), UIFactory.Yellow, 140f);
            UIFactory.Anchor((RectTransform)newWorld.transform, new Vector2(0f, 0f), new Vector2(0f, 0f), new Vector2(60f, 60f), new Vector2(140f, 140f));
            newWorld.holdSeconds = 1.5f;
            newWorld.Clicked += () => game.NewWorld();

            ToyButton gear = UIFactory.Button("Settings", menuRoot, Icon("settings"), UIFactory.Blue, 120f);
            UIFactory.Anchor((RectTransform)gear.transform, new Vector2(1f, 0f), new Vector2(1f, 0f), new Vector2(-60f, 60f), new Vector2(120f, 120f));
            gear.holdSeconds = 2f; // parent gate: hold the gear
            gear.Clicked += () => ShowSettings(true);
        }

        // ------------------------------------------------------------------------------------------------ hud
        private void BuildHud()
        {
            ToyButton home = UIFactory.Button("Home", hudRoot, Icon("home"), UIFactory.Blue, 130f);
            UIFactory.Anchor((RectTransform)home.transform, new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(36f, -30f), new Vector2(130f, 130f));
            home.Clicked += () => game.GoHome();

            ToyButton reset = UIFactory.Button("CameraReset", hudRoot, Icon("camera_reset"), UIFactory.Cream, 110f);
            UIFactory.Anchor((RectTransform)reset.transform, new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(190f, -40f), new Vector2(110f, 110f));
            reset.Clicked += () => game.cameraController.ResetView();

            RectTransform tabs = UIFactory.Column("ModeTabs", hudRoot, 22f);
            UIFactory.Anchor(tabs, new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(-30f, -30f), new Vector2(150f, 640f));
            AddTab(tabs, GameMode.Build, "build", UIFactory.Orange);
            AddTab(tabs, GameMode.Train, "train", UIFactory.Blue);
            AddTab(tabs, GameMode.Decorate, "decorate", UIFactory.Green);
            AddTab(tabs, GameMode.Explore, "explore", UIFactory.Purple);

            BuildBuildPanel();
            BuildTrainPanel();
            BuildDecoPanel();
        }

        private void AddTab(RectTransform parent, GameMode mode, string icon, Color c)
        {
            ToyButton b = UIFactory.Button("Tab_" + mode, parent, Icon(icon), c, 135f);
            b.Clicked += () => game.SetMode(mode);
            modeTabs[mode] = b;
        }

        private RectTransform BottomBar(string name)
        {
            RectTransform bar = UIFactory.Rect(name, hudRoot);
            UIFactory.Anchor(bar, new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0f, 0f), new Vector2(1920f, 220f));
            Image bg = UIFactory.Image("Back", bar, UIFactory.Rounded, new Color(1f, 1f, 1f, 0.35f));
            UIFactory.Anchor(bg.rectTransform, new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0f, -40f), new Vector2(1880f, 230f));
            return bar;
        }

        private void BuildBuildPanel()
        {
            buildPanel = BottomBar("BuildPanel");
            RectTransform cats = UIFactory.Row("Categories", buildPanel, 22f, TextAnchor.MiddleLeft);
            UIFactory.Anchor(cats, new Vector2(0f, 0f), new Vector2(0f, 0f), new Vector2(36f, 22f), new Vector2(900f, 160f));
            foreach (TrackCategory cat in new[] { TrackCategory.Straight, TrackCategory.Curve, TrackCategory.Junction, TrackCategory.BridgeTunnel, TrackCategory.Station })
            {
                TrackPieceDefinition rep = FirstTrack(cat);
                ToyButton b = UIFactory.Button("Cat_" + cat, cats, rep != null ? rep.icon : null, CategoryColour(cat), 150f, 0.92f);
                TrackCategory c = cat;
                b.Clicked += () => OpenTrackTray(openTrackCat == c ? (TrackCategory?)null : c);
                trackCats.Add((b, cat));
            }
            trayRoot = UIFactory.Rect("Tray", hudRoot);
            UIFactory.Stretch(trayRoot); // the tray grid is positioned from the screen's bottom-left

            RectTransform actions = UIFactory.Row("Actions", buildPanel, 20f, TextAnchor.MiddleRight);
            UIFactory.Anchor(actions, new Vector2(1f, 0f), new Vector2(1f, 0f), new Vector2(-36f, 22f), new Vector2(900f, 160f));
            cancelBtn = Action(actions, "cancel", UIFactory.Cream, () => game.placement.Deselect());
            rotateBtn = Action(actions, "rotate", UIFactory.Orange, () => game.placement.Rotate());
            undoBtn = Action(actions, "undo", UIFactory.Yellow, () => game.Undo());
            redoBtn = Action(actions, "redo", UIFactory.Yellow, () => game.Redo());
            deleteBtn = Action(actions, "delete", UIFactory.Red, () => game.placement.ToggleDeleteMode());
            confirmBtn = Action(actions, "confirm", UIFactory.Green, () => game.placement.Confirm(), 160f);

            ToyButton clear = UIFactory.Button("ClearAll", buildPanel, Icon("clear_all"), UIFactory.Cream, 100f);
            UIFactory.Anchor((RectTransform)clear.transform, new Vector2(0.5f, 1f), new Vector2(0.5f, 0f), new Vector2(0f, 20f), new Vector2(100f, 100f));
            clear.holdSeconds = 2f;
            clear.Clicked += () => game.ClearRailway();
            clear.gameObject.SetActive(true);
            ((RectTransform)clear.transform).anchoredPosition = new Vector2(860f, 0f);
            clear.transform.SetParent(hudRoot, true);
            UIFactory.Anchor((RectTransform)clear.transform, new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(330f, -45f), new Vector2(100f, 100f));
            clear.name = "ClearAll";
            buildOnly.Add(clear.gameObject);
        }

        private readonly List<GameObject> buildOnly = new List<GameObject>();

        private ToyButton Action(RectTransform parent, string icon, Color c, System.Action act, float size = 140f)
        {
            ToyButton b = UIFactory.Button("Act_" + icon, parent, Icon(icon), c, size);
            b.Clicked += act;
            return b;
        }

        private static Color CategoryColour(TrackCategory c)
        {
            switch (c)
            {
                case TrackCategory.Straight: return new Color32(255, 236, 200, 255);
                case TrackCategory.Curve: return new Color32(214, 238, 255, 255);
                case TrackCategory.Junction: return new Color32(255, 222, 236, 255);
                case TrackCategory.BridgeTunnel: return new Color32(214, 246, 214, 255);
                default: return new Color32(236, 226, 255, 255);
            }
        }

        private TrackPieceDefinition FirstTrack(TrackCategory c)
        {
            foreach (TrackPieceDefinition d in content.tracks) if (d != null && d.category == c) return d;
            return null;
        }

        private void OpenTrackTray(TrackCategory? cat)
        {
            openTrackCat = cat;
            ClearTray();
            if (cat == null) return;
            var row = TrayRow();
            foreach (TrackPieceDefinition d in content.tracks)
            {
                if (d == null || d.category != cat.Value) continue;
                ToyButton b = UIFactory.Button("Piece_" + d.type, row, d.icon, CategoryColour(cat.Value), 150f, 0.95f);
                TrackType t = d.type;
                b.Clicked += () => game.placement.Select(t);
                trackButtons.Add((b, t));
                Juice.PopIn(b.transform, 0.25f);
            }
            FitTray(row, trackButtons.Count);
        }

        private RectTransform TrayRow()
        {
            // Grid that grows upwards from just above the bottom bar, at most 9 per row, so it never reaches the mode tabs.
            RectTransform row = UIFactory.Rect("TrayGrid", trayRoot);
            row.anchorMin = row.anchorMax = new Vector2(0f, 0f);
            row.pivot = new Vector2(0f, 0f);
            row.anchoredPosition = new Vector2(36f, 205f);
            var grid = row.gameObject.AddComponent<GridLayoutGroup>();
            grid.cellSize = new Vector2(150f, 150f);
            grid.spacing = new Vector2(20f, 16f);
            grid.startCorner = GridLayoutGroup.Corner.LowerLeft;
            grid.startAxis = GridLayoutGroup.Axis.Horizontal;
            grid.childAlignment = TextAnchor.LowerLeft;
            grid.constraint = GridLayoutGroup.Constraint.FixedColumnCount;
            grid.constraintCount = 9;
            grid.padding = new RectOffset(12, 12, 10, 10);
            var fit = row.gameObject.AddComponent<ContentSizeFitter>();
            fit.horizontalFit = ContentSizeFitter.FitMode.PreferredSize;
            fit.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            Image bg = UIFactory.Image("TrayBack", trayRoot, UIFactory.Rounded, new Color(1f, 1f, 1f, 0.55f));
            bg.transform.SetAsFirstSibling();
            trayBack = bg.rectTransform;
            trayGrid = row;
            return row;
        }

        private RectTransform trayBack, trayGrid;

        /// <summary>The tray is only as wide as its buttons (at most 9 per row).</summary>
        private static void FitTray(RectTransform row, int count) =>
            row.GetComponent<GridLayoutGroup>().constraintCount = Mathf.Clamp(count, 1, 9);

        private void LateUpdate()
        {
            if (trayBack == null || trayGrid == null) return;
            trayBack.anchorMin = trayBack.anchorMax = new Vector2(0f, 0f);
            trayBack.pivot = new Vector2(0f, 0f);
            trayBack.anchoredPosition = trayGrid.anchoredPosition;
            trayBack.sizeDelta = trayGrid.sizeDelta;
        }

        private void ClearTray()
        {
            foreach (Transform c in trayRoot) Destroy(c.gameObject);
            trackButtons.Clear();
            decoButtons.Clear();
        }

        private void BuildTrainPanel()
        {
            trainPanel = BottomBar("TrainPanel");
            RectTransform left = UIFactory.Row("Drive", trainPanel, 26f, TextAnchor.MiddleLeft);
            UIFactory.Anchor(left, new Vector2(0f, 0f), new Vector2(0f, 0f), new Vector2(40f, 14f), new Vector2(1100f, 200f));
            goBtn = UIFactory.Button("Go", left, Icon("go"), UIFactory.Green, 190f, 0.66f);
            goBtn.Clicked += () => game.TrainGo();
            stopBtn = UIFactory.Button("Stop", left, Icon("stop"), UIFactory.Red, 190f, 0.72f);
            stopBtn.Clicked += () => game.TrainStop();
            ToyButton whistle = UIFactory.Button("Whistle", left, Icon("whistle"), UIFactory.Yellow, 160f);
            whistle.Clicked += () => game.Whistle();
            whistle.playSound = false;
            ToyButton bell = UIFactory.Button("Bell", left, Icon("bell"), UIFactory.Orange, 160f);
            bell.Clicked += () => game.Bell();
            bell.playSound = false;

            RectTransform right = UIFactory.Row("Speed", trainPanel, 20f, TextAnchor.MiddleRight);
            UIFactory.Anchor(right, new Vector2(1f, 0f), new Vector2(1f, 0f), new Vector2(-36f, 22f), new Vector2(700f, 160f));
            slowBtn = UIFactory.Button("Slow", right, Icon("speed_slow"), new Color32(200, 240, 200, 255), 140f, 0.9f);
            slowBtn.Clicked += () => game.ChangeSpeed(-1);
            RectTransform dots = UIFactory.Column("Dots", right, 10f, TextAnchor.MiddleCenter);
            dots.sizeDelta = new Vector2(40f, 140f);
            speedDots = new Image[TrainController.SpeedLevels.Length];
            for (int i = speedDots.Length - 1; i >= 0; i--)
            {
                speedDots[i] = UIFactory.Image("Dot" + i, dots, UIFactory.Circle, Color.white);
                speedDots[i].rectTransform.sizeDelta = new Vector2(34f, 34f);
            }
            fastBtn = UIFactory.Button("Fast", right, Icon("speed_fast"), new Color32(255, 226, 200, 255), 140f, 0.9f);
            fastBtn.Clicked += () => game.ChangeSpeed(1);
            followBtn = UIFactory.Button("Follow", right, Icon("camera_follow"), UIFactory.Cream, 140f);
            followBtn.Clicked += () => game.ToggleFollow();

            // Train chooser + carriages, above the bar on the left.
            RectTransform pick = UIFactory.Row("Pick", hudRoot, 16f, TextAnchor.MiddleLeft);
            UIFactory.Anchor(pick, new Vector2(0f, 0f), new Vector2(0f, 0f), new Vector2(40f, 225f), new Vector2(1300f, 130f));
            trainOnly.Add(pick.gameObject);
            foreach (TrainDefinition d in content.Locomotives())
            {
                ToyButton b = UIFactory.Button("Pick_" + d.id, pick, d.icon, Color.Lerp(d.uiColor, Color.white, 0.6f), 120f, 0.95f);
                string id = d.id;
                b.Clicked += () => { game.trains.SelectLoco(id); RefreshLocoSelection(); };
                locoButtons.Add((b, id));
            }
            RectTransform gap = UIFactory.Rect("Gap", pick);
            gap.sizeDelta = new Vector2(24f, 10f);
            foreach (TrainDefinition d in content.trains)
            {
                if (d == null || d.kind != VehicleKind.Carriage) continue;
                ToyButton b = UIFactory.Button("Add_" + d.id, pick, d.icon, new Color32(220, 236, 255, 255), 120f, 0.95f);
                string id = d.id;
                b.Clicked += () => game.trains.AddCarriage(id);
            }
            ToyButton minus = UIFactory.Button("RemoveCar", pick, Icon("minus"), UIFactory.Cream, 100f);
            minus.Clicked += () => game.trains.RemoveCarriage();
        }

        private readonly List<GameObject> trainOnly = new List<GameObject>();

        private void BuildDecoPanel()
        {
            decoPanel = BottomBar("DecoPanel");
            RectTransform cats = UIFactory.Row("Categories", decoPanel, 22f, TextAnchor.MiddleLeft);
            UIFactory.Anchor(cats, new Vector2(0f, 0f), new Vector2(0f, 0f), new Vector2(36f, 22f), new Vector2(950f, 160f));
            foreach (DecorationCategory cat in new[] { DecorationCategory.Nature, DecorationCategory.Buildings, DecorationCategory.Animals, DecorationCategory.People, DecorationCategory.Props })
            {
                DecorationDefinition rep = FirstDeco(cat);
                if (rep == null) continue;
                ToyButton b = UIFactory.Button("DCat_" + cat, cats, rep.icon, new Color32(222, 246, 214, 255), 150f, 0.92f);
                DecorationCategory c = cat;
                b.Clicked += () => OpenDecoTray(openDecoCat == c ? (DecorationCategory?)null : c);
                decoCats.Add((b, cat));
            }
            RectTransform actions = UIFactory.Row("Actions", decoPanel, 20f, TextAnchor.MiddleRight);
            UIFactory.Anchor(actions, new Vector2(1f, 0f), new Vector2(1f, 0f), new Vector2(-36f, 22f), new Vector2(800f, 160f));
            decoCancel = Action(actions, "cancel", UIFactory.Cream, () => game.decoPlacement.Deselect());
            decoRotate = Action(actions, "rotate", UIFactory.Orange, () => game.decoPlacement.Rotate());
            decoUndo = Action(actions, "undo", UIFactory.Yellow, () => game.Undo());
            decoDelete = Action(actions, "delete", UIFactory.Red, () => game.decoPlacement.ToggleDeleteMode());
        }

        private DecorationDefinition FirstDeco(DecorationCategory c)
        {
            foreach (DecorationDefinition d in content.decorations) if (d != null && d.placeable && d.category == c) return d;
            return null;
        }

        private void OpenDecoTray(DecorationCategory? cat)
        {
            openDecoCat = cat;
            ClearTray();
            if (cat == null) return;
            var row = TrayRow();
            foreach (DecorationDefinition d in content.decorations)
            {
                if (d == null || !d.placeable || d.category != cat.Value) continue;
                ToyButton b = UIFactory.Button("Deco_" + d.id, row, d.icon, new Color32(222, 246, 214, 255), 150f, 0.95f);
                string id = d.id;
                b.Clicked += () => game.decoPlacement.Select(id);
                decoButtons.Add((b, id));
                Juice.PopIn(b.transform, 0.25f);
            }
            FitTray(row, decoButtons.Count);
        }

        // ------------------------------------------------------------------------------------------------ settings
        private void BuildSettings()
        {
            Image dim = UIFactory.Image("Dim", settingsRoot, null, new Color(0.1f, 0.15f, 0.3f, 0.55f), true);
            UIFactory.Stretch(dim.rectTransform);
            Image panel = UIFactory.Image("Panel", settingsRoot, UIFactory.Rounded, UIFactory.Cream, true);
            UIFactory.Anchor(panel.rectTransform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(1100f, 1010f));
            RectTransform p = panel.rectTransform;
            Text title = UIFactory.Label("Title", p, "Grown-ups", 64, new Color(0.25f, 0.3f, 0.5f));
            title.GetComponent<Outline>().enabled = false;
            UIFactory.Anchor(title.rectTransform, new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -40f), new Vector2(900f, 80f));

            SettingsSaveRow(p, "Music", -170f, Icon("music"), out musicSlider);
            SettingsSaveRow(p, "Sounds", -280f, Icon("sound"), out sfxSlider);
            SettingsSaveRow(p, "Nature sounds", -390f, Icon("decorate"), out ambientSlider);
            SettingsSaveRow(p, "Voice", -500f, Icon("narrator") ?? Icon("sound"), out voiceSlider);
            musicSlider.onValueChanged.AddListener(_ => ApplyVolumes());
            sfxSlider.onValueChanged.AddListener(_ => ApplyVolumes());
            ambientSlider.onValueChanged.AddListener(_ => ApplyVolumes());
            voiceSlider.onValueChanged.AddListener(_ => ApplyVolumes());

            SectionLabel(p, "Graphics", -610f);
            RectTransform qrow = UIFactory.Row("Quality", p, 20f, TextAnchor.MiddleLeft);
            UIFactory.Anchor(qrow, new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(380f, -610f), new Vector2(640f, 100f));
            string[] names = { "Low", "Medium", "High" };
            for (int i = 0; i < 3; i++)
            {
                int q = i;
                qualityButtons.Add(TextToggle(qrow, names[i], () => { game.performance.Apply((QualityPreset)q); game.save.Settings.quality = q; game.save.SaveSettings(); RefreshQuality(); }));
            }

            SectionLabel(p, "Language", -715f);
            RectTransform lrow = UIFactory.Row("Language", p, 20f, TextAnchor.MiddleLeft);
            UIFactory.Anchor(lrow, new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(380f, -715f), new Vector2(640f, 100f));
            string[] langs = { "auto", "en", "th" };
            string[] langNames = { "Auto", "English", "ไทย" };
            for (int i = 0; i < langs.Length; i++)
            {
                string l = langs[i];
                ToyButton b = TextToggle(lrow, langNames[i], () =>
                {
                    game.save.Settings.language = l;
                    Localization.Set(l);
                    game.save.SaveSettings();
                    RefreshLanguage();
                    narrator.Say("choo_choo");
                });
                languageButtons.Add((b, l));
            }

            // Replay the first-play tour.
            RectTransform howBox = UIFactory.Rect("ShowMeHow", p);
            UIFactory.Anchor(howBox, new Vector2(0f, 0f), new Vector2(0f, 0f), new Vector2(80f, 70f), new Vector2(330f, 100f));
            ToyButton how = TextToggle(howBox, "Show me how", () => { ShowSettings(false); game.SetMode(GameMode.Menu); guide.StartTutorial(); });
            ((RectTransform)how.transform).sizeDelta = new Vector2(330f, 100f);
            how.Selected = false; // an action, not a toggle: no selection ring

            Text fps = UIFactory.Label("Fps", p, "", 26, new Color(0.4f, 0.45f, 0.6f), TextAnchor.MiddleLeft);
            fps.GetComponent<Outline>().enabled = false;
            UIFactory.Anchor(fps.rectTransform, new Vector2(0f, 0f), new Vector2(0f, 0f), new Vector2(80f, 14f), new Vector2(700f, 44f));
            fps.gameObject.AddComponent<FpsLabel>();

            ToyButton newWorld = UIFactory.Button("NewWorld", p, Icon("new_world"), UIFactory.Yellow, 130f);
            UIFactory.Anchor((RectTransform)newWorld.transform, new Vector2(1f, 0f), new Vector2(1f, 0f), new Vector2(-230f, 40f), new Vector2(130f, 130f));
            newWorld.holdSeconds = 1.5f;
            newWorld.Clicked += () => { ShowSettings(false); game.NewWorld(); };
            Text nwLabel = UIFactory.Label("NewWorldLabel", p, "Hold for a new world", 26, new Color(0.4f, 0.45f, 0.6f));
            nwLabel.GetComponent<Outline>().enabled = false;
            UIFactory.Anchor(nwLabel.rectTransform, new Vector2(1f, 0f), new Vector2(1f, 0f), new Vector2(-160f, 10f), new Vector2(360f, 40f));

            ToyButton close = UIFactory.Button("Close", p, Icon("confirm"), UIFactory.Green, 130f);
            UIFactory.Anchor((RectTransform)close.transform, new Vector2(1f, 0f), new Vector2(1f, 0f), new Vector2(-50f, 40f), new Vector2(130f, 130f));
            close.Clicked += () => ShowSettings(false);
            settingsRoot.gameObject.SetActive(false);
        }

        private void SectionLabel(RectTransform p, string text, float y)
        {
            Text t = UIFactory.Label(text + "Label", p, text, 40, new Color(0.25f, 0.3f, 0.5f), TextAnchor.MiddleLeft);
            t.GetComponent<Outline>().enabled = false;
            UIFactory.Anchor(t.rectTransform, new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(80f, y - 20f), new Vector2(300f, 60f));
        }

        /// <summary>A rounded text button for the grown-ups' panel (selectable).</summary>
        private ToyButton TextToggle(RectTransform parent, string label, System.Action act)
        {
            RectTransform box = UIFactory.Rect("Opt_" + label, parent);
            box.sizeDelta = new Vector2(190f, 90f);
            Image bg = UIFactory.Image("Bg", box, UIFactory.Rounded, new Color32(214, 230, 255, 255), true);
            UIFactory.Stretch(bg.rectTransform);
            Text t = UIFactory.Label("Text", box, label, 36, new Color(0.2f, 0.25f, 0.45f));
            t.GetComponent<Outline>().enabled = false;
            if (content.captionFont != null) t.font = content.captionFont;
            UIFactory.Stretch(t.rectTransform);
            Image ring = UIFactory.Image("Ring", box, UIFactory.Rounded, new Color(1f, 0.8f, 0.2f, 0.6f));
            UIFactory.Stretch(ring.rectTransform);
            ring.rectTransform.offsetMin = new Vector2(-8f, -8f);
            ring.rectTransform.offsetMax = new Vector2(8f, 8f);
            ring.transform.SetAsFirstSibling();
            ToyButton b = box.gameObject.AddComponent<ToyButton>();
            b.background = bg;
            b.ring = ring;
            b.Clicked += act;
            return b;
        }

        private void RefreshLanguage()
        {
            foreach (var (b, l) in languageButtons) b.Selected = l == (game.save.Settings.language ?? "auto");
        }

        private void SettingsSaveRow(RectTransform p, string label, float y, Sprite icon, out Slider slider)
        {
            Image ic = UIFactory.Image(label + "Icon", p, icon, Color.white);
            ic.preserveAspect = true;
            UIFactory.Anchor(ic.rectTransform, new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(80f, y), new Vector2(90f, 90f));
            Text t = UIFactory.Label(label + "Label", p, label, 38, new Color(0.25f, 0.3f, 0.5f), TextAnchor.MiddleLeft);
            t.GetComponent<Outline>().enabled = false;
            UIFactory.Anchor(t.rectTransform, new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(190f, y - 15f), new Vector2(300f, 60f));
            slider = UIFactory.Slider(label + "Slider", p, 0.5f, UIFactory.Green, 520f);
            UIFactory.Anchor((RectTransform)slider.transform, new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(480f, y - 10f), new Vector2(520f, 70f));
        }

        public void ShowSettings(bool on)
        {
            settingsRoot.gameObject.SetActive(on);
            settingsRoot.SetAsLastSibling();
            if (on) narrator?.Quiet();
            if (!on) { game.save.SaveSettings(); return; }
            musicSlider.SetValueWithoutNotify(game.audioManager.MusicVolume);
            sfxSlider.SetValueWithoutNotify(game.audioManager.SfxVolume);
            ambientSlider.SetValueWithoutNotify(game.audioManager.AmbientVolume);
            voiceSlider.SetValueWithoutNotify(game.audioManager.VoiceVolume);
            RefreshQuality();
            RefreshLanguage();
        }

        private void ApplyVolumes()
        {
            game.audioManager.SetVolumes(musicSlider.value, sfxSlider.value, ambientSlider.value);
            game.save.Settings.music = musicSlider.value;
            game.save.Settings.sfx = sfxSlider.value;
            game.save.Settings.ambient = ambientSlider.value;
            game.audioManager.SetVoiceVolume(voiceSlider.value);
            game.save.Settings.voice = voiceSlider.value;
        }

        private void RefreshQuality()
        {
            for (int i = 0; i < qualityButtons.Count; i++) qualityButtons[i].Selected = (int)game.performance.Current == i;
        }

        // ------------------------------------------------------------------------------------------------ state
        private void OnModeChanged(GameMode m)
        {
            menuRoot.gameObject.SetActive(m == GameMode.Menu);
            hudRoot.gameObject.SetActive(m != GameMode.Menu);
            buildPanel.gameObject.SetActive(m == GameMode.Build);
            trainPanel.gameObject.SetActive(m == GameMode.Train);
            decoPanel.gameObject.SetActive(m == GameMode.Decorate);
            foreach (GameObject g in trainOnly) g.SetActive(m == GameMode.Train);
            foreach (GameObject g in buildOnly) g.SetActive(m == GameMode.Build);
            foreach (KeyValuePair<GameMode, ToyButton> kv in modeTabs) kv.Value.Selected = kv.Key == m;
            openTrackCat = null;
            openDecoCat = null;
            ClearTray();
            // Conductor (help) button: bottom-left on the menu beside New World, top-left next to the camera buttons in play.
            if (helpBtn != null)
            {
                var hr = (RectTransform)helpBtn.transform;
                if (m == GameMode.Menu) UIFactory.Anchor(hr, new Vector2(0f, 0f), new Vector2(0f, 0f), new Vector2(230f, 70f), new Vector2(120f, 120f));
                else UIFactory.Anchor(hr, new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(m == GameMode.Build ? 460f : 330f, -45f), new Vector2(110f, 110f));
                helpBtn.transform.SetSiblingIndex(settingsRoot.GetSiblingIndex());
            }
            // Menu: centred under the title. Play: between the top-left buttons and the mode tabs.
            if (m == GameMode.Menu) narrator?.SetBubble(new Vector2(0f, -258f), new Vector2(1040f, 116f));
            else narrator?.SetBubble(new Vector2(m == GameMode.Build ? 175f : 110f, -36f), new Vector2(m == GameMode.Build ? 1000f : 1100f, 128f));
            if (m == GameMode.Build) OpenTrackTray(TrackCategory.Straight);
            if (m == GameMode.Decorate) OpenDecoTray(DecorationCategory.Nature);
            RefreshLocoSelection();
        }

        private void RefreshLocoSelection()
        {
            foreach (var (b, id) in locoButtons) b.Selected = id == game.trains.SelectedLocoId;
            foreach (var (b, id) in menuLocoButtons) b.Selected = id == game.trains.SelectedLocoId;
        }

        private void Update()
        {
            if (game == null || hudRoot == null) return;
            GameMode m = game.Mode;
            if (m == GameMode.Build)
            {
                bool ghost = game.placement.HasGhost;
                confirmBtn.gameObject.SetActive(ghost);
                cancelBtn.gameObject.SetActive(ghost);
                rotateBtn.gameObject.SetActive(ghost);
                if (ghost) confirmBtn.Interactable = game.placement.GhostValid;
                undoBtn.Interactable = game.Commands.CanUndo;
                redoBtn.Interactable = game.Commands.CanRedo;
                deleteBtn.Selected = game.placement.DeleteMode;
                foreach (var (b, t) in trackButtons) b.Selected = game.placement.Selected == t;
                foreach (var (b, c) in trackCats) b.Selected = openTrackCat == c;
            }
            else if (m == GameMode.Decorate)
            {
                bool ghost = game.decoPlacement.Selected != null;
                decoCancel.gameObject.SetActive(ghost);
                decoRotate.gameObject.SetActive(ghost);
                decoUndo.Interactable = game.Commands.CanUndo;
                decoDelete.Selected = game.decoPlacement.DeleteMode;
                foreach (var (b, id) in decoButtons) b.Selected = game.decoPlacement.Selected == id;
                foreach (var (b, c) in decoCats) b.Selected = openDecoCat == c;
            }
            else if (m == GameMode.Train)
            {
                TrainController t = game.trains.Current;
                goBtn.Selected = t != null && t.Running;
                stopBtn.Selected = t != null && !t.Running;
                followBtn.Selected = game.cameraController.IsFollowing;
                int lvl = t != null ? t.SpeedLevel : 1;
                for (int i = 0; i < speedDots.Length; i++) speedDots[i].color = i <= lvl ? UIFactory.Green : new Color(1f, 1f, 1f, 0.6f);
            }
        }
    }

    /// <summary>Fits its RectTransform to Screen.safeArea.</summary>
    public class SafeArea : MonoBehaviour
    {
        private Rect last;

        private void Update()
        {
            Rect s = Screen.safeArea;
            if (s == last || Screen.width <= 0 || Screen.height <= 0) return;
            last = s;
            var rt = (RectTransform)transform;
            rt.anchorMin = new Vector2(s.xMin / Screen.width, s.yMin / Screen.height);
            rt.anchorMax = new Vector2(s.xMax / Screen.width, s.yMax / Screen.height);
            rt.offsetMin = rt.offsetMax = Vector2.zero;
        }
    }

    /// <summary>Grown-up panel: frame rate and device info (helps when testing on the Redmi A3).</summary>
    public class FpsLabel : MonoBehaviour
    {
        private Text text;
        private float t;

        private void Awake() => text = GetComponent<Text>();

        private void Update()
        {
            t += Time.unscaledDeltaTime;
            if (t < 0.5f) return;
            t = 0f;
            PerformanceManager pm = PerformanceManager.Instance;
            text.text = $"{(pm != null ? pm.AverageFps : 0f):0} fps  ·  {(System.IntPtr.Size == 4 ? "32-bit" : "64-bit")}  ·  {SystemInfo.graphicsDeviceType}  ·  v{Application.version}";
        }
    }
}
