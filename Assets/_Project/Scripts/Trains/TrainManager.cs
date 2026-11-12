using System;
using System.Collections.Generic;
using TinyTracks.Audio;
using TinyTracks.Core;
using TinyTracks.Tracks;
using UnityEngine;

namespace TinyTracks.Trains
{
    /// <summary>
    /// Creates, places and removes the trains (up to <see cref="MaxTrains"/>). One of them is the "current" train
    /// that the controls (GO, STOP, whistle, speed, camera, loco and carriage pickers) act on; tapping a train selects
    /// it. Trains keep a safe distance from each other themselves (see <see cref="TrainController"/>). If track under
    /// a train is removed the train hops off with a puff (never floats over missing track).
    /// </summary>
    public class TrainManager : MonoBehaviour
    {
        public static TrainManager Instance { get; private set; }

        public ContentLibrary content;
        public TrackNetworkManager network;
        public TrainEffects effects;
        public int maxCarriages = 3;
        public const int MaxTrains = 3;

        private readonly List<TrainController> all = new List<TrainController>();
        private string defaultLocoId;
        private readonly List<string> pendingCars = new List<string>();

        /// <summary>Every train in the world (index 0 is not special).</summary>
        public IReadOnlyList<TrainController> All => all;
        /// <summary>The train the controls act on (null when there are none).</summary>
        public TrainController Current { get; private set; }
        /// <summary>The current train's locomotive (or the one the next train will get).</summary>
        public string SelectedLocoId => Current != null && Current.LocoDefinition != null ? Current.LocoDefinition.id : defaultLocoId;
        /// <summary>The current train's carriages (or those the next train will get).</summary>
        public List<string> SelectedCars
        {
            get
            {
                if (Current == null) return new List<string>(pendingCars);
                var ids = new List<string>();
                foreach (TrainDefinition d in Current.CarDefinitions()) ids.Add(d.id);
                return ids;
            }
        }

        /// <summary>Selection, consist or train count changed.</summary>
        public event Action TrainChanged;
        /// <summary>A second (or third) train joined.</summary>
        public event Action<TrainController> TrainAdded;

        private void Awake()
        {
            Instance = this;
            // Choose the default locomotive here, not in Start: GameManager.Start may build the starter world (and
            // place its train) before this component's Start runs, which used to create an invisible, model-less train.
            EnsureLoco();
        }

        private void Start()
        {
            if (network != null) network.NetworkChanged += OnNetworkChanged;
        }

        private void EnsureLoco()
        {
            if (content == null || content.Train(defaultLocoId) != null) return;
            foreach (TrainDefinition d in content.Locomotives()) { defaultLocoId = d.id; break; }
        }

        private List<TrainDefinition> Defs(IList<string> ids)
        {
            var list = new List<TrainDefinition>();
            foreach (string id in ids) { TrainDefinition d = content.Train(id); if (d != null && list.Count < maxCarriages) list.Add(d); }
            return list;
        }

        // ------------------------------------------------------------------------------------------------ selection
        public void Select(TrainController t)
        {
            if (t == null || !all.Contains(t) || t == Current) return;
            Current = t;
            Juice.Bounce(t.Locomotive != null ? t.Locomotive.transform : t.transform, 0.2f, 0.35f);
            TrainChanged?.Invoke();
        }

        public void SelectLoco(string id)
        {
            if (content.Train(id) == null) return;
            defaultLocoId = id;
            if (Current != null)
            {
                Current.SetConsist(content.Train(id), Current.CarDefinitions());
                Juice.PopIn(Current.Locomotive.transform, 0.3f);
                effects?.Puff(Current.Locomotive.transform.position + Vector3.up, 1.5f);
                AudioManager.Sfx(AudioManager.Clips?.puff);
            }
            TrainChanged?.Invoke();
        }

        public void SetCarriages(IList<string> ids)
        {
            pendingCars.Clear();
            foreach (string id in ids) if (pendingCars.Count < maxCarriages && content.Train(id) != null) pendingCars.Add(id);
            if (Current != null) Current.SetConsist(content.Train(SelectedLocoId), Defs(pendingCars));
            TrainChanged?.Invoke();
        }

