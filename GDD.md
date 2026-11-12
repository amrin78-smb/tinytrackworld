# TINY TRACKS WORLD

## Game Design Document and Claude Code Master Development Prompt

**Document version:** 1.0\
**Engine:** Unity 6\
**Platform:** Android\
**Target audience:** Toddlers aged 2--5\
**Primary test device:** Xiaomi Redmi A3\
**Critical compatibility:** Android ARMv7 (32-bit) and ARM64\
**Orientation:** Landscape\
**Connectivity:** Offline-first

------------------------------------------------------------------------

# PART 1 --- GAME DESIGN DOCUMENT (GDD)

# 1. Game Vision

Tiny Tracks World is a toddler-friendly 3D railway sandbox where
children create their own railway networks, select trains, build bridges
and tunnels, decorate their environment, and operate trains through a
miniature world.

**Tagline:** Build it. Connect it. Ride it. Explore it.

The core gameplay loop is:

1.  Build a railway.
2.  Connect railway pieces.
3.  Choose a train.
4.  Place the train on the track.
5.  Start the train.
6.  Watch it travel around the railway.
7.  Explore, decorate, and expand the world.

There are no losing conditions, time limits, lives, complicated
missions, or punishment mechanics.

The game encourages creativity, experimentation, spatial awareness,
cause and effect, basic problem-solving, and independent play.

The experience should feel like playing with a physical wooden railway
set, with the freedom of a digital 3D sandbox.

# 2. Core Design Principles

## 2.1 Toddler-first interaction

-   Large touch targets.
-   Simple visual icons.
-   Minimal text.
-   No keyboard requirements.
-   No complex menus.
-   No multi-step configuration.
-   One-tap actions wherever possible.
-   Forgiving placement and snapping.
-   Immediate visual and audio feedback.

## 2.2 Creative freedom

Children should be able to build whatever railway they imagine. Track
pieces snap together intelligently, supporting straight sections,
curves, intersections, and loops.

## 2.3 Immediate gratification

Examples:

-   Tap a train: it whistles.
-   Tap a cow: it makes a sound.
-   Place a track: it snaps into position.
-   Tap the locomotive: it starts moving.
-   Drive through a tunnel: the train emerges from the other side.

## 2.4 No punishment

If tracks are disconnected, explain the issue visually and gently. If a
train reaches a disconnected endpoint, stop it safely and provide a
friendly visual suggestion.

# 3. Visual Direction

## 3.1 Art style

Use high-quality stylised 3D cartoon graphics:

-   Wooden railway toy inspiration.
-   Colourful children's educational-game aesthetic.
-   Soft, rounded geometry.
-   Friendly toy-like proportions.
-   Bright but comfortable colours.

Avoid realistic industrial trains, dark environments, and overly complex
scenery.

## 3.2 Initial environment

Create a colourful miniature countryside containing:

-   Green rolling hills.
-   Blue sky and animated clouds.
-   Trees and bushes.
-   Small lakes and rivers.
-   Farmhouses and barns.
-   Animal farms.
-   Flowers and rocks.
-   Small villages.
-   Bridges and tunnels.

The world should feel like a living miniature toy landscape.

## 3.3 Camera

Use a smooth 3D perspective camera with an elevated, slightly
downward-facing view.

Requirements:

-   Focus on the current construction area.
-   Smooth pan and zoom.
-   Optional gentle rotation.
-   Automatic train-follow camera during operation.
-   User-adjustable camera during train operation.
-   Camera reset button.
-   Configurable camera boundaries.
-   No sudden or excessively fast camera movement.

# 4. Main Game Modes

## 4.1 Build Mode

The primary creative mode. Children construct railways by selecting and
placing individual track pieces.

Features:

-   Place track pieces throughout the buildable world.
-   Rotate pieces before placement.
-   Automatic track snapping.
-   Move existing pieces.
-   Remove individual pieces.
-   Undo the last placement.
-   Redo if feasible.
-   Clear the railway with confirmation.
-   Extend existing railways.
-   Build loops and multiple connected routes.

Track placement should not require precise alignment.

## 4.2 Train Mode

Allows children to operate their railway.

Features:

