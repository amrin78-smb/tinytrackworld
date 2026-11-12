#!/usr/bin/env bash
# Renders the game to Logs/Showcase/*.png (visual QA).
cd "$(dirname "$0")/.."
U="${UNITY_EDITOR:-$HOME/Unity/Hub/Editor/6000.3.27f2/Editor/Unity}"
rm -rf Logs/Showcase
xvfb-run -a -s "-screen 0 1600x900x24" "$U" -batchmode -force-glcore -projectPath "$PWD" -runTests -testPlatform PlayMode \
  -testFilter "TinyTracks.Tests.ShowcaseCapture" -testResults "$PWD/Logs/showcase-results.xml" -logFile Logs/showcase.log
grep -E "\[TT Showcase\]|Exception|error" Logs/showcase.log | grep -v Licensing | head -30
ls Logs/Showcase
