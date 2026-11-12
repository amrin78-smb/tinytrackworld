using System;
using System.Collections.Generic;
using TinyTracks.Tracks;
using UnityEngine;

namespace TinyTracks.Core
{
    public class WorldDefinition : ScriptableObject
    {
        public string id = "sunny_valley";
        public string displayName = "Sunny Valley";
        public Sprite icon;
        [Tooltip("Half extents (x, z) of the flat area where tracks and decorations may be placed.")]
        public Vector2 buildableHalfSize = new Vector2(30f, 22f);
        [Tooltip("Camera target bounds (half extents).")]
        public Vector2 cameraHalfSize = new Vector2(34f, 26f);
        public GameObject terrainPrefab;
        public GameObject waterPrefab;
        public List<WorldProp> props = new List<WorldProp>();
        public Color fogColor = new Color(0.78f, 0.9f, 1f);
        public Color ambientSky = new Color(0.72f, 0.8f, 0.95f);
        public Color ambientEquator = new Color(0.7f, 0.78f, 0.68f);
        public Color ambientGround = new Color(0.45f, 0.5f, 0.38f);
        public Color sunColor = new Color(1f, 0.96f, 0.88f);
        public Vector3 sunEuler = new Vector3(48f, -35f, 0f);
    }
}
