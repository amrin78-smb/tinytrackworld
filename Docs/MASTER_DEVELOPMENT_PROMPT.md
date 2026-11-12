# PART 2 --- CLAUDE CODE MASTER DEVELOPMENT PROMPT

# PROJECT: TINY TRACKS WORLD

## Unity 6 --- Android Toddler Train Building Sandbox

You are the lead Unity 6 game developer, gameplay engineer, technical
architect, 3D game designer, UI/UX designer, and QA engineer responsible
for delivering a complete, playable Android game called TINY TRACKS
WORLD.

Develop this game from the ground up into a polished, production-quality
toddler-friendly 3D railway sandbox.

Take ownership of the complete development lifecycle.

Do not merely generate scripts or provide instructions. Inspect the
environment, create the project structure, implement features, integrate
systems, build the game, test it, and resolve problems.

The GDD in Part 1 is the primary product specification. Follow it
throughout development.

If a design decision is not explicitly covered, use sensible
professional judgement while preserving the toddler-first philosophy.

------------------------------------------------------------------------

# 1. PROJECT IDENTITY

-   Game: Tiny Tracks World
-   Tagline: Build it. Connect it. Ride it. Explore it.
-   Engine: Unity 6
-   Platform: Android
-   Game type: 3D Creative Sandbox
-   Target audience: Ages 2--5
-   Primary test device: Xiaomi Redmi A3
-   Critical compatibility: Android 32-bit ARMv7 AND ARM64
-   Orientation: Landscape
-   Camera: Elevated third-person / isometric perspective
-   Visual style: Colourful, polished, stylised 3D cartoon toy world
-   Connectivity: Offline-first

The game must be fully playable without an internet connection.

Do not introduce advertisements, analytics SDKs, in-app purchases,
account systems, or external services.

# 2. MANDATORY DEVICE COMPATIBILITY

This is a critical project constraint.

The game must run on the Xiaomi Redmi A3, including its 32-bit Android
configuration.

Do not develop exclusively for modern 64-bit Android devices.

## Android build configuration

Configure:

-   Android as the primary platform.
-   ARMv7 (32-bit) compatibility.
-   ARM64 compatibility.
-   IL2CPP scripting backend.
-   OpenGL ES 3.0 graphics baseline.
-   Vulkan must not be mandatory.
-   Landscape orientation.
-   Appropriate minimum Android API level.
-   Appropriate target API level for the selected Unity version.

Before implementation, inspect the installed Unity version, Android
modules, available build targets, and installed toolchains.

Verify that the selected Unity 6 configuration actually supports ARMv7.

Do not silently remove ARMv7 support because of a package or
configuration conflict.

If ARMv7 support is unavailable, investigate the cause and document the
required remediation before proceeding.

Do not claim 32-bit compatibility based solely on a successful ARM64
build.

## Performance requirements

Target 30 FPS on Redmi A3.

Prioritise:

-   Low memory footprint.
-   Fast startup.
-   Responsive touch controls.
-   Minimal loading screens.
-   Lightweight materials.
-   Simple shaders.
-   Baked lighting where appropriate.
-   Limited real-time shadows.
-   Texture compression.
-   Object pooling.
-   Efficient mesh rendering.
-   Frustum and distance culling.
-   Minimal physics usage.

Avoid expensive post-processing, excessive particles, unnecessary
real-time lighting, excessive transparent materials, unoptimised
vegetation, unnecessary Update loops, and expensive per-frame graph
calculations.

Do not sacrifice track visibility or gameplay clarity for visual
effects.

# 3. DEVELOPMENT WORKFLOW

Work in clearly defined milestones.

Do not attempt to implement the entire game in one uncontrolled
operation.

For each milestone:

1.  Inspect the existing project.
2.  Understand the current architecture.
3.  Create an implementation plan.
4.  Implement the required functionality.
5.  Integrate the feature with existing systems.
6.  Compile and resolve errors.
7.  Run available automated tests.
8.  Build the Android APK when appropriate.
9.  Verify the actual implementation.
10. Update project documentation.

