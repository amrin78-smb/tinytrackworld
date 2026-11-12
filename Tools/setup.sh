#!/usr/bin/env bash
# Regenerates settings, materials, prefabs, definitions, content library and the scene from the art + code.
set -u
cd "$(dirname "$0")/.."
Tools/unity_batch.sh TinyTracks.EditorTools.TrackShapeExporter.Export export_shapes
Tools/unity_batch.sh TinyTracks.EditorTools.ProjectSetup.RunBatch setup -buildTarget Android
code=$?
grep -E "\[TT (Setup|Validate)\]|error CS|Exception" Logs/setup.log | head -60
exit $code
