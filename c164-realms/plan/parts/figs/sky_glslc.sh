#!/usr/bin/env bash
# Find a GLSL compiler for plan/parts/figs/sky_shaders.py and print its path (nothing when there
# is none). The game compiles its shaders with shaderc; glslc is shaderc's command, glslang its
# front end. Looked for in this order: C164_GLSLC, glslc on PATH, one fetched earlier into
# /tmp/c164_glslc, shaderc's own build for Linux, glslang's own build for Linux. Nothing is
# installed: a fetched compiler lies in /tmp/c164_glslc and is run from there.
#
#   python plan/parts/figs/sky_shaders.py --glslc "$(bash plan/parts/figs/sky_glslc.sh)"
set -uo pipefail
DIR=/tmp/c164_glslc

works() { [ -n "${1:-}" ] && [ -x "$1" ] && "$1" --version >/dev/null 2>&1; }

for c in "${C164_GLSLC:-}" "$(command -v glslc 2>/dev/null)" "$DIR/install/bin/glslc" "$DIR/glslang/bin/glslang"; do
  if works "$c"; then echo "$c"; exit 0; fi
done

mkdir -p "$DIR" && cd "$DIR" || exit 0
# shaderc: the page behind the build badge names the newest build
url=$(curl -sSL -m 30 "https://storage.googleapis.com/shaderc/badges/build_link_linux_clang_release.html" 2>/dev/null \
      | grep -o 'https://[^"<> ]*install\.tgz' | head -n 1)
if [ -n "$url" ] && curl -sSL -m 180 -o install.tgz "$url" 2>/dev/null && tar xzf install.tgz 2>/dev/null; then
  if works "$DIR/install/bin/glslc"; then echo "$DIR/install/bin/glslc"; exit 0; fi
fi
# glslang
if curl -sSL -m 180 -o glslang.zip "https://github.com/KhronosGroup/glslang/releases/download/main-tot/glslang-main-linux-Release.zip" 2>/dev/null; then
  mkdir -p glslang && (cd glslang && python3 -c "import zipfile; zipfile.ZipFile('../glslang.zip').extractall('.')" 2>/dev/null) && chmod +x glslang/bin/* 2>/dev/null
  if works "$DIR/glslang/bin/glslang"; then echo "$DIR/glslang/bin/glslang"; exit 0; fi
fi
exit 0