-   Place a locomotive on a valid track.
-   Start and stop the train.
-   Automatic train movement by default.
-   Optional manual speed adjustment.
-   Whistle and bell buttons.
-   Camera-follow mode.
-   Smooth navigation through the railway.

The train must follow connected track geometry rather than moving
independently in a straight line.

## 4.3 Explore Mode

A relaxed mode for exploring the world and interacting with objects.

Examples:

-   Tap animals to hear their sounds.
-   Tap trees to make leaves move.
-   Tap houses to trigger friendly animations.
-   Interact with bridges and tunnels.
-   Discover environmental interactions.

No compulsory objectives or missions.

## 4.4 Decorate Mode

Allow children to customise the world with:

-   Trees.
-   Flowers.
-   Buildings.
-   Houses.
-   Stations.
-   Farm animals.
-   People.
-   Road signs.
-   Fences.
-   Lakes.
-   Rocks.
-   Decorative objects.

Use large selection icons and simple placement controls.

# 5. Track Construction System

This is the most important gameplay system.

Tracks must be functional interconnected railway pieces, not isolated
decorative meshes.

## 5.1 Initial track library

  Track piece          Description
  -------------------- -----------------------------
  Straight             Standard straight section
  Gentle left curve    45-degree left turn
  Gentle right curve   45-degree right turn
  Tight left curve     90-degree left turn
  Tight right curve    90-degree right turn
  Short straight       Small connecting section
  S-curve              Alternating curved section
  T-junction           Three-way connection
  Cross junction       Four-way intersection
  End piece            Decorative railway endpoint

## 5.2 Advanced track pieces

-   Wooden bridge.
-   Stone bridge.
-   Tunnel entrance.
-   Tunnel exit.
-   Elevated track.
-   Track ramp.
-   Station platform.
-   Train depot.
-   Railway crossing.

These should be available in sandbox mode or introduced without
demanding difficult progression.

## 5.3 Track placement flow

1.  Tap a track category.
2.  Select a piece.
3.  Display a ghost preview.
4.  Drag or tap to position.
5.  Rotate using a large rotate button.
6.  Snap to nearby compatible connection points.
7.  Confirm placement or release to place.

Requirements:

-   Automatic alignment.
-   Automatic rotation when snapping.
-   Visual indication of valid connections.
-   Prevent overlapping geometry where inappropriate.
-   Prevent impossible connections.
-   Support connecting new tracks to existing tracks.
-   Allow unsnapped placement where appropriate.
-   Provide undo and delete.

## 5.4 Track connection architecture

Use a graph-based railway network.

Each track piece must contain:

-   Unique piece ID.
-   Piece type.
-   World position.
-   Rotation.
-   Entry connection point.
-   Exit connection point.
-   Additional connection points for junctions.
-   Connection references to neighbouring pieces.
-   Traversal information.

Track pieces are graph nodes; connections are traversable edges.

The architecture must support:

-   Closed loops.
-   Branching paths.
-   Multiple railway networks.
-   Junctions.
-   Train navigation.
-   Track removal and reconnection.

A train must never travel over a disconnected section.

# 6. Train System

## 6.1 Initial locomotives

Include at least four visually distinct original locomotives:

1.  **Classic Red Express** --- friendly red steam locomotive.
2.  **Blue Adventure** --- cheerful blue locomotive.
3.  **Green Explorer** --- green countryside locomotive.
4.  **Yellow Sunshine** --- bright yellow locomotive.

Use original designs. Do not copy copyrighted characters or commercial
train designs.

Each locomotive should have:

-   Friendly face.
-   Large expressive eyes.
-   Rounded proportions.
-   Colourful body.
-   Visible wheels.
-   Moving wheel animations.

## 6.2 Train components

Each train can consist of:

-   Locomotive.
-   Optional passenger carriage.
-   Optional cargo carriage.

Allow simple carriage combinations.

## 6.3 Train movement

The train must follow actual railway geometry using a spline-based or
equivalent continuous path representation.

Requirements:

-   Smooth movement along straight sections.
-   Smooth rotation through curves.
-   Correct orientation based on track tangent.
-   No visible sliding.
-   No sudden snapping.
-   Smooth transitions between connected pieces.
-   Correct handling of junctions.
-   Safe stopping at disconnected endpoints.

