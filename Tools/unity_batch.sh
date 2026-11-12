#!/usr/bin/env bash
# Runs a Unity Editor static method in batch mode inside a virtual X server.
# Usage: Tools/unity_batch.sh <Namespace.Class.Method|-> [log-name] [extra Unity args...]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
METHOD="$1"; LOG="${2:-batch}"; shift $(( $# >= 2 ? 2 : 1 ))
UNITY="${UNITY_EDITOR:-$HOME/Unity/Hub/Editor/6000.3.27f2/Editor/Unity}"
mkdir -p "$ROOT/Logs"
EXEC=(); [ "$METHOD" != "-" ] && EXEC=(-executeMethod "$METHOD")
xvfb-run -a -s "-screen 0 1920x1080x24" "$UNITY" -batchmode -quit -force-glcore \
  -projectPath "$ROOT" "${EXEC[@]}" -logFile "$ROOT/Logs/$LOG.log" "$@"
