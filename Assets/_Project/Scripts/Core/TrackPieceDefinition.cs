using System;
using System.Collections.Generic;
using TinyTracks.Tracks;
using UnityEngine;

namespace TinyTracks.Core
{
    public class TrackPieceDefinition : ScriptableObject
    {
        public TrackType type;
        public string displayName;
        public TrackCategory category;
        public Sprite icon;
        public GameObject prefab;
        [Tooltip("Optional extra model placed with the piece (station building, depot shed, crossing barriers).")]
        public GameObject accessory;
        public Vector3 accessoryOffset;
        public float accessoryYaw;
        public bool mirrorAccessory;
    }

    public enum VehicleKind { Locomotive, Carriage }
    public enum EngineSound { Steam, Motor }
}
