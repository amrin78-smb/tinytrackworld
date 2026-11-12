using System.Collections.Generic;
using TinyTracks.Core;
using UnityEngine;

namespace TinyTracks.Audio
{
    public enum AudioChannel { Music, Sfx, Ambient }

    /// <summary>
    /// Music, ambience and pooled one-shot effects with separate volumes. A per-clip cooldown stops a toddler's
    /// rapid taps from stacking the same sound into a loud wall.
    /// </summary>
    public class AudioManager : MonoBehaviour
    {
        public static AudioManager Instance { get; private set; }

        public AudioConfig config;
        public int poolSize = 10;
        public float sameClipCooldown = 0.12f;

        private AudioSource music, ambient;
        private readonly List<AudioSource> pool = new List<AudioSource>();
        private readonly Dictionary<AudioClip, float> lastPlayed = new Dictionary<AudioClip, float>();
        private int next;

        public float MusicVolume { get; private set; } = 0.45f;
        public float SfxVolume { get; private set; } = 0.8f;
        public float AmbientVolume { get; private set; } = 0.5f;

        private void Awake()
        {
            Instance = this;
            music = gameObject.AddComponent<AudioSource>();
            music.loop = true;
            music.playOnAwake = false;
            music.priority = 0;
            ambient = gameObject.AddComponent<AudioSource>();
            ambient.loop = true;
            ambient.playOnAwake = false;
            ambient.priority = 10;
            for (int i = 0; i < poolSize; i++)
            {
                AudioSource s = gameObject.AddComponent<AudioSource>();
                s.playOnAwake = false;
                pool.Add(s);
            }
            if (config != null)
            {
                MusicVolume = config.defaultMusic;
                SfxVolume = config.defaultSfx;
                AmbientVolume = config.defaultAmbient;
            }
        }

        public void SetVolumes(float musicV, float sfxV, float ambientV)
        {
            MusicVolume = Mathf.Clamp01(musicV);
            SfxVolume = Mathf.Clamp01(sfxV);
            AmbientVolume = Mathf.Clamp01(ambientV);
            music.volume = MusicVolume * 0.6f;
            ambient.volume = AmbientVolume * 0.7f;
        }

        public void StartBackground()
        {
            if (config == null) return;
            if (config.music != null && music.clip != config.music) { music.clip = config.music; music.Play(); }
            if (config.ambience != null && ambient.clip != config.ambience) { ambient.clip = config.ambience; ambient.Play(); }
            SetVolumes(MusicVolume, SfxVolume, AmbientVolume);
        }

        public void Play(AudioClip clip, float volume = 1f, float pitch = 1f)
        {
            if (clip == null || SfxVolume <= 0.001f) return;
            float now = Time.unscaledTime;
            if (lastPlayed.TryGetValue(clip, out float t) && now - t < sameClipCooldown) return;
            lastPlayed[clip] = now;
            AudioSource s = pool[next];
            next = (next + 1) % pool.Count;
            s.pitch = pitch;
            s.volume = volume * SfxVolume;
            s.clip = clip;
            s.Play();
        }

        /// <summary>Plays with a tiny random pitch so repeated taps sound lively, not robotic.</summary>
        public void PlayVaried(AudioClip clip, float volume = 1f) => Play(clip, volume, Random.Range(0.94f, 1.06f));

        public bool IsPlaying(AudioClip clip)
        {
            foreach (AudioSource s in pool) if (s.isPlaying && s.clip == clip) return true;
            return false;
        }

        /// <summary>Creates a looping source owned by the caller (train engine, crossing bell) that follows SFX volume.</summary>
        public AudioSource CreateLoop(GameObject owner, AudioClip clip)
        {
            AudioSource s = owner.AddComponent<AudioSource>();
            s.clip = clip;
            s.loop = true;
            s.playOnAwake = false;
            s.spatialBlend = 0f;
            s.volume = 0f;
            return s;
        }

        public static void Sfx(AudioClip clip, float volume = 1f)
        {
            if (Instance != null) Instance.PlayVaried(clip, volume);
        }

        public static AudioConfig Clips => Instance != null ? Instance.config : null;

        private void OnApplicationPause(bool paused)
        {
            if (paused) { music.Pause(); ambient.Pause(); }
            else { music.UnPause(); ambient.UnPause(); }
        }
    }
}
