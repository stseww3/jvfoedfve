#!/usr/bin/env bash
# Start the official client under Xvfb with Mesa software rendering and join a local server.
# Offline-mode launch for local testing only; the server it joins must listen on 127.0.0.1.
#
#   run_client.sh [player_name] [server_host:port]
#
# Environment: MC_HOME (client files from fetch_client.py), JAVA (Java 25 binary),
#              MC_VERSION, MC_DISPLAY (X display number), MC_SIZE (WxH), LP_NUM_THREADS.
set -euo pipefail

MC_HOME="${MC_HOME:-/agent/realms-study/client26}"
JAVA="${JAVA:-/agent/realms-study/jdk/jdk-25.0.5+8-jre/bin/java}"
MC_VERSION="${MC_VERSION:-26.3}"
MC_DISPLAY="${MC_DISPLAY:-164}"
MC_SIZE="${MC_SIZE:-1280x720}"
NAME="${1:-C164Cam}"
SERVER="${2:-127.0.0.1:25599}"

GAME_DIR="$MC_HOME/game"
NATIVES="$MC_HOME/natives"
mkdir -p "$GAME_DIR" "$NATIVES"

ASSET_INDEX="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['assetIndex']['id'])" "$MC_HOME/versions/$MC_VERSION/$MC_VERSION.json")"
UUID="$(python3 -c "
import hashlib,sys,uuid
d=bytearray(hashlib.md5(('OfflinePlayer:'+sys.argv[1]).encode()).digest())
d[6]=(d[6]&0x0f)|0x30; d[8]=(d[8]&0x3f)|0x80
print(uuid.UUID(bytes=bytes(d)).hex)" "$NAME")"

if [ ! -e "/tmp/.X11-unix/X$MC_DISPLAY" ]; then
  Xvfb ":$MC_DISPLAY" -screen 0 "${MC_SIZE}x24" +extension GLX -nolisten tcp >"$MC_HOME/xvfb.log" 2>&1 &
  sleep 2
fi

export DISPLAY=":$MC_DISPLAY"
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export LP_NUM_THREADS="${LP_NUM_THREADS:-3}"
export SDL_VIDEODRIVER=x11
export ALSOFT_DRIVERS=null

cd "$GAME_DIR"
exec nice -n 10 "$JAVA" -Xms512M -Xmx3G \
  -XX:StackShadowPages=32 --enable-native-access=ALL-UNNAMED \
  --add-exports java.base/jdk.internal.misc=ALL-UNNAMED \
  -Djava.library.path="$NATIVES/java" -Djna.tmpdir="$NATIVES/jna" \
  -Dorg.lwjgl.system.SharedLibraryExtractPath="$NATIVES/lwjgl" \
  -Dio.netty.native.workdir="$NATIVES/netty" \
  -Dminecraft.launcher.brand=c164-test -Dminecraft.launcher.version=1 \
  -cp "$(cat "$MC_HOME/classpath-$MC_VERSION.txt")" \
  net.minecraft.client.main.Main \
  --username "$NAME" --version "$MC_VERSION" --gameDir "$GAME_DIR" \
  --assetsDir "$MC_HOME/assets" --assetIndex "$ASSET_INDEX" \
  --uuid "$UUID" --accessToken 0 --clientId 0 --xuid 0 --versionType release \
  --width "${MC_SIZE%x*}" --height "${MC_SIZE#*x}" \
  --quickPlayMultiplayer "$SERVER"