Use a robust path-following system based on the railway graph, with
continuous interpolation between track segments.

## 6.4 Train controls

Provide large touch controls:

-   Green GO button.
-   Red STOP button.
-   WHISTLE button.
-   BELL button.
-   Simple speed control.

Default behaviour:

-   Start at a gentle speed.
-   Allow speed adjustment.
-   Continue around closed loops.
-   Stop at disconnected endpoints.
-   Allow the child to stop at any time.

Automatic operation is the default; manual controls are secondary.

# 7. World Interaction

## 7.1 Animals

Include:

-   Cow --- moo.
-   Sheep --- baa.
-   Chicken --- cluck.
-   Dog --- bark.
-   Cat --- meow.
-   Horse --- neigh.

## 7.2 Environment

-   Windmills rotate.
-   Trees sway.
-   Clouds move slowly.
-   Water animates.
-   Flowers react when touched.
-   Birds fly across the sky.

## 7.3 Buildings

-   Train station: friendly station announcement.
-   Farm: animal interactions.
-   House: friendly lighting or animation.
-   Depot: train selection interaction.

Interactions should be short and rewarding.

# 8. User Interface

Design the interface for children who may not yet read.

## 8.1 Main screen

Display:

-   Play / Continue.
-   Build.
-   Train selection.
-   World selection.
-   Settings.

Avoid complicated menus.

## 8.2 Build mode

Bottom toolbar categories:

-   Straight tracks.
-   Curves.
-   Junctions.
-   Bridges and tunnels.
-   Stations.
-   Decorate.
-   Undo.
-   Delete.

## 8.3 Train mode

Large controls:

-   GO.
-   STOP.
-   WHISTLE.
-   BELL.
-   SPEED.
-   CAMERA.

## 8.4 UI design requirements

-   Large rounded buttons.
-   High contrast.
-   Simple icons.
-   Minimal text.
-   Friendly animations.
-   Clear selected-state indicators.
-   No small controls.
-   Avoid obstructing the railway.
-   Landscape orientation only.

# 9. Audio Design

Include:

-   Locomotive whistle.
-   Steam locomotive sounds.
-   Electric train motor sounds.
-   Railway rolling sounds.
-   Train bell.
-   Track placement sounds.
-   Track snapping sounds.
-   Button interaction sounds.
-   Animal sounds.
-   Ambient countryside sounds.
-   Cheerful, relaxing background music that loops seamlessly.

Provide separate volume controls for music, sound effects, and ambient
audio.

Avoid excessively loud or startling sounds.

# 10. Progression and Rewards

This is primarily a sandbox game.

Do not implement aggressive progression mechanics.

Optional rewards:

-   Discover new animals.
-   Unlock additional locomotives.
-   Find new scenery items.
-   Discover special railway pieces.

Never require advertisements, purchases, or difficult tasks to access
core features.

All core features should work offline.

# 11. World Design

## Initial world: Sunny Valley

A miniature countryside containing:

-   Farm area.
-   Village area.
-   Lake area.
-   Forest area.
-   Hill area.
-   Railway station.
-   Open construction areas.

The initial world should be large enough for creative railway layouts
but not so large that it becomes difficult for a toddler to navigate.

Use a defined buildable area with expansion capability.

## Future environments

Design the architecture to support:

-   Snowy Valley.
-   Desert Adventure.
-   Tropical Island.
-   City Railway.
-   Mountain Railway.

These are future expansions, not first-release requirements.

# 12. Save and Load System

Automatically save:

-   Railway layout.
-   Track positions and rotations.
-   Track connections or reconstructable connection data.
-   Train selection.
-   Train carriages.
-   Decorative objects.
-   World configuration.

Implement:

-   Autosave after meaningful construction changes.
-   Manual save option.
-   Continue button.
-   New World option.
-   Versioned JSON save format.
-   Graceful handling of missing or corrupted saves.

Save locally on Android.

# 13. Technical Architecture

Use Unity 6 with a modular architecture.

Suggested systems:

