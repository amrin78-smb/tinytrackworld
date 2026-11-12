# Changelog

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
