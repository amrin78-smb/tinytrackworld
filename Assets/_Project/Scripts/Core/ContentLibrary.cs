using System;
using System.Collections.Generic;
using TinyTracks.Tracks;
using UnityEngine;

namespace TinyTracks.Core
{
    public class ContentLibrary : ScriptableObject
    {
        public const string ResourcePath = "TinyTracksContent";

        public List<TrackPieceDefinition> tracks = new List<TrackPieceDefinition>();
        public List<TrainDefinition> trains = new List<TrainDefinition>();
        public List<DecorationDefinition> decorations = new List<DecorationDefinition>();
        public List<WorldDefinition> worlds = new List<WorldDefinition>();
        public AudioConfig audio;

        public Material toyMaterial;
        public Material ghostMaterial;
        public Material blobMaterial;
        public Material markerMaterial;
        public Material waterMaterial;
        public GameObject pillarPrefab;
        public GameObject switchArrowPrefab;
        public GameObject smokePuffPrefab;
        public Mesh quadMesh;

        public List<NamedSprite> icons = new List<NamedSprite>();

        [NonSerialized] private Dictionary<TrackType, TrackPieceDefinition> trackLookup;
        [NonSerialized] private Dictionary<string, TrainDefinition> trainLookup;
        [NonSerialized] private Dictionary<string, DecorationDefinition> decoLookup;
        [NonSerialized] private Dictionary<string, Sprite> iconLookup;

        public TrackPieceDefinition Track(TrackType t)
        {
            if (trackLookup == null)
            {
                trackLookup = new Dictionary<TrackType, TrackPieceDefinition>();
                foreach (TrackPieceDefinition d in tracks) if (d != null) trackLookup[d.type] = d;
            }
            return trackLookup.TryGetValue(t, out TrackPieceDefinition r) ? r : null;
        }

        public TrainDefinition Train(string id)
        {
            if (trainLookup == null)
            {
                trainLookup = new Dictionary<string, TrainDefinition>();
                foreach (TrainDefinition d in trains) if (d != null) trainLookup[d.id] = d;
            }
            return id != null && trainLookup.TryGetValue(id, out TrainDefinition r) ? r : null;
        }

        public DecorationDefinition Decoration(string id)
        {
            if (decoLookup == null)
            {
                decoLookup = new Dictionary<string, DecorationDefinition>();
                foreach (DecorationDefinition d in decorations) if (d != null) decoLookup[d.id] = d;
            }
            return id != null && decoLookup.TryGetValue(id, out DecorationDefinition r) ? r : null;
        }

        public Sprite Icon(string name)
        {
            if (iconLookup == null)
            {
                iconLookup = new Dictionary<string, Sprite>();
                foreach (NamedSprite n in icons) if (n.sprite != null) iconLookup[n.name] = n.sprite;
            }
            return iconLookup.TryGetValue(name, out Sprite s) ? s : null;
        }

        public IEnumerable<TrainDefinition> Locomotives()
        {
            foreach (TrainDefinition t in trains) if (t != null && t.kind == VehicleKind.Locomotive) yield return t;
        }

        public static ContentLibrary Load() => Resources.Load<ContentLibrary>(ResourcePath);
    }

    [Serializable]
    public struct NamedSprite
    {
        public string name;
        public Sprite sprite;
    }
}
