#!/usr/bin/env bash
# What a worker node has of the things the game needs. Read-only: nothing is installed or changed.
#
#   bash c164-realms/tools/nodejob.sh --no-push --tail 80 bash tools/nodeprobe.sh
#
# One fact a line, so that the receipt's closing lines carry all of it.
ROOT="${MC_ROOT:-/agent/realms-study}"

echo "machine: $(nproc) cores, $(awk '/MemTotal/ {printf "%.1f GB", $2/1048576}' /proc/meminfo) memory, $(awk '/MemAvailable/ {printf "%.1f GB", $2/1048576}' /proc/meminfo) available, load $(cut -d' ' -f1-3 /proc/loadavg)"
echo "disk: $(df -h --output=avail,target "$ROOT" 2>/dev/null | tail -n 1 | xargs)"
echo "system: $(. /etc/os-release 2>/dev/null; echo "$PRETTY_NAME"), kernel $(uname -r), user $(id -un)"
if sudo -n true 2>/dev/null; then echo "sudo: yes, without a password"; else echo "sudo: no"; fi

for tool in Xvfb xvfb-run import xdotool xwd glxinfo tmux curl unzip tar; do
  path="$(command -v "$tool" 2>/dev/null)"
  echo "tool $tool: ${path:-MISSING}"
done

found=""
for java in "$ROOT"/jdk/*/bin/java /usr/lib/jvm/*/bin/java "$(command -v java 2>/dev/null)"; do
  [ -x "$java" ] || continue
  version="$("$java" -version 2>&1 | head -n 1)"
  echo "java: $java -> $version"
  case "$version" in *'"25'*) found="$java" ;; esac
done
echo "java 25: ${found:-MISSING}"

for lib in libGL.so.1 libGLX_mesa.so.0 libEGL.so.1 libX11.so.6 libXrandr.so.2 libXinerama.so.1 libXcursor.so.1 libXi.so.6 libXxf86vm.so.1 libgallium; do
  hit="$(ldconfig -p 2>/dev/null | grep -m1 "$lib" | awk '{print $NF}')"
  echo "library $lib: ${hit:-MISSING}"
done
echo "mesa dri: $(ls /usr/lib/x86_64-linux-gnu/dri 2>/dev/null | tr '\n' ' ' | cut -c1-200)"
echo "packages: $(dpkg -l 2>/dev/null | awk '$1=="ii" && $2 ~ /^(xvfb|imagemagick|libgl1-mesa-dri|libglx-mesa0|mesa-libgallium|mesa-utils|openjdk-25-jre-headless|openjdk-25-jre|xdotool|x11-apps)(:|$)/ {printf "%s=%s ", $2, $3}')"

# Mesa's software renderer, asked on a display of its own
if command -v Xvfb >/dev/null 2>&1 && command -v glxinfo >/dev/null 2>&1; then
  Xvfb :199 -screen 0 640x360x24 +extension GLX -nolisten tcp >/dev/null 2>&1 &
  xpid=$!
  sleep 2
  DISPLAY=:199 LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe glxinfo -B 2>&1 | grep -E 'renderer string|core profile version|OpenGL version string|direct rendering|rror' | sed 's/^ */glx: /'
  kill "$xpid" 2>/dev/null
else
  echo "glx: not asked (no Xvfb or no glxinfo)"
fi

for url in https://piston-meta.mojang.com/mc/game/version_manifest_v2.json https://resources.download.minecraft.net/ https://libraries.minecraft.net/ https://piston-data.mojang.com/ https://api.adoptium.net/v3/info/available_releases; do
  code="$(curl -s -o /dev/null -m 20 -w '%{http_code} in %{time_total}s' "$url" 2>&1)"
  echo "reach $url: $code"
done

echo "under $ROOT: $(ls "$ROOT" 2>/dev/null | tr '\n' ' ')"
for dir in client26/libraries client26/assets/objects client26/game server26; do
  if [ -d "$ROOT/$dir" ]; then echo "  $dir: $(du -sh "$ROOT/$dir" 2>/dev/null | cut -f1), $(find "$ROOT/$dir" -type f 2>/dev/null | wc -l) files"; else echo "  $dir: not there"; fi
done
echo "ours running: $(pgrep -af 'server.jar nogui|net.minecraft.client.main.Main|Xvfb :164' 2>/dev/null | cut -c1-120 | tr '\n' ';' | cut -c1-400)"
echo "probe done"