Maintain these documents:

-   README.md
-   GDD.md
-   DEVELOPMENT_PLAN.md
-   ARCHITECTURE.md
-   BUILD_NOTES.md
-   TEST_REPORT.md
-   CHANGELOG.md

Maintain a milestone checklist with these statuses:

-   Pending
-   In progress
-   Implemented
-   Tested
-   Verified

Never mark a feature as tested or verified unless the relevant test was
actually performed.

Never replace a functional implementation with a temporary placeholder
and report the feature as complete.

If a feature cannot be completed, document the exact reason and
remaining work.

After each milestone, provide a concise development report.

Do not stop after producing documentation or code skeletons. The
objective is a functioning game.

# 4. PROJECT STRUCTURE

Create a clean, modular Unity project.

Suggested structure:

``` text
Assets/
  _Project/
    Art/
      Environment/
      Trains/
      Tracks/
      Decorations/
      Animals/
      UI/
    Audio/
      Music/
      SFX/
      Ambient/
    Materials/
    Models/
    Prefabs/
      Tracks/
      Trains/
      Environment/
      UI/
      Decorations/
    Scenes/
    Scripts/
      Core/
      Camera/
      Input/
      UI/
      World/
      Tracks/
      Trains/
      Building/
      Interaction/
      Audio/
      SaveSystem/
      Performance/
    ScriptableObjects/
      TrackDefinitions/
      TrainDefinitions/
      DecorationDefinitions/
      WorldDefinitions/
    Settings/
    Tests/
      EditMode/
      PlayMode/
```

Use namespaces consistently.

Keep scripts small, maintainable, and focused on specific
responsibilities.

Avoid tightly coupled monolithic managers.

Use ScriptableObjects for reusable configuration and content
definitions.

# 5. MILESTONE 0 --- ENVIRONMENT AUDIT AND TECHNICAL VALIDATION

Before building gameplay:

1.  Inspect the working directory.
2.  Check whether a Unity project already exists.
3.  Identify the exact Unity editor version.
4.  Verify installed Android Build Support.
5.  Verify ARMv7 build availability.
6.  Verify IL2CPP availability.
7.  Verify Android SDK and NDK configuration.
8.  Check available graphics APIs.
9.  Identify package dependencies.
10. Check target device specifications where available.

If an existing project is present, inspect it and preserve useful work.

If no project exists, create the Unity project.

Produce an environment audit report.

Do not proceed with an incompatible Android configuration without
documenting the problem.

# 6. MILESTONE 1 --- CORE GAME FOUNDATION

Implement:

-   Main game scene.
-   World environment.
-   Camera system.
-   Touch input system.
-   Game state management.
-   Basic UI.
-   Audio manager.
-   Performance manager.

Create an attractive initial environment containing green terrain, blue
sky, clouds, trees, hills, a small lake, farm buildings, and a railway
construction area.

The initial scene must look like a miniature toy world, not an empty
Unity terrain.

## Camera requirements

Implement:

-   Smooth pan.
-   Zoom in/out.
-   Optional rotation.
-   Camera follow mode.
-   Camera reset.
-   Configurable camera boundaries.

Touch controls must work naturally.

Avoid camera movement when the player is interacting with UI.

**Deliverable:** A working Android build where the player can enter the
world and move the camera.

# 7. MILESTONE 2 --- TRACK BUILDING ENGINE

This is the most important technical milestone.

Implement a robust railway construction engine.

Do not start with decorative track placement alone. The railway must be
a functional interconnected network.

## Track architecture

Implement:

-   TrackPieceDefinition
-   TrackPiece
-   TrackConnection
-   TrackGraph
-   TrackNetworkManager
-   TrackPlacementController
-   TrackValidationService

Each track piece must contain:

-   Unique identifier.
-   Track type.
-   Position.
-   Rotation.
-   Connection points.
-   Connection directions.
-   Neighbour references.
-   Traversal information.

Use connection points to build a railway graph.

Support:

