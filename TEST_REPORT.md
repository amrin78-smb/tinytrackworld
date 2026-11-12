# Test Report: 0.2.0 (2026-11-12)

This report separates **automated verification** (run in this repo) from **hardware testing** (on a phone). Nothing
here is claimed for hardware unless it was actually run on one.

## Automated tests (`Tools/run_tests.sh all`, Unity 6000.3.27f2, batch mode)

| Suite | Result |
|---|---|
| EditMode | **36 / 36 passed**: track shapes, graph links, snapping, duplicates and overlaps, open ends, validation, loops, junction switching, train spine traversal, dead ends, reversal, carriage following, save round-trip, corrupted and future-version saves, missing lists |
| PlayMode | **6 / 6 passed** (+1 explicit screenshot capture): starter world (closed loop and train), full train lap and stop, building a loop through the placement controller then save and reload, undo and redo, every narrator line has captions and clips in both languages, **the guided tour completes with no input at all** (proves it cannot soft-lock: 13 steps, each hinted up to 3 times and then performed by the guide), the help button speaks the right tip per mode |
| Content validation (`Tools/setup.sh`) | OK: 21 track pieces, 6 trains, 40 decorations, 32 icons, 238 world props, 23 narrator lines × 2 languages, caption font |

## Screenshot QA (`Tools/showcase.sh` → `Logs/Showcase/`)

13 in-game captures reviewed: menu, train overview, follow, carriages, build ghost, special pieces (bridge, new
tunnel, junction, ramp, elevated, crossing), decorate, explore (farm, village), the guide on the menu, a build tip with
the hand, a Thai caption, and the grown-ups' panel. Issues found and fixed in this round:

* the piece tray was anchored to the screen centre and covered the mode tabs;
* the caption bubble overlapped the help button;
* the help button drew over the grown-ups' panel;
* a decoration could be placed inside the station building.

## Narrator voice check

All 46 clips were transcribed back with Whisper (small).

* **English:** all lines match the script. "Uh-oh" was misheard, so that line was reworded and regenerated.
* **Thai:** recognisable, but Whisper-small produces tone and vowel slips (for example แตะ heard as แต่). Its Thai
  accuracy is limited, so **a native speaker should listen to the Thai lines**. Not yet done.

## APK verification (`Tools/verify_apk.sh`)

Universal (armeabi-v7a + arm64-v8a), ARMv7-only and ARM64-only APKs: correct `libil2cpp.so` per ABI (checked with
`file`), GLES 3.0 required, landscape, **no INTERNET permission**, version 0.2.0 (2). See BUILD_NOTES.md.

## Hardware testing

| Device | Status |
|---|---|
| Xiaomi Redmi A3 (target) | **Not yet tested by me.** The phone was made available over wireless debugging during this session but is not paired with the build machine yet. |
| The owner's phone (model not recorded) | The owner reported that 0.1.0 installs and plays. They also noted there were no instructions, which led to the narrator and tour in 0.2.0. |
| Xiaomi Mi Box 4 | Cannot run the game (GLES 2.0 only); not a target. |

Still to do on the Redmi A3:

* first launch;
* close and relaunch (the PowerVR issue);
* frame rate on the Low preset;
* touch feel and button sizes;
* narrator audio level against the music;
* memory over 15 minutes of play;
* save survives an app restart.

## Master-prompt regression list

| Check | Automated | On device |
|---|---|---|
| Launch, enter world, move camera | PlayMode (scene and camera), screenshots | pending |
| Build straight, curves, connect, loop | EditMode + PlayMode | pending |
| Junction | EditMode (switching, traversal) | pending |
| Place, start, stop train; whistle, bell, speed | PlayMode (lap, stop, guide tour drives whistle and speed) | pending |
| Delete and rebuild track | EditMode + PlayMode (undo/redo) | pending |
| Place decorations, animals react | PlayMode (tour places one); screenshots | pending |
| Save, restart, load | PlayMode save/apply; EditMode corruption | pending (real restart) |
| No train through disconnected track | EditMode (dead end braking and spine) | — |

## Known issues and limitations

* The Thai voice still needs a native speaker to listen to it.
* Captions use legacy uGUI text, so Thai tone marks may sit slightly differently from a full shaping engine (they read
  correctly in the screenshots).
* When the guide auto-places track, the track is placed where the ghost was. In the closed starter loop that is a
  free spot near the view centre; if it does not fit, the guide skips that step instead of retrying.
* APKs are debug-signed.
* Performance has not been profiled on the Redmi A3. The Low preset is selected automatically on 32-bit devices.
