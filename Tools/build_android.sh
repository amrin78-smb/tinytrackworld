#!/usr/bin/env bash
# Android APKs. Usage: Tools/build_android.sh [dev|release|armv7|arm64|all]
#   dev     -> Builds/Android/TinyTracksWorld-dev.apk (development, ARMv7+ARM64)
#   release -> Builds/Android/TinyTracksWorld-universal.apk
#   all     -> universal + armv7-only + arm64-only release APKs
set -u
cd "$(dirname "$0")/.."
MODE="${1:-dev}"
case "$MODE" in
  dev) METHOD=AndroidDevBatch; APKS="Builds/Android/TinyTracksWorld-dev.apk";;
  release) METHOD=AndroidReleaseBatch; APKS="Builds/Android/TinyTracksWorld-universal.apk";;
  armv7) METHOD=AndroidArmv7Batch; APKS="Builds/Android/TinyTracksWorld-armv7.apk";;
  arm64) METHOD=AndroidArm64Batch; APKS="Builds/Android/TinyTracksWorld-arm64.apk";;
  all) METHOD=AndroidAllBatch; APKS="Builds/Android/TinyTracksWorld-universal.apk Builds/Android/TinyTracksWorld-armv7.apk Builds/Android/TinyTracksWorld-arm64.apk";;
  *) echo "unknown mode $MODE"; exit 2;;
esac
Tools/unity_batch.sh TinyTracks.EditorTools.BuildScript.$METHOD android_build -buildTarget Android
code=$?
echo "ANDROID BUILD exit=$code"
grep "\[TT Build\]" Logs/android_build.log
for a in $APKS; do Tools/verify_apk.sh "$a" || code=1; done
exit $code
