# Development Plan and Milestone Checklist

Statuses: **Pending**, **In progress**, **Implemented** (code exists), **Tested** (automated tests or screenshot QA
ran against it), **Verified** (confirmed on the target hardware). Nothing is marked Verified until it has run on a
Redmi A3.

| # | Milestone | Status | Evidence / notes |
|---|---|---|---|
| 0 | Environment audit and technical validation | **Tested** | Unity 6000.3.27f2 with Android Build Support, IL2CPP, NDK r27c, SDK and OpenJDK 17. ARMv7 + ARM64 IL2CPP player libraries present. Blender 5.2.3. Device: only a Mi Box 4 (GLES 2.0, so it can't run Unity 6); no Redmi A3 attached. See BUILD_NOTES.md. |
| 1 | Core foundation (scene, world, camera, touch, state, UI, audio, performance) | **Tested** | Generated scene; terrain, lake and dressing; orbit camera (pan, zoom, twist, follow, reset, bounds); InputManager; GameManager modes; AudioManager; PerformanceManager. PlayMode + screenshots. |
| 2 | Track building engine | **Tested** | TrackShapeLibrary, TrackGraph, TrackSnapping, TrackNetworkManager and TrackPlacementController (ghost, snap, rotate, move, delete, undo, redo, validation). 29 EditMode graph/spine tests plus a PlayMode "four taps make a circle" test. |
| 3 | Train movement engine | **Tested** | TrainSpine (graph traversal, junctions, dead ends, reverse, carriages following the exact route), TrainController (braking, stations, crossings, wheels, smoke, audio), TrainManager. EditMode tests + PlayMode full lap + screenshots. |
| 4 | Track and world expansion | **Tested** | Wooden and stone bridges, tunnel, ramp, elevated track with auto pillars, station, depot, level crossing with barriers; animals, people, birds, clouds, windmill, tree sway. The crossing-barrier lowering animation has not been seen on screen yet. |
| 5 | Decoration sandbox | **Tested** | 38 placeable items in 5 categories: place, rotate, move (long-press), delete and undo. Screenshot QA; save round-trip in PlayMode. |
| 6 | UI and toddler UX | **Implemented** | Picture-only buttons of 130–300 px, hold-to-confirm for risky actions, parent-gated settings, hint hand. Screenshot QA done; **not yet tried by a toddler.** |
| 7 | Audio and animations | **Implemented** | 27 synthesised sounds + music + ambience, pop/wobble/bounce feedback. Loudness was checked numerically but **not by ear**. |
| 8 | Save system | **Tested** | Versioned JSON, atomic write + backup, corruption fallback, autosave. EditMode parse/corruption tests and a PlayMode round-trip. A restart on a real device is not yet tested. |
| 9 | Visual polish | **In progress** | Blender models (trains, creatures, buildings, nature, tracks) and 3D icons are done. Pending: tunnel hill shape and the remaining shared-helper issues (see TEST_REPORT known issues). |
| 10 | Performance optimisation | **Implemented** | Low/Medium/High presets, auto Low on 32-bit or <4.5 GB RAM, FPS governor, one shared material (SRP batcher), pooling. **Not profiled on a Redmi A3.** |
| 11 | QA and Android release | **In progress** | Universal release APK (ARMv7 + ARM64) built 2026-11-12 and verified by inspecting the APK (both IL2CPP libs, GLES3, landscape, no INTERNET), published as GitHub release v0.1.0. Debug-signed. Separate ARMv7-only and ARM64-only APKs not built yet. Hardware testing on the Redmi A3 is pending. |

## Next steps

1. Install on a Redmi A3: first launch, the close-and-relaunch test (PowerVR), touch feel, FPS on Low, and a
   memory check over 15 minutes.
2. Watch a toddler play. Tune the ghost tap radius, the camera pan speed and the hint timing.
3. Polish: tunnel hill, grain and noise detail on joined extras, more track variety in the trays.
4. Future (GDD §17): several trains, signalling, more worlds (WorldDefinition + terrain settings + layout).
