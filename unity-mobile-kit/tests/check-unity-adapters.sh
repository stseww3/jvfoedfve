#!/usr/bin/env bash
# Compile-checks unity/Runtime against the UnityEngine stand-ins (tests/UnityApiStubs) once per
# combination of scripting defines Unity can set for it. This proves the adapters are valid C#
# against those signatures and the real core; it does not run them or prove Unity accepts them.
set -euo pipefail
cd "$(dirname "$0")/UnityAdapters.CompileCheck"

configs=(
  "ENABLE_LEGACY_INPUT_MANAGER"
  "ENABLE_LEGACY_INPUT_MANAGER;UMK_UGUI;UMK_INPUT_SYSTEM;UNITY_2022_2_OR_NEWER"
  "ENABLE_INPUT_SYSTEM;UMK_INPUT_SYSTEM;UMK_UGUI;UNITY_2022_2_OR_NEWER;UNITY_ANDROID"
  "ENABLE_INPUT_SYSTEM;ENABLE_LEGACY_INPUT_MANAGER;UMK_INPUT_SYSTEM;UNITY_ANDROID;UNITY_EDITOR"
  "ENABLE_INPUT_SYSTEM;UMK_INPUT_SYSTEM;UNITY_ANDROID"
)

failed=0
for defines in "${configs[@]}"; do
  if output=$(UNITY_DEFINES="$defines" dotnet build --nologo --no-incremental -v quiet 2>&1); then
    echo "OK    $defines"
  else
    echo "FAIL  $defines"
    echo "$output" | grep -E "error|warning" | sort -u
    failed=1
  fi
done
exit $failed