-   GameManager
-   WorldManager
-   CameraController
-   InputManager
-   UIManager
-   BuildModeController
-   TrackPlacementController
-   TrackNetworkManager
-   TrackPiece
-   TrackConnection
-   TrackGraph
-   TrainManager
-   TrainController
-   TrainPathFollower
-   TrainCarriageController
-   InteractionManager
-   DecorationManager
-   AudioManager
-   SaveManager
-   PerformanceManager

Use ScriptableObjects for:

-   Track definitions.
-   Train definitions.
-   Decoration definitions.
-   Audio configuration.
-   World configuration.

Use object pooling where appropriate. Avoid unnecessary runtime
allocations and expensive physics calculations.

# 14. Performance and Device Compatibility

Mandatory target device: Xiaomi Redmi A3, including its 32-bit Android
environment.

Do not assume that a successful 64-bit build proves compatibility.

## Build requirements

-   Unity 6.
-   Android ARMv7 (32-bit) support.
-   Android ARM64 support.
-   IL2CPP backend.
-   Compatible Android API configuration.
-   OpenGL ES 3.0 as the primary graphics baseline.
-   Vulkan must not be required.
-   Landscape orientation.
-   Offline operation.
-   No mandatory network access.

Verify that the selected Unity version and Android toolchain support
ARMv7 before committing to implementation.

If ARMv7 is unsupported by the installed Unity version or a required
package, identify the limitation and propose a compatible solution
before proceeding.

## Performance targets

-   Target 30 FPS on Redmi A3.
-   Stable gameplay without excessive frame drops.
-   Low memory consumption.
-   Fast initial loading.
-   Efficient rendering.
-   Minimal draw calls.
-   Lightweight shaders.
-   Compressed textures.
-   Object pooling.
-   Baked lighting where practical.
-   No unnecessary real-time shadows.

Provide Low, Medium, and High graphics presets. Redmi A3 defaults to
Low.

Low preset should reduce shadows, vegetation density, texture
resolution, environmental effects, and post-processing without
compromising gameplay or track visibility.

# 15. Development Phases

1.  **Foundation:** Unity project setup, Android configuration, camera,
    world, basic UI, touch input.
2.  **Track Builder:** Track prefabs, placement, rotation, snapping,
    connections, undo, delete, validation.
3.  **Train System:** Locomotives, placement, graph traversal, movement,
    curves, junctions, controls.
4.  **World Interaction:** Animals, buildings, environmental animations,
    audio.
5.  **Customisation:** Locomotives, carriages, decorations, stations,
    bridges, tunnels.
6.  **Saving and Polish:** Autosave, loading, UI polish, audio polish,
    optimisation.
7.  **Android Release:** ARMv7 and ARM64 builds, Redmi A3 testing,
    memory and FPS profiling, touch testing, save/load testing, final
    APK.

# 16. Acceptance Criteria

The game is complete when:

1.  It launches successfully on Redmi A3.
2.  It works without internet connectivity.
3.  A toddler can build a basic railway without assistance.
4.  Track pieces snap correctly.
5.  The child can construct a closed loop.
6.  A locomotive can be placed on the railway.
7.  The locomotive follows the complete railway loop.
8.  The locomotive navigates curves smoothly.
9.  The train can stop and restart.
10. Whistle and bell controls work.
11. Bridges and tunnels are traversable.
12. Disconnected tracks do not cause train crashes.
13. The child can decorate the world.
14. Railway layouts save and load correctly.
15. The game remains responsive during construction.
16. The 32-bit ARMv7 build launches and runs correctly.
17. Performance is acceptable on the target device.

# 17. Future Features

Potential future additions:

-   Multiple trains operating simultaneously.
-   Railway signalling.
-   Automatic junction switching.
-   Passenger pickup and drop-off.
-   Cargo transportation.
-   More environments.
-   Custom train colours.
-   Railway stations with animated passengers.
-   More track types.
-   Free camera exploration.
-   Additional sandbox toys.

These must not delay the first playable release.

# 18. Final Design Statement

Tiny Tracks World should feel like an unlimited digital wooden railway
toy.

The child is the creator, railway designer, and train driver.

The most important measure of success is whether a toddler can
independently open the game, build something, start a train, and enjoy
watching it travel through a world they created.

Prioritise simplicity, creativity, reliability, visual charm, and
performance over feature count.

------------------------------------------------------------------------
