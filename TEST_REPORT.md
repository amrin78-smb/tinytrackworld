# Test Report: 0.2.1 (2026-11-12)

This report separates **automated verification** (run in this repo) from **hardware testing** (on a phone). Nothing
here is claimed for hardware unless it was actually run on one.

## Automated tests (`Tools/run_tests.sh all`, Unity 6000.3.27f2, batch mode)

| Suite | Result |
|---|---|
| EditMode | **36 / 36 passed**: track shapes, graph links, snapping, duplicates and overlaps, open ends, validation, loops, junction switching, train spine traversal, dead ends, reversal, carriage following, save round-trip, corrupted and future-version saves, missing lists |
| PlayMode | **7 / 7 passed** (+1 explicit screenshot capture). New in 0.2.1: the starter train is a real, visible locomotive, and in the closed starter loop every piece type gets a placeable ghost. Also: starter world (closed loop and train), full train lap and stop, building a loop through the placement controller then save and reload, undo and redo, every narrator line has captions and clips in both languages, **the guided tour completes with no input at all** (proves it cannot soft-lock: 13 steps, each hinted up to 3 times and then performed by the guide), the help button speaks the right tip per mode |
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

## Hardware testing (0.2.1)

| Device | Build | Result |
|---|---|---|
| **TCL 8183A tablet**: Android 15, Helio G85 / Mali-G52 MC2, 4 GB, 1280×800, arm64-only | ARM64 | **Pass.** Auto **Low** preset, **30 FPS** (the Low cap). Full guided tour played with real taps: Play, GO, whistle by tapping the train, faster, build tab, pick a piece, place it (✓), decorate, place a tree, back to the train. The "lead back" step was also checked (switching to Build before pressing GO). **Memory flat at 253–256 MB PSS over 4 minutes** of driving. Closed and relaunched twice: cold start 0.3 s, the saved world reloaded with the added piece and tree, and the tour did not replay. No errors in logcat. |
| **Galaxy S23 Ultra**: Android 16, Snapdragon 8 Gen 2 / Adreno 740, 8 GB, 2316×1080 (21:9) | ARM64 / universal | **Pass.** Auto **High**, **60 FPS**. The UI fits the 21:9 screen and the camera cutout area is kept clear. The universal APK installs as arm64-v8a with no warnings. |
| Galaxy S23 Ultra, **forced 32-bit** | ARMv7-only | **Runs:** Unity reports `armeabi-v7a`, auto Low, the tour and train work, about 328 MB PSS. Android 16 shows its standard "not compatible with the latest version of Android" warning for 32-bit-only apps on 64-bit phones, which is why only the universal APK ships. |
| **Xiaomi Redmi A3** (target, 32-bit, PowerVR GE8320) | — | **Not tested yet** (not paired). The S23 32-bit run exercises the same ARMv7 code, but not the PowerVR GPU. |
| The owner's phone (model not recorded) | 0.1.0 | The owner reported that it installs and plays. |

Bugs found on hardware and fixed in 0.2.1:

* the starter train was invisible on a fresh install;
* the first track piece appeared across existing track on the closed loop and couldn't be placed;
* the UI was clipped on 16:10;
* a code-stripping error;
* the game was drawn under the status bar.

Still to do on the Redmi A3:

* first launch;
* close and relaunch (the PowerVR issue);
* frame rate on Low;
* memory over 15 minutes;
* touch feel.

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
* **Android status bar stays visible** on Android 15/16 (TCL tablet, S23). The game is laid out below it rather than
  under it. Hiding it needs either Unity support for edge-to-edge immersive mode or an Android plugin; the sibling
  Unity games use the same settings. A runtime `WindowInsetsController.hide` attempt was overridden by Unity.
* The track ghost is a faint green against the grass, and the hint hand points slightly below the ghost's centre.
* Performance has not been profiled on the Redmi A3. The Low preset is selected automatically on 32-bit devices.
