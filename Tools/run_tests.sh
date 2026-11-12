#!/usr/bin/env bash
# Runs EditMode and/or PlayMode tests in batch. Usage: Tools/run_tests.sh [EditMode|PlayMode|all]
set -u
cd "$(dirname "$0")/.."
U="${UNITY_EDITOR:-$HOME/Unity/Hub/Editor/6000.3.27f2/Editor/Unity}"
MODES="${1:-all}"; [ "$MODES" = all ] && MODES="EditMode PlayMode"
rc=0
for P in $MODES; do
  rm -f "Logs/${P,,}-results.xml"
  xvfb-run -a -s "-screen 0 1280x720x24" "$U" -batchmode -force-glcore -projectPath "$PWD" -runTests -testPlatform $P \
    -testResults "$PWD/Logs/${P,,}-results.xml" -logFile "Logs/${P,,}.log"
  code=$?; [ $code -ne 0 ] && rc=$code
  echo "$P exit=$code $(grep -o 'total="[0-9]*" passed="[0-9]*" failed="[0-9]*"' Logs/${P,,}-results.xml 2>/dev/null | head -1)"
  grep -B1 -A8 'result="Failed"' Logs/${P,,}-results.xml 2>/dev/null | grep -E "<test-case|message|CDATA" | head -40
  grep -E "error CS" Logs/${P,,}.log | sort -u | head -20
done
exit $rc
