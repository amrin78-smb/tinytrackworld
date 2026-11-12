#!/usr/bin/env bash
# Verifies an APK's real contents (not Unity's settings): native libraries per ABI, GLES requirement, landscape,
# no INTERNET in release builds. Usage: Tools/verify_apk.sh <apk> [expect: both|armv7|arm64]
set -u
APK="$1"
[ -f "$APK" ] || { echo "FAIL no APK at $APK"; exit 1; }
EXPECT="${2:-}"
if [ -z "$EXPECT" ]; then case "$APK" in *armv7*) EXPECT=armv7;; *arm64*) EXPECT=arm64;; *) EXPECT=both;; esac; fi
SDK="$HOME/Unity/Hub/Editor/6000.3.27f2/Editor/Data/PlaybackEngines/AndroidPlayer/SDK"
AAPT=$(ls -d "$SDK"/build-tools/*/aapt 2>/dev/null | sort -V | tail -1)
fail=0
echo "== $APK ($(du -h "$APK" | cut -f1))"
LIBS=$(unzip -l "$APK" | awk '{print $4}' | grep '^lib/' )
for abi in armeabi-v7a arm64-v8a; do
  n=$(echo "$LIBS" | grep -c "^lib/$abi/")
  il2=$(echo "$LIBS" | grep -c "^lib/$abi/libil2cpp.so")
  echo "     lib/$abi: $n files, libil2cpp.so=$il2"
done
has7=$(echo "$LIBS" | grep -c "^lib/armeabi-v7a/libil2cpp.so"); has64=$(echo "$LIBS" | grep -c "^lib/arm64-v8a/libil2cpp.so")
case "$EXPECT" in
  both) [ "$has7" = 1 ] && [ "$has64" = 1 ] && echo "OK   ARMv7 (32-bit) + ARM64 IL2CPP libraries present" || { echo "FAIL expected both ABIs"; fail=1; };;
  armv7) [ "$has7" = 1 ] && [ "$has64" = 0 ] && echo "OK   ARMv7-only (32-bit) IL2CPP library" || { echo "FAIL expected ARMv7 only"; fail=1; };;
  arm64) [ "$has64" = 1 ] && [ "$has7" = 0 ] && echo "OK   ARM64-only IL2CPP library" || { echo "FAIL expected ARM64 only"; fail=1; };;
esac
if command -v file >/dev/null && [ "$has7" = 1 ]; then
  T=$(mktemp -d); unzip -q -o "$APK" lib/armeabi-v7a/libil2cpp.so -d "$T"; echo "     $(file -b "$T/lib/armeabi-v7a/libil2cpp.so" | cut -c1-90)"; rm -rf "$T"
fi
BADGING=$("$AAPT" dump badging "$APK" 2>/dev/null)
echo "$BADGING" | grep -E "^package:|sdkVersion|targetSdkVersion|native-code" | sed 's/^/     /'
"$AAPT" dump xmltree "$APK" AndroidManifest.xml | grep -q "glEsVersion.*0x30000" && echo "OK   requires OpenGL ES 3.0" || echo "INFO glEsVersion: $("$AAPT" dump xmltree "$APK" AndroidManifest.xml | grep -m1 glEsVersion)"
"$AAPT" dump xmltree "$APK" AndroidManifest.xml | grep -q 'screenOrientation.*0x6\|screenOrientation.*0xb\|screenOrientation.*0x0' && echo "OK   landscape orientation" || echo "INFO $("$AAPT" dump xmltree "$APK" AndroidManifest.xml | grep -m1 screenOrientation)"
if echo "$BADGING" | grep -q "android.permission.INTERNET"; then
  case "$APK" in *-dev.apk) echo "INFO INTERNET permission (development build: profiler)";; *) echo "FAIL release APK requests INTERNET"; fail=1;; esac
else echo "OK   no INTERNET permission (offline)"; fi
exit $fail