        public void AddCarriage(string id)
        {
            List<string> cars = SelectedCars;
            if (cars.Count >= maxCarriages || content.Train(id) == null) { AudioManager.Sfx(AudioManager.Clips?.invalid); return; }
            cars.Add(id);
            pendingCars.Clear();
            pendingCars.AddRange(cars);
            if (Current != null) Current.SetConsist(content.Train(SelectedLocoId), Defs(cars));
            AudioManager.Sfx(AudioManager.Clips?.trackSnap);
            TrainChanged?.Invoke();
        }

        public void RemoveCarriage()
        {
            List<string> cars = SelectedCars;
            if (cars.Count == 0) { AudioManager.Sfx(AudioManager.Clips?.invalid); return; }
            cars.RemoveAt(cars.Count - 1);
            pendingCars.Clear();
            pendingCars.AddRange(cars);
            if (Current != null) Current.SetConsist(content.Train(SelectedLocoId), Defs(cars));
            AudioManager.Sfx(AudioManager.Clips?.trackRemove);
            TrainChanged?.Invoke();
        }

        // ------------------------------------------------------------------------------------------------ placing
        /// <summary>Places the current train (creating one if needed) on the track nearest a world point.</summary>
        public bool PlaceNear(Vector3 world, float radius = 3f)
        {
            if (!network.Graph.NearestPoint(world, radius, out TrackNode n, out int path, out float s)) return false;
            return PlaceAt(n.id, path, s, true);
        }

        public bool PlaceAt(int node, int path, float s, bool forward)
        {
            bool created = false;
            if (Current == null) { Current = CreateTrain(defaultLocoId, pendingCars); created = true; }
            if (!Current.PlaceAt(node, path, s, forward))
            {
                if (created) Discard(Current);
                return false;
            }
            Arrive(Current);
            TrainChanged?.Invoke();
            return true;
        }

        /// <summary>When GO is pressed with no train: put one on the network nearest the view (prefer a loop).</summary>
        public bool AutoPlace(Vector3 near)
        {
            TrackNode best = null;
            float bestD = float.MaxValue;
            foreach (TrackNode n in network.Graph.Nodes.Values)
            {
                if (TrackShapeLibrary.IsDeadEndPiece(n.type) || n.shape.isSwitch) continue;
                float d = Vector3.Distance(n.pose.position, near);
                if (d < bestD) { bestD = d; best = n; }
            }
            if (best == null) foreach (TrackNode n in network.Graph.Nodes.Values) { best = n; break; }
            if (best == null) return false;
            return PlaceAt(best.id, 0, best.shape.paths[0].Length * 0.5f, true);
        }

        /// <summary>
        /// Adds another train (a different locomotive) on the track as far as possible from the others and selects it.
        /// Returns null when there are already <see cref="MaxTrains"/> trains or no free track.
        /// </summary>
        public TrainController AddTrain(string locoId = null)
        {
            if (all.Count >= MaxTrains) return null;
            if (all.Count == 0) return AutoPlace(Vector3.zero) ? Current : null;
            locoId = locoId ?? UnusedLoco();
            TrackNode best = null;
            float bestScore = 4f; // need at least a few metres of clear track
            foreach (TrackNode n in network.Graph.Nodes.Values)
            {
                if (TrackShapeLibrary.IsDeadEndPiece(n.type) || n.shape.isSwitch || n.pose.position.y > 0.6f) continue;
                Vector3 mid = n.WorldPoint(0, n.shape.paths[0].Length * 0.5f);
                float score = DistanceToTrains(mid);
                if (score > bestScore) { bestScore = score; best = n; }
            }
            if (best == null) return null;
            TrainController t = CreateTrain(locoId, Array.Empty<string>());
            if (!t.PlaceAt(best.id, 0, best.shape.paths[0].Length * 0.5f, true)) { Discard(t); return null; }
            Current = t;
            Arrive(t);
            TrainAdded?.Invoke(t);
            TrainChanged?.Invoke();
            return t;
        }

