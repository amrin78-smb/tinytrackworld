using System;
using System.Collections.Generic;
using TinyTracks.Tracks;
using UnityEngine;

namespace TinyTracks.Core
{
    public class TrainDefinition : ScriptableObject
    {
        public string id;
        public string displayName;
        public VehicleKind kind;
        public EngineSound engine;
        public Sprite icon;
        public GameObject prefab;
        [Tooltip("Distance between the front and rear bogie points (from the model's BogieFront/BogieRear empties).")]
        public float bogieSpacing = 1.2f;
        [Tooltip("Front bogie offset from the vehicle front coupler, along the track.")]
        public float frontOverhang = 0.4f;
        [Tooltip("Coupler-to-coupler length.")]
        public float length = 2f;
        public Color uiColor = Color.white;
        [Tooltip("The body colour the paint mask (mesh uv2.x = 1) was modelled in (sRGB, before AO). Alpha 0 = not paintable.")]
        public Color paintColor = new Color(0f, 0f, 0f, 0f);
        [Tooltip("Hidden until discovered (a gentle surprise after playing for a while).")]
        public bool discoverable;
    }

    public enum DecorationCategory { Nature, Buildings, Animals, People, Props }
    public enum TapReaction { None, Animal, Tree, House, Windmill, Station, Person, Bird, Wobble }
}