-   Straight sections.
-   Left curves.
-   Right curves.
-   Tight curves.
-   Gentle curves.
-   S-curves.
-   T-junctions.
-   Crossings.
-   Endpoints.

## Track snapping

Implement intelligent snapping.

When a player places a track piece near an existing connection:

-   Detect nearby compatible connection points.
-   Calculate the correct rotation.
-   Align the connection points.
-   Preview the result.
-   Indicate whether placement is valid.
-   Snap automatically when confirmed.

The snapping system must be forgiving.

Use a configurable snapping distance.

Avoid floating-point alignment errors.

## Track preview

Show a ghost version of the selected track piece.

Valid placement should have positive visual feedback.

Invalid placement should have negative visual feedback.

The preview must not interfere with existing track geometry.

## Editing

Implement:

-   Place.
-   Rotate.
-   Move.
-   Delete.
-   Undo.
-   Redo if feasible.

Track deletion must correctly update the graph and invalidate affected
train routes.

## Track validation

Detect:

-   Disconnected endpoints.
-   Invalid connections.
-   Overlapping pieces.
-   Duplicate connections.
-   Invalid junction configuration.

Do not prevent the toddler from experimenting with incomplete track
layouts.

Allow incomplete railways, but prevent trains from traversing invalid
connections.

## Testing

Create automated tests for:

-   Straight-to-straight connection.
-   Straight-to-curve connection.
-   Curve-to-curve connection.
-   Closed loop construction.
-   Junction connections.
-   Track deletion.
-   Graph reconstruction.
-   Duplicate connection prevention.
-   Disconnected endpoints.

**Deliverable:** A fully functioning track construction system. The
child must be able to construct a closed railway loop.

# 8. MILESTONE 3 --- TRAIN MOVEMENT ENGINE

Implement the complete train system.

## Train architecture

Create:

-   TrainDefinition
-   TrainController
-   TrainManager
-   TrainPathFollower
-   TrainCarriageController
-   TrainRoutePlanner
-   TrainMovementAudio

## Initial locomotives

Create four original locomotives:

1.  Classic Red Express.
2.  Blue Adventure.
3.  Green Explorer.
4.  Yellow Sunshine.

Use original, friendly cartoon designs. Do not reproduce copyrighted
commercial train characters.

Each locomotive should have a friendly face, large eyes, rounded
proportions, colourful body, visible wheels, and moving wheel
animations.

## Train placement

Allow the player to select a locomotive and place it on a valid railway
section.

Show a placement preview.

Ensure the locomotive is correctly aligned with the track.

## Train movement

The train must follow the actual railway network.

Do not use simple straight-line movement between predefined points.

Implement continuous movement along track geometry.

Requirements:

-   Smooth straight movement.
-   Correct curvature.
-   Correct orientation.
-   Smooth transitions between pieces.
-   Consistent speed.
-   No visual sliding.
-   No sudden rotation.
-   Proper junction handling.
-   Safe stopping at disconnected endpoints.

For the initial implementation, a deterministic route-selection strategy
is acceptable:

-   Follow the only available valid connection.
-   At a junction, choose a deterministic default.
-   Avoid immediately reversing onto the previous segment.
-   Continue around a closed loop.
-   Never become trapped in an endless junction-selection loop.

Later, support player-controlled junction switching.

## Carriages

Implement attachable carriages:

-   Passenger carriage.
-   Cargo carriage.
-   Additional locomotive combinations where practical.

Carriages must follow the locomotive naturally, including through
curves.

## Controls

Implement large touch controls:

-   GO
-   STOP
-   WHISTLE
-   BELL
-   SPEED

GO starts movement.

STOP stops the train smoothly.

WHISTLE plays a friendly whistle.

BELL plays a bell.

SPEED adjusts movement between safe toddler-friendly speed levels.

**Deliverable:** A locomotive must successfully complete a complete
closed railway loop. Test multiple track configurations.

# 9. MILESTONE 4 --- TRACK AND WORLD EXPANSION

Add:

-   Wooden bridges.
-   Stone bridges.
-   Tunnels.
-   Elevated tracks.
-   Ramps.
-   Train stations.
-   Train depot.
-   Railway crossings.

