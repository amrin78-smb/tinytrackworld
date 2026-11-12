using TinyTracks.Audio;
using TinyTracks.Core;
using TinyTracks.World;
using UnityEngine;

namespace TinyTracks.Interaction
{
    /// <summary>
    /// Something a child can tap: animals make their sound and nod, trees sway, houses bounce and glow, the windmill
    /// spins faster, the station chimes. Parts are found by name (Head, Tail, Canopy, Sails, WingL/WingR, ArmL/ArmR).
    /// </summary>
    public class Interactable : MonoBehaviour
    {
        public TapReaction reaction = TapReaction.Wobble;
        public AudioClip sound;
        [HideInInspector] public int decorationId;

        private Transform head, tail, canopy, sails, armL, armR;
        private float cooldown;

        private void Awake()
        {
            foreach (Transform t in GetComponentsInChildren<Transform>(true))
            {
                switch (t.name)
                {
                    case "Head": head = t; break;
                    case "Tail": tail = t; break;
                    case "Canopy": canopy = t; break;
                    case "Sails": sails = t; break;
                    case "ArmL": armL = t; break;
                    case "ArmR": armR = t; break;
                }
            }
        }

        private void OnEnable() => AmbientAnimator.Register(this, head, tail, canopy, sails);
        private void OnDisable() => AmbientAnimator.Unregister(this);

        public void OnTap()
        {
            if (Time.unscaledTime < cooldown) return;
            cooldown = Time.unscaledTime + 0.35f;
            AudioConfig clips = AudioManager.Clips;
            switch (reaction)
            {
                case TapReaction.Animal:
                    AudioManager.Sfx(sound, 0.9f);
                    Juice.Bounce(transform, 0.3f, 0.45f);
                    if (head != null) Juice.Wobble(head, 18f, 0.7f);
                    if (tail != null) Juice.Wobble(tail, 30f, 0.8f);
                    break;
                case TapReaction.Bird:
                    AudioManager.Sfx(sound != null ? sound : clips?.tweet, 0.8f);
                    Juice.Bounce(transform, 0.5f, 0.5f);
                    break;
                case TapReaction.Person:
                    AudioManager.Sfx(sound != null ? sound : clips?.button);
                    Juice.Bounce(transform, 0.35f, 0.45f);
                    if (armR != null) Juice.Wobble(armR, 50f, 0.9f);
                    if (armL != null) Juice.Wobble(armL, 30f, 0.9f);
                    break;
                case TapReaction.Tree:
                    AudioManager.Sfx(clips?.placeDecor, 0.6f);
                    Juice.Wobble(canopy != null ? canopy : transform, 9f, 0.9f);
                    break;
                case TapReaction.House:
                    AudioManager.Sfx(sound != null ? sound : clips?.trackSnap, 0.7f);
                    Juice.Squash(transform, 0.1f, 0.45f);
                    break;
                case TapReaction.Windmill:
                    AudioManager.Sfx(clips?.buttonToggle);
                    AmbientAnimator.BoostSpin(this, 6f);
                    Juice.Squash(transform, 0.05f, 0.4f);
                    break;
                case TapReaction.Station:
                    AudioManager.Sfx(clips?.stationChime, 0.8f);
                    Juice.Squash(transform, 0.06f, 0.4f);
                    break;
                case TapReaction.Wobble:
                    AudioManager.Sfx(sound != null ? sound : clips?.button);
                    Juice.Wobble(transform, 8f, 0.5f);
                    break;
            }
        }
    }
}
