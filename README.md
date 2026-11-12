# Tiny Tracks World

*Build it. Connect it. Ride it. Explore it.* A toddler-friendly (ages 2–5) 3D toy-railway sandbox for Android,
built with Unity 6. Children snap wooden track pieces together, pick a friendly locomotive and carriages, press GO,
and watch it travel through the Sunny Valley countryside. There are no fail states, timers, ads, accounts, network
access or reading. A friendly conductor explains everything out loud (English or Thai), and a hand shows where to
tap.

| | |
|---|---|
| Engine | Unity **6000.3.27f2**, URP 17.3, Input System, uGUI |
| Platform | Android, landscape, offline; **ARMv7 (32-bit) + ARM64**, IL2CPP, OpenGL ES 3.0 (Vulkan not used) |
| Target | Xiaomi Redmi A3 (32-bit Android, PowerVR GE8320); Low preset at 30 FPS |
| Art | Original models scripted in **Blender 5.2** (`Tools/blender`), audio synthesised offline (`Tools/audio`), narrator voice generated offline with Kokoro TTS (English) and VachanaTTS (Thai) (`Tools/voice`) |

## Quick start

```bash
Tools/setup.sh                 # regenerate settings, materials, prefabs, definitions, scene (after art/code changes)
Tools/run_tests.sh all         # EditMode + PlayMode tests
Tools/showcase.sh              # in-game screenshots -> Logs/Showcase/*.png
Tools/build_android.sh dev     # development APK (ARMv7+ARM64) + verification
Tools/build_android.sh all     # release: universal + armv7-only + arm64-only APKs, each verified
adb install -r Builds/Android/TinyTracksWorld-universal.apk
```

Regenerate art (optional, needs Blender on PATH; outputs are committed):

```bash
blender -b --factory-startup --python Tools/blender/models/build_tracks.py      # 21 track pieces (from track_shapes.json)
blender -b --factory-startup --python Tools/blender/models/build_trains.py      # 4 locos + 2 carriages
blender -b --factory-startup --python Tools/blender/models/build_creatures.py   # 7 animals + 3 people
blender -b --factory-startup --python Tools/blender/models/build_env.py         # 33 trees/buildings/props
blender -b --factory-startup --python Tools/blender/icons/build_icons.py        # 31 UI icons
blender -b --factory-startup --python Tools/blender/render_thumbs.py            # toolbar thumbnails
~/.local/opt/blender-5.2.3-linux-x64/5.2/python/bin/python3.13 Tools/audio/synth_audio.py   # all sounds + music
Tools/voice/generate_voice.sh [key...]   # narrator clips from Tools/voice/voice_lines.json (EN + TH), then Tools/setup.sh
```

## How to play (grown-ups' guide)

* **The conductor (narrator):** on the first play a short guided tour runs: drive the train, whistle, go faster, lay a
  piece of track, place a decoration, and back to the train. Each step is spoken, captioned and shown by an animated
  hand. If the child does nothing, the hint repeats every 9 s and after three hints the conductor does the step for
  them, so the tour can never get stuck. Afterwards the conductor gives a short spoken tip when a mode is first
  opened, again if the child seems stuck, and reacts to events (end of the track, a finished loop, a station stop, a
  piece that doesn't fit). Tap the **conductor button** at any time to hear what to do, or tap the caption to repeat
  it. In the grown-ups' panel you can set the voice volume and language (Auto, English or ไทย) and replay the tour
  ("Show me how").

* **Home screen:** the big green ▶ plays. Tap a locomotive below to choose it. Hold the sprout for 1.5 s to start a
  new world. Hold the gear for 2 s to open the grown-ups' settings (volumes, voice, language, graphics, replay tour).
* **Build (hammer):** pick a piece and a see-through ghost appears at the end of the railway (green means it fits,
  red means it doesn't). Tap the ghost, or the same piece button again, to lay it; keep tapping to grow the line.
  Drag the ghost anywhere and it snaps to nearby ends; let go to place it. Rotate swaps left/right. Long-press a
  piece to pick it up and move it. The bin toggles delete mode. Undo and redo are available. Tap a junction to
  flip it. Hold the broom to clear everything (this can be undone).
* **Train:** GO / STOP / whistle / bell, turtle and rabbit for speed, and the camera button to follow the train. Pick
  a locomotive and add or remove passenger and cargo carriages. Trains stop safely at the end of the track (a yellow
  "!" marks the gap); press GO and the train turns round. Trains pause at stations and lower crossing barriers.
* **Passengers and cargo:** passengers wait at stations and ride in the passenger carriage. Build a **Cargo
  Station** (station tray) and add a cargo wagon: the crane loads crates, logs, milk or hay, and unloads them on the
  next visit.
* **More trains:** the green "+" adds a train (up to three). Tap a train, or its chip, to drive it; hold a chip to
  send that train away. Trains keep their distance by themselves.
* **Paint:** the paintbrush opens colours for the selected train; the curly arrow restores its own colours.
* **Worlds:** pick Sunny Valley or Snowy Valley at the top left of the home screen. Each world keeps its own
  railway.
* **Surprises:** after a while of play a gift box appears; tap it to meet a new friend (or a new train).
* **Decorate (tree):** trees, flowers, buildings, animals, people and props are placed the same way as track.
* **Explore (magnifier):** tap animals, trees, houses and the windmill for sounds and animations; tap the train to
  make it whistle.

The world saves automatically (`world.json` in the app's private storage).

## Documents

[GDD.md](GDD.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) ·
[BUILD_NOTES.md](BUILD_NOTES.md) · [TEST_REPORT.md](TEST_REPORT.md) · [CHANGELOG.md](CHANGELOG.md) ·
[Docs/MASTER_DEVELOPMENT_PROMPT.md](Docs/MASTER_DEVELOPMENT_PROMPT.md)