        /// <summary>Restores a saved extra train (does not change the selection).</summary>
        public TrainController RestoreTrain(string locoId, IList<string> cars, int node, int path, float s, bool forward, int speed)
        {
            if (all.Count >= MaxTrains) return null;
            TrainController t = CreateTrain(content.Train(locoId) != null ? locoId : UnusedLoco(), cars);
            if (!t.PlaceAt(node, path, s, forward)) { Discard(t); return null; }
            t.SetSpeedLevel(speed);
            if (Current == null) Current = t;
            TrainChanged?.Invoke();
            return t;
        }

        private float DistanceToTrains(Vector3 p)
        {
            float best = float.MaxValue;
            foreach (TrainController t in all)
                foreach (TrainVehicle v in t.Vehicles)
                    if (v != null) best = Mathf.Min(best, Vector3.Distance(v.transform.position, p));
            return best;
        }

        private string UnusedLoco()
        {
            var used = new HashSet<string>();
            foreach (TrainController t in all) if (t.LocoDefinition != null) used.Add(t.LocoDefinition.id);
            foreach (TrainDefinition d in content.Locomotives()) if (!used.Contains(d.id) && IsAvailable(d)) return d.id;
            return defaultLocoId;
        }

        /// <summary>Hook for unlockable locomotives (see Discoveries); everything is available by default.</summary>
        public static Func<TrainDefinition, bool> Availability;
        private static bool IsAvailable(TrainDefinition d) => Availability == null || Availability(d);

        private void Arrive(TrainController t)
        {
            effects?.Puff(t.Locomotive.transform.position + Vector3.up, 1.6f);
            AudioManager.Sfx(AudioManager.Clips?.puff);
            // Pop each vehicle in where it stands (scaling the train root, which sits at the world origin, made the
            // whole train fly in from the middle of the world).
            foreach (TrainVehicle v in t.Vehicles) if (v != null) Juice.PopIn(v.body != null ? v.body : v.transform, 0.35f);
        }

        private TrainController CreateTrain(string locoId, IList<string> cars)
        {
            EnsureLoco();
            var go = new GameObject("Train" + (all.Count + 1));
            go.transform.SetParent(transform, false);
            TrainController t = go.AddComponent<TrainController>();
            t.Init(network.Graph, content.Train(content.Train(locoId) != null ? locoId : defaultLocoId), Defs(cars), effects);
            all.Add(t);
            return t;
        }

        private void Discard(TrainController t)
        {
            all.Remove(t);
            if (Current == t) Current = all.Count > 0 ? all[all.Count - 1] : null;
            Destroy(t.gameObject);
        }

        // ------------------------------------------------------------------------------------------------ removing
        /// <summary>Removes the current train (the next one becomes current).</summary>
        public void RemoveTrain() => RemoveTrain(Current);

        public void RemoveTrain(TrainController t)
        {
            if (t == null || !all.Contains(t)) return;
            effects?.Puff(t.Locomotive != null ? t.Locomotive.transform.position + Vector3.up : t.transform.position, 1.6f);
            effects?.HideDeadEnd();
            AudioManager.Sfx(AudioManager.Clips?.puff);
            Discard(t);
            TrainChanged?.Invoke();
        }

        public void RemoveAll()
        {
            for (int i = all.Count - 1; i >= 0; i--) RemoveTrain(all[i]);
        }

        private void OnNetworkChanged()
        {
            for (int i = all.Count - 1; i >= 0; i--)
            {
                TrainController t = all[i];
                if (t != null && t.Spine.IsValid && !t.IsOnTrackIntact()) RemoveTrain(t);
            }
        }

        /// <summary>The train a ray hits, if any (tap = select + whistle).</summary>
        public TrainController TrainHit(Ray ray)
        {
            TrainController best = null;
            float bestD = float.MaxValue;
            foreach (TrainController t in all)
                foreach (TrainVehicle v in t.Vehicles)
                {
                    Collider c = v != null ? v.GetComponent<Collider>() : null;
                    if (c != null && c.Raycast(ray, out RaycastHit h, 300f) && h.distance < bestD) { bestD = h.distance; best = t; }
                }
            return best;
        }

        public bool HitsTrain(Ray ray) => TrainHit(ray) != null;
    }
}
