# Procedural audio

Every sound in `Assets/_Project/Audio/` is made from scratch by `synth_audio.py` using numpy. There are no samples and no network access. The output is deterministic, with one seed per sound name, so you can re-run it as often as you like. Files are 16-bit, 44.1 kHz WAV: SFX are mono, while ambience and music are stereo.

```
PY=~/.local/opt/blender-5.2.3-linux-x64/5.2/python/bin/python3.13   # any Python with numpy
$PY Tools/audio/synth_audio.py              # regenerate everything (~1 min, music is most of it)
$PY Tools/audio/synth_audio.py moo whistle  # regenerate only some sounds
$PY Tools/audio/check_audio.py [-v] [names] # peak/RMS/DC/fades/loop seams + pitch track
```

| File | What it is |
|---|---|
| SFX/whistle | Two-blast A-major steam whistle with a breathy noise and pitch scoop, low-passed so it isn't shrill |
| SFX/bell | Three dings of a small train bell (inharmonic modal partials) |
| SFX/chug_loop | 1 s loop of 4 steam chuffs (CHUFF-chuff-CHUFF-chuff) |
| SFX/rolling_loop | 2 s loop of a wooden clickety-clack plus a low rumble |
| SFX/motor_loop | 1.5 s gentle electric/diesel hum for non-steam engines |
| SFX/track_place / track_snap / track_remove | Wooden clonk / click plus a tiny chime / soft pop with a whoosh |
| SFX/switch_flip | Wooden click-clack |
| SFX/invalid | Gentle two-note descending "boop-boop" |
| SFX/button / button_toggle / undo | Bubbly pop / two-note blip / reverse whoosh |
| SFX/place_decor / puff | Bloop with a sparkle / smoke puff |
| SFX/station_chime | Ding-dong-ding (E5 C5 G5 vibraphone tones) |
| SFX/crossing_bell | 1 s loop of a level-crossing ding-ding |
| SFX/tada | Short C-major arpeggio and chord fanfare |
| SFX/moo baa cluck bark meow neigh | Animal voices made by source-filter synthesis: a harmonic source shaped by time-varying formants, with pitch contours, vibrato or tremolo, jitter and breath noise |
| SFX/tweet | Bird chirps and a little trill |
| Ambient/countryside_loop | 24 s stereo loop of wind, leaf rustle and distant birds (quiet) |
| Music/music_loop | 57.6 s stereo loop at 100 bpm: C-G-Am-F, Karplus-Strong ukulele, marimba melody, soft bass, shaker and reverb |

How it works:

- **Loops** (`*_loop`, `crossing_bell`) are built circularly. Events wrap modulo the loop length, noise is filtered in the FFT domain over exactly one period, and the reverb is circular. The seam is therefore continuous by construction and needs no crossfade.
- **One-shots** get a 5 ms fade-in and a 10 ms fade-out. Every file is high-passed at 25 Hz and has its DC offset removed.
- **Levels:**
  - Each sound is peak-normalised to the target in the `SOUNDS` table: animals and the whistle at -6, UI sounds at -10, loops at -10 to -12, ambience at -14 and music at -6 dBFS.
  - SFX are then capped so that their loudest 100 ms is no more than `LOUDNESS_CAP_DB` (6 dB) above `button`. Because of this cap, some peaks end up below their targets.
- To tweak a sound, edit its `s_<name>` function and re-run the script with that name.
