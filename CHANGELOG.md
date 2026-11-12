# Changelog

## 0.2.1: first real-device fixes (2026-11-12)

Tested on a TCL 8183A tablet (Android 15) and a Galaxy S23 Ultra (Android 16, 64-bit and forced 32-bit).

### Fixed
- **Invisible train on a fresh install:** the default locomotive was chosen after the starter world placed its
  train, so the train had no model. It is now chosen in `Awake` (plus a PlayMode regression test).
- **Red ghost on the closed starter loop:** with no open end, the first piece appeared across existing track and
  could not be placed (the tour said "tap the green track"). The ghost now goes to the nearest free spot, or to
  another open end, so it is always placeable (plus a PlayMode test).
- **UI cut off on 16:10 tablets:** the canvas now uses Expand scaling, so the full layout fits any aspect ratio
  (16:10 tablets to 21:9 phones).
- **Smoke-puff mesh error:** `CreatePrimitive` needed a class removed by code stripping; the sphere is now built in
  code.
- **Status bar covering the game:** the game now sits below the status bar (targets SDK 35 with Android's
  edge-to-edge opt-out). The bar itself is still shown on Android 15/16; see Known issues.
- "Show me how" no longer shows a selection ring.

### Changed
- Releases ship one **universal APK** (ARMv7 + ARM64). Android picks the right code, so 64-bit phones run 64-bit
  (no 32-bit warning) and 32-bit phones such as the Redmi A3 run ARMv7. `Tools/build_android.sh armv7|arm64|all`
  can still make split APKs.

## 0.2.0: the conductor explains how to play (2026-11-12)

### Added
- Narrator ("the conductor"): 23 spoken lines in English and Thai (generated offline with Kokoro TTS and VachanaTTS,
  checked by transcribing them back with Whisper), a caption bubble (Mitr font, SIL OFL) and an animated tap/drag hand.
- First-play guided tour: drive, whistle, go faster, build, decorate, back to the train. Hints repeat when idle and
  the conductor does the step after three hints, so the tour can never get stuck. It can be replayed from the
  grown-ups' panel ("Show me how").
- Free-play guidance: a spoken tip on first entering each mode and when the child seems stuck, the conductor button
  for help at any time, and spoken reactions (end of track, loop finished, station stop, "doesn't fit", new train).
- Grown-ups' panel: voice volume and language (Auto, English, ไทย). Music dips while the conductor speaks.
- Narrator icon. Release APKs for ARMv7-only and ARM64-only alongside the universal APK.

### Changed
- Tunnel piece remodelled: a smooth rounded hill with stone-block portals, bushes, rocks and flowers.
- Piece trays now sit just above the toolbar and are only as wide as their buttons (previously they could cover the
  mode tabs).
- Decorations can no longer be placed inside the station, depot or crossing buildings.

### Fixed
- The release APK requested the INTERNET permission (Unity adds it to its generated manifest); a build step now
  removes it and the APK check verifies it.

## 0.1.0: first playable (2026-11-12)

### Added
- Unity 6000.3.27f2 project with URP, Input System and uGUI. Android settings: IL2CPP, ARMv7 + ARM64, OpenGL ES 3.0
  only, landscape, min SDK 25, no INTERNET permission.
- Railway engine: 21 track pieces (straights, gentle and tight curves, S-curves, three junctions, cross, buffer stop,
  wooden and stone bridges, tunnel, ramp, elevated straight, station, depot, level crossing). Graph-based connections,
  forgiving snapping, overlap and duplicate checks, and validation.
- Toddler build flow: ghost preview, tap-to-place chains, drag and release, rotate, long-press to move, delete mode,
  undo/redo, and clear (hold).
- Trains: four original locomotives (Classic Red Express, Blue Adventure, Green Explorer, Yellow Sunshine) and
  passenger and cargo carriages. Bogie-based movement along the graph, smooth braking at dead ends, reversing, station
  stops, level crossings, spinning wheels, smoke, and speed-following engine sounds.
- Sunny Valley: procedural terrain and lake; farm, village, forest, windmill, clouds and birds. Tap reactions for
  animals, trees, houses, the windmill, the station and people.
- Decorate mode with 38 items.
- Original art scripted in Blender 5.2: 70 models (21 track pieces, 6 trains, 10 creatures, 33 environment), 31
  3D-rendered icons and model thumbnails. All audio synthesised offline (27 sounds, music, ambience).
- Save system: versioned JSON, atomic writes with backup, corruption fallback and autosave. Grown-ups' settings
  (volumes, graphics preset, FPS display), opened by holding the gear.
- Tests: 36 EditMode and 3 PlayMode tests, plus screenshot showcase capture and APK verification tooling.
