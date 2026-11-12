using System;
using System.Collections.Generic;
using TinyTracks.Audio;
using TinyTracks.Trains;
using UnityEngine;

namespace TinyTracks.Core
{
    /// <summary>
    /// Gentle surprises (GDD §10 "optional rewards"): a few friends are kept back and arrive one at a time, in a gift
    /// box, after the child has played for a while. Never required, never a test: "surprise points" simply build up
    /// from playing (one per minute, a little extra for finishing a loop or a station scene). Opening the gift brings
    /// the new friend into the world and into the pickers for good. Grown-ups can unlock everything in settings.
    /// </summary>
    public class Discoveries : MonoBehaviour
    {
        public static Discoveries Instance { get; private set; }

        /// <summary>Discoverable items in the order they arrive, with the points needed for each.</summary>
        public static readonly (string id, float points)[] Schedule =
        {
            ("Duck", 6f), ("Loco_PurpleStarlight", 14f), ("Rabbit", 24f),
        };

        public GameManager game;

        /// <summary>A gift is waiting to be opened (id of what's inside), or null.</summary>
        public string PendingGift { get; private set; }
        public event Action<string> GiftReady;
        public event Action<string> Discovered;

        private SaveSystem.SettingsSave Settings => game != null && game.save != null ? game.save.Settings : null;
        private float saveTimer;

        private void Awake()
        {
            Instance = this;
            TrainManager.Availability = d => d == null || IsUnlocked(d.id);
        }

        private void OnDestroy()
        {
            if (Instance == this) TrainManager.Availability = null;
        }

        public static bool IsDiscoverable(string id)
        {
            foreach (var s in Schedule) if (s.id == id) return true;
            return false;
        }

        /// <summary>Everything that isn't a surprise is always available; surprises once found.</summary>
        public static bool IsUnlocked(string id)
        {
            if (string.IsNullOrEmpty(id) || !IsDiscoverable(id)) return true;
            Discoveries d = Instance;
            return d != null && d.Settings != null && d.Settings.discovered.Contains(id);
        }

        private void Start()
        {
            if (game == null) return;
            game.placement.Placed += (n, linked, loop) => { if (loop) AddPoints(2f); };
            Stations.StationManager.Happened += OnStation;
            CheckGift();
        }

        private void OnStation(string key)
        {
            if (key == "all_aboard" || key == "delivery" || key == "load_cargo") AddPoints(1f);
        }

        private void Update()
        {
            if (game == null || game.Mode == GameMode.Menu || Settings == null) return;
            AddPoints(Time.unscaledDeltaTime / 60f, false);
            saveTimer += Time.unscaledDeltaTime;
            if (saveTimer > 30f) { saveTimer = 0f; game.save.SaveSettings(); }
        }

        public void AddPoints(float p, bool save = true)
        {
            SaveSystem.SettingsSave s = Settings;
            if (s == null) return;
            s.surprisePoints += p;
            CheckGift();
            if (save) game.save.SaveSettings();
        }

        private void CheckGift()
        {
            SaveSystem.SettingsSave s = Settings;
            if (s == null || PendingGift != null) return;
            foreach (var item in Schedule)
            {
                if (s.discovered.Contains(item.id)) continue;
                if (s.surprisePoints < item.points) return; // in order: the next one isn't due yet
                PendingGift = item.id;
                GiftReady?.Invoke(item.id);
                return;
            }
        }

        /// <summary>Opens the waiting gift: the new friend arrives in the world.</summary>
        public void OpenGift()
        {
            string id = PendingGift;
            if (id == null) return;
            PendingGift = null;
            Unlock(id, true);
            CheckGift();
        }

        public void UnlockAll()
        {
            PendingGift = null;
            foreach (var item in Schedule) Unlock(item.id, false);
        }

        private void Unlock(string id, bool arrive)
        {
            SaveSystem.SettingsSave s = Settings;
            if (s == null) return;
            if (!s.discovered.Contains(id)) s.discovered.Add(id);
            game.save.SaveSettings();
            if (arrive) Arrive(id);
            Discovered?.Invoke(id);
        }

        private void Arrive(string id)
        {
            AudioManager.Sfx(AudioManager.Clips?.tada, 0.8f);
            TrainDefinition loco = game.content.Train(id);
            if (loco != null)
            {
                // A new train comes to visit (or the current one becomes it when the railway is full).
                if (game.trains.AddTrain(id) == null) game.trains.SelectLoco(id);
                return;
            }
            DecorationDefinition d = game.content.Decoration(id);
            if (d == null) return;
            Vector3 c = game.cameraController.Target;
            // Find a free spot near what the child is looking at.
            for (int ring = 0; ring < 8; ring++)
                for (int k = 0; k < 8; k++)
                {
                    Vector3 p = c + Quaternion.Euler(0f, k * 45f + ring * 17f, 0f) * Vector3.forward * (2f + ring * 1.5f);
                    p.y = 0f;
                    if (!game.decoPlacement.IsValid(p, d)) continue;
                    game.decorations.Place(id, p, UnityEngine.Random.Range(140f, 220f));
                    return;
                }
        }
    }
}
