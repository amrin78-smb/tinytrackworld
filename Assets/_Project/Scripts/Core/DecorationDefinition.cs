using System;
using System.Collections.Generic;
using TinyTracks.Tracks;
using UnityEngine;

namespace TinyTracks.Core
{
    public class DecorationDefinition : ScriptableObject
    {
        public string id;
        public string displayName;
        public DecorationCategory category;
        public Sprite icon;
        public GameObject prefab;
        public float footprintRadius = 0.6f;
        public float height = 1f;
        public TapReaction reaction = TapReaction.Wobble;
        public AudioClip sound;
        [Tooltip("Shown in the decorate toolbar (some world-only models are not).")]
        public bool placeable = true;
        [Tooltip("Skipped on the Low graphics preset when part of the world dressing.")]
        public bool lowDetailOptional;
    }

    [Serializable]
    public struct WorldProp
    {
        public string decorationId;
        public Vector3 position;
        public float yaw;
        public float scale;
    }
}
