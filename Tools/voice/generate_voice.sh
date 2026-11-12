#!/usr/bin/env bash
# Generates the narrator clips offline (English: Kokoro TTS, Apache-2.0; Thai: VachanaTTS, MIT).
# Output: Assets/_Project/Audio/Voice/<lang>/<key>.wav. Then run Tools/setup.sh.
# Shares the model cache with littleburgerworld (~/.cache/lbw-tts); first run installs it (~450 MB).
set -euo pipefail
cd "$(dirname "$0")/../.."
T="${LBW_TTS_HOME:-$HOME/.cache/lbw-tts}"
if [ ! -x "$T/venv/bin/python" ]; then
  python3 -m venv "$T/venv"
  "$T/venv/bin/pip" install -q kokoro-onnx==0.6.1 vachanatts==0.0.7 requests soundfile
fi
mkdir -p "$T/models"
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -s "$T/models/$f" ] || curl -sSL -o "$T/models/$f" "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f"
done
"$T/venv/bin/python" -I Tools/voice/generate_voice.py Tools/voice/voice_lines.json "${OUT:-Assets/_Project/Audio/Voice}" "$T/models" "$@"
