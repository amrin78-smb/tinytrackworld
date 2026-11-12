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
| 6 | UI and toddler UX | **Tested** | Picture-only buttons of 130–300 px, hold-to-confirm for risky actions, parent-gated settings. **0.2.0: spoken narrator (English and Thai) with caption and animated hand, a first-play guided tour that cannot soft-lock (PlayMode test), free-play tips, a help button and event reactions.** Screenshot QA done; **not yet tried by a toddler.** |
| 7 | Audio and animations | **Implemented** | 27 synthesised sounds + music + ambience + 46 narrator clips (EN and TH, checked by Whisper transcription; Thai still needs a native listener), music ducks under the voice, pop/wobble/bounce feedback. Loudness checked numerically but **not by ear**. |
| 8 | Save system | **Tested** | Versioned JSON, atomic write + backup, corruption fallback, autosave. EditMode parse/corruption tests and a PlayMode round-trip. A restart on a real device is not yet tested. |
| 9 | Visual polish | **Tested** | Blender models (trains, creatures, buildings, nature, tracks) and 3D icons; tunnel remodelled in 0.2.0 (rounded hill, stone portals). Screenshot QA. Remaining: grain and noise detail on joined extras (minor). |
| 10 | Performance optimisation | **Tested** (2 devices) | Low/Medium/High presets, auto Low on 32-bit or <4.5 GB RAM, FPS governor, one shared material (SRP batcher), pooling. Measured: TCL tablet Low 30 FPS with flat memory (~255 MB) over 4 minutes; S23 Ultra High 60 FPS. **Not yet profiled on the Redmi A3.** |
| 11 | QA and Android release | **Tested** (2 real devices) | 0.2.1: universal APK (ARMv7 + ARM64) verified by inspection and run on a TCL tablet (Android 15, Low, 30 FPS, memory flat, relaunch and save OK) and a Galaxy S23 Ultra (Android 16, High, 60 FPS; 32-bit path forced and working). Five device-only bugs found and fixed. **Redmi A3 / PowerVR still pending.** See TEST_REPORT.md. |

## Next steps

1. Install on a Redmi A3: first launch, the close-and-relaunch test (PowerVR), touch feel, FPS on Low, and a
   memory check over 15 minutes.
2. Watch a toddler play. Tune the ghost tap radius, the camera pan speed and the guide's hint timing (9 s repeat, 3 hints before it helps).
3. A native Thai speaker listens to the Thai narrator lines; replace any clip by dropping a WAV with the same name into `Audio/Voice/th/`.
4. Polish: grain and noise detail on joined extras, more track variety in the trays.
5. Future (GDD §17): several trains, signalling, more worlds (WorldDefinition + terrain settings + layout).