Ensure the train can physically and visually traverse these structures.

Tunnels should have appropriate entrances and exits. The train must not
disappear permanently or become stuck inside tunnels.

Implement simple environmental interactions.

Add:

-   Cows.
-   Sheep.
-   Chickens.
-   Horses.
-   Dogs.
-   Cats.

Interactions should use simple touch detection and audio feedback.

Add:

-   Animated trees.
-   Moving clouds.
-   Water animation.
-   Windmills.
-   Birds.

Keep simultaneously active animations limited on Low graphics settings.

# 10. MILESTONE 5 --- DECORATION AND CREATIVE SANDBOX

Implement a decoration placement system.

Objects should be selectable from a simple bottom toolbar.

Include:

-   Trees.
-   Flowers.
-   Bushes.
-   Rocks.
-   Houses.
-   Barns.
-   Fences.
-   Animals.
-   Stations.
-   Decorative objects.

Support placement, rotation, moving, deletion, and undo.

Use simple collision and placement rules.

Do not make decoration placement unnecessarily restrictive.

The child should be able to create a personalised railway world.

# 11. MILESTONE 6 --- UI AND TODDLER UX

Design every screen for children aged 2--5.

Do not create conventional complex mobile game menus.

## Main menu

Include:

-   Play.
-   Continue.
-   New World.
-   Train selection.
-   Settings.

Use large visual buttons.

## Build mode

Display a large bottom toolbar with:

-   Straight.
-   Curves.
-   Junctions.
-   Bridges.
-   Tunnels.
-   Stations.
-   Decorations.
-   Undo.
-   Delete.

## Train mode

Display:

-   GO.
-   STOP.
-   WHISTLE.
-   BELL.
-   SPEED.
-   CAMERA.

All buttons must be large enough for toddler fingers, with generous
spacing.

Implement touch feedback.

Avoid tiny buttons, dropdown menus, and text-heavy interfaces.

Use icons and visual demonstrations wherever possible.

The game must work without requiring the child to read.

# 12. MILESTONE 7 --- AUDIO AND ANIMATIONS

Create and integrate:

-   Train whistle.
-   Train bell.
-   Train movement sound.
-   Steam effects.
-   Wheel animations.
-   Track placement sound.
-   Track snapping sound.
-   Button sounds.
-   Animal sounds.
-   Environmental ambience.
-   Background music.

Ensure sounds do not overlap excessively.

Implement audio volume settings.

Use subtle, cheerful animations for UI interactions.

Avoid aggressive screen shaking or flashing.

# 13. MILESTONE 8 --- SAVE SYSTEM

Implement a robust local save system.

Save:

-   Track layout.
-   Track connections or reconstructable track data.
-   Train selection.
-   Carriage configuration.
-   Train position where appropriate.
-   Decoration placements.
-   World configuration.

Implement:

-   Automatic saving.
-   Continue.
-   New World.
-   Save versioning.
-   Corruption handling.
-   Default world recovery.

Use JSON serialization.

Do not rely exclusively on Unity scene serialization.

Save changes at sensible intervals rather than every frame.

Test persistence across application restarts.

# 14. MILESTONE 9 --- VISUAL POLISH

The final game must look professionally designed.

Prioritise:

-   Attractive train models.
-   Consistent art direction.
-   Rounded geometry.
-   Appealing colours.
-   Clear track visibility.
-   Smooth camera movement.
-   Attractive terrain.
-   Polished UI.
-   Friendly animations.

Use lightweight assets and shaders.

Do not use generic grey cubes as final gameplay assets.

If custom models are unavailable, create attractive procedural models
using Unity meshes or simple assembled geometry.

Use consistent materials and proportions.

All models must have appropriate colliders where interaction is
required.

# 15. MILESTONE 10 --- PERFORMANCE OPTIMISATION

Profile the game on target hardware whenever physical device access is
available.

Implement:

