using System;
using System.Collections.Generic;
using TinyTracks.Audio;
using TinyTracks.Core;
using TinyTracks.Tracks;
using UnityEngine;

namespace TinyTracks.Trains
{
    /// <summary>
    /// Creates, places and removes the train(s). The UI drives the "current" train. If track under a train is
    /// removed the train hops off with a puff (never floats over missing track) and can be placed again.
    /// </summary>
    public class TrainManager : MonoBehaviour
    {
        public static TrainManager Instance { get; private set; }

        public ContentLibrary content;
        public TrackNetworkManager network;
        public TrainEffects effects;
        public int maxCarriages = 3;

        public TrainController Current { get; private set; }
        public string SelectedLocoId { get; private set; }
        public readonly List<string> SelectedCars = new List<string>();
        public event Action TrainChanged;

        private void Awake() => Instance = this;

        private void Start()
        {
            if (network != null) network.NetworkChanged += OnNetworkChanged;
            if (string.IsNullOrEmpty(SelectedLocoId))
                foreach (TrainDefinition d in content.Locomotives()) { SelectedLocoId = d.id; break; }
        }

        private List<TrainDefinition> CarDefs()
        {
            var list = new List<TrainDefinition>();
            foreach (string id in SelectedCars) { TrainDefinition d = content.Train(id); if (d != null) list.Add(d); }
            return list;
        }

        public void SelectLoco(string id)
        {
            if (content.Train(id) == null) return;
            SelectedLocoId = id;
            if (Current != null)
            {
                Current.SetConsist(content.Train(id), CarDefs());
                Juice.PopIn(Current.Locomotive.transform, 0.3f);
                effects?.Puff(Current.Locomotive.transform.position + Vector3.up, 1.5f);
                AudioManager.Sfx(AudioManager.Clips?.puff);
            }
            TrainChanged?.Invoke();
        }

        public void SetCarriages(IList<string> ids)
        {
            SelectedCars.Clear();
            foreach (string id in ids) if (SelectedCars.Count < maxCarriages && content.Train(id) != null) SelectedCars.Add(id);
            if (Current != null) Current.SetConsist(content.Train(SelectedLocoId), CarDefs());
            TrainChanged?.Invoke();
        }

        public void AddCarriage(string id)
        {
            if (SelectedCars.Count >= maxCarriages || content.Train(id) == null) { AudioManager.Sfx(AudioManager.Clips?.invalid); return; }
            SelectedCars.Add(id);
            if (Current != null) Current.SetConsist(content.Train(SelectedLocoId), CarDefs());
            AudioManager.Sfx(AudioManager.Clips?.trackSnap);
            TrainChanged?.Invoke();
        }

        public void RemoveCarriage()
        {
            if (SelectedCars.Count == 0) { AudioManager.Sfx(AudioManager.Clips?.invalid); return; }
            SelectedCars.RemoveAt(SelectedCars.Count - 1);
            if (Current != null) Current.SetConsist(content.Train(SelectedLocoId), CarDefs());
            AudioManager.Sfx(AudioManager.Clips?.trackRemove);
            TrainChanged?.Invoke();
        }

        /// <summary>Places the train on the track nearest a world point. Returns false if there is no track nearby.</summary>
        public bool PlaceNear(Vector3 world, float radius = 3f)
        {
            if (!network.Graph.NearestPoint(world, radius, out TrackNode n, out int path, out float s)) return false;
            return PlaceAt(n.id, path, s, true);
        }

        public bool PlaceAt(int node, int path, float s, bool forward)
        {
            if (Current == null) Current = CreateTrain();
            if (!Current.PlaceAt(node, path, s, forward)) return false;
            effects?.Puff(Current.Locomotive.transform.position + Vector3.up, 1.6f);
            AudioManager.Sfx(AudioManager.Clips?.puff);
            Juice.PopIn(Current.transform, 0.35f);
            TrainChanged?.Invoke();
            return true;
        }

        /// <summary>When GO is pressed with no train: put it on the network nearest the view (prefer a loop).</summary>
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

        private TrainController CreateTrain()
        {
            var go = new GameObject("Train");
            go.transform.SetParent(transform, false);
            TrainController t = go.AddComponent<TrainController>();
            t.Init(network.Graph, content.Train(SelectedLocoId), CarDefs(), effects);
            return t;
        }

        public void RemoveTrain()
        {
            if (Current == null) return;
            effects?.Puff(Current.Locomotive != null ? Current.Locomotive.transform.position + Vector3.up : Current.transform.position, 1.6f);
            effects?.HideDeadEnd();
            AudioManager.Sfx(AudioManager.Clips?.puff);
            Destroy(Current.gameObject);
            Current = null;
            TrainChanged?.Invoke();
        }

        private void OnNetworkChanged()
        {
            if (Current != null && Current.Spine.IsValid && !Current.IsOnTrackIntact()) RemoveTrain();
        }

        /// <summary>Is a world point on (or very near) the current train? (Tap = whistle.)</summary>
        public bool HitsTrain(Ray ray)
        {
            if (Current == null) return false;
            foreach (TrainVehicle v in Current.Vehicles)
            {
                Collider c = v.GetComponent<Collider>();
                if (c != null && c.Raycast(ray, out _, 300f)) return true;
            }
            return false;
        }
    }
}