-   Graphics quality presets.
-   Texture quality adjustment.
-   Shadow controls.
-   Render distance settings.
-   Object pooling.
-   Efficient mesh management.
-   Limited particle effects.
-   Efficient update loops.
-   Reduced garbage collection.
-   Efficient save operations.

Default to Low on Redmi A3.

Performance acceptance:

-   Target 30 FPS.
-   No sustained severe frame drops.
-   Responsive touch controls.
-   No progressive memory growth during normal play.
-   No major gameplay stalls when placing tracks.

If the physical device is unavailable, report this clearly and
distinguish automated verification from actual hardware testing.

# 16. MILESTONE 11 --- QA AND FINAL ANDROID RELEASE

Perform complete regression testing.

## Gameplay tests

-   Launch game.
-   Enter world.
-   Move camera.
-   Build straight track.
-   Build curves.
-   Connect track pieces.
-   Build a loop.
-   Build a junction.
-   Place train.
-   Start train.
-   Stop train.
-   Use whistle.
-   Use bell.
-   Change speed.
-   Delete track.
-   Rebuild track.
-   Place decorations.
-   Interact with animals.
-   Save world.
-   Restart application.
-   Load saved world.

## Technical tests

-   No critical console errors.
-   No missing references.
-   No broken prefabs.
-   No missing materials.
-   No Android crashes.
-   No corrupted save files.
-   No broken track graph.
-   No train movement through disconnected tracks.

## Android builds

Generate:

1.  ARMv7 32-bit APK.
2.  ARM64 APK.
3.  Combined APK supporting both architectures, where supported.

Provide a clearly labelled release directory.

Include:

-   APK files.
-   Build configuration notes.
-   Build report.
-   Known limitations.
-   Test report.

Verify APK architecture rather than assuming it from Unity build
settings.

# 17. DEVELOPMENT QUALITY RULES

These rules are mandatory.

1.  Never implement a fake feature simply to satisfy a checklist.
2.  Never report a successful build without actually building it.
3.  Never report successful hardware testing without testing on
    hardware.
4.  Do not overwrite existing working implementations without inspecting
    them.
5.  Keep the project modular.
6.  Avoid unnecessary dependencies.
7.  Do not introduce online dependencies.
8.  Do not use copyrighted train characters.
9.  Keep the toddler-first experience central to every design decision.
10. Prioritise functionality before decorative complexity.
11. Write tests for important systems.
12. Fix compilation errors before proceeding to subsequent milestones.
13. Maintain documentation.
14. Ensure ARMv7 remains a release requirement throughout development.

When encountering a technical limitation, explain it, propose
alternatives, and choose the best compatible approach.

# 18. REQUIRED FINAL DELIVERABLE

The final output must be a complete Unity 6 Android project.

It must include:

-   Complete Unity project.
-   All gameplay scripts.
-   Track building engine.
-   Railway graph system.
-   Train movement engine.
-   Train models and assets.
-   Environment assets.
-   UI.
-   Audio.
-   Save system.
-   Performance settings.
-   Automated tests.
-   Documentation.

Final Android deliverables:

-   ARMv7 APK.
-   ARM64 APK.
-   Combined APK where supported.

Final report must include:

1.  Completed milestones.
2.  Implemented gameplay systems.
3.  Automated test results.
4.  Build results.
5.  Android architecture verification.
6.  Redmi A3 hardware testing results, if performed.
7.  Performance observations.
8.  Known issues.
9.  Remaining improvements.

# 19. EXECUTION INSTRUCTIONS

Start with MILESTONE 0.

Do not immediately generate the entire game.

First audit the environment and confirm that the Unity installation can
support the mandatory Android 32-bit requirement.

Then create the project foundation.

Work through the milestones systematically.

You have authority to make reasonable technical and design decisions
without asking for approval for every small detail.

However, do not make major changes to the core game concept, platform,
or device compatibility requirements.

The most important gameplay requirement is that a toddler can
independently build a railway, place a train, and watch it travel around
a railway they created.

Build a real game, not a prototype disguised as a finished product.

**Begin with the environment audit and Milestone 0.**
