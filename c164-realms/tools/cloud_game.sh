#!/usr/bin/env bash
# Make a fresh cloud machine ready to run the game: the test server and the picture client, software
# rendered on Xvfb, so that real-machine pictures can be taken on a machine with no graphics card.
# Since 11-15 the admin's computer is not used and the render-key holder draws them on its own
# cloud machine. cloud_setup.sh comes first; this builds on it. Running it again is harmless.
#
#   bash c164-realms/tools/cloud_game.sh [--check-only]
#
# Take it from the assembly branch and pipe it in, the same way as cloud_setup.sh:
#
#   cd /agent/repos/jvfoedfve && git fetch -q origin cursor/c164-realms-map-b59c && git show FETCH_HEAD:c164-realms/tools/cloud_game.sh | bash -s --
#
# What it leaves, at the paths tools/mc.sh and tools/run_client.sh already use:
#
#   /usr/lib/jvm/java-25-openjdk-amd64            Java 25 through apt (26.3 asks for 25; the system
#                                                 Python image has 21, which will not start it)
#   /agent/realms-study/jdk/jdk-25.0.5+8-jre      a symlink to it: the scripts were written for a JRE
#                                                 unpacked by hand, and a symlink needs no edit in them
#   Mesa's llvmpipe Vulkan driver                 mesa-vulkan-drivers. Under Xvfb the OpenGL backend
#                                                 always fails on "Couldn't find matching GLX visual",
#                                                 and the client falls back to Vulkan; with no ICD the
#                                                 Vulkan backend fails too and the client exits
#   ImageMagick's import                          tools/shoot.py grabs the X display with it on Linux
#   /agent/realms-study/client26 (the client files) and /agent/realms-study/server26/server.jar:
#                                                 from Mojang only, SHA-1 checked, by tools/fetch_client.py
#   server.properties, eula.txt, .rcon_pw         the test server: void world, offline mode, RCON on
#                                                 127.0.0.1:25598, listening on 127.0.0.1 only
#
# Nothing here goes into the repository: the game files are big and the RCON password is a secret.
#
# --check-only installs nothing and only says what is in place. It ends with 1 when something the
# game needs is missing, so it can be run to see whether a machine is ready.
#
# Getting the pictures after this: plan/roles/S1-cloud-notes.md, sections 5 to 10.
#
# Environment: MC_ROOT (default /agent/realms-study), MC_SERVER_HEAP (default 2G).
set -euo pipefail

VERSION="26.3"
RCON_PORT=25598
SERVER_PORT=25599

say() { printf '[cloud_game %4ds] %s\n' "$SECONDS" "$*"; }
die() { printf '[cloud_game] FAILED: %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
cloud_game.sh [--check-only]
  --check-only   install nothing; say what is in place and end with 1 if something is missing
EOF
}

# One function called on the last line, so the file is read whole before anything runs: piped into
# `bash -s`, a command that reads standard input could otherwise swallow the rest of the script.
main() {
  local check=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --check-only) check=1 ;;
      -h|--help) usage; return 0 ;;
      *) usage >&2; die "unknown option $1" ;;
    esac
    shift
  done

  local root="${MC_ROOT:-/agent/realms-study}"
  local java_dir=/usr/lib/jvm/java-25-openjdk-amd64
  local jre="$root/jdk/jdk-25.0.5+8-jre"
  # not `local missing=()`: bash splits that into a bare `local` and a separate assignment, so an
  # empty array is there but every later `${missing[@]}` sees nothing had been added.
  local missing=""

  have_java25() { [ -x "$java_dir/bin/java" ] && "$java_dir/bin/java" -version 2>&1 | grep -q '"25\.'; }
  have_vulkan() { ls /usr/share/vulkan/icd.d/lvp_icd.json >/dev/null 2>&1; }
  have_import() { command -v import >/dev/null 2>&1; }

  # 0. what is in place
  if [ "$check" = 1 ]; then
    have_java25 && say "java 25: $("$java_dir/bin/java" -version 2>&1 | head -1)" || missing="$missing Java 25 (openjdk-25-jdk-headless)"
    have_vulkan && say "vulkan: llvmpipe ICD present" || missing="$missing Mesa's Vulkan driver (mesa-vulkan-drivers)"
    have_import && say "import: $(command -v import)" || missing="$missing ImageMagick (imagemagick)"
    [ -e "$jre" ] && say "jre link: $jre" || missing="$missing the JRE symlink at $jre"
    [ -f "$root/client26/classpath-$VERSION.txt" ] && say "client: $root/client26" || missing="$missing the client files (tools/fetch_client.py)"
    [ -f "$root/server26/server.jar" ] && say "server jar: $root/server26/server.jar" || missing="$missing server.jar (tools/fetch_client.py --server)"
    [ -f "$root/server26/.rcon_pw" ] && say "rcon password: in place" || missing="$missing server26/.rcon_pw"
    if [ -n "$missing" ]; then
      say "missing:$missing"
      return 1
    fi
    say "ready for the game"
    return 0
  fi

  # 1. the system packages. This is the one job allowed to install them; the Python venv is
  #    cloud_setup.sh's and gets nothing added.
  local pkgs=()
  have_java25 || pkgs+=("openjdk-25-jdk-headless")
  have_vulkan || pkgs+=("mesa-vulkan-drivers")
  have_import || pkgs+=("imagemagick")
  # only for looking at the machine by hand; the game does not need them
  dpkg -s mesa-utils >/dev/null 2>&1 || pkgs+=("mesa-utils")
  dpkg -s vulkan-tools >/dev/null 2>&1 || pkgs+=("vulkan-tools")
  if [ ${#pkgs[@]} ]; then
    say "apt: installing ${pkgs[*]}"
    sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq </dev/null >/dev/null 2>&1 || true
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${pkgs[@]}" </dev/null >/dev/null \
      || die "apt-get could not install ${pkgs[*]}"
  else
    say "apt: all there"
  fi
  have_java25 || die "Java 25 is not at $java_dir after installing it"
  have_vulkan || die "Mesa's llvmpipe Vulkan driver is not in /usr/share/vulkan/icd.d"
  have_import || die "ImageMagick's import is not on the path"
  say "java 25: $("$java_dir/bin/java" -version 2>&1 | head -1)"
  say "vulkan: llvmpipe ICD present"

  # 2. the JRE path the scripts look for. They were written on Windows, where a JRE was unpacked by
  #    hand into this folder, so a symlink is enough and nothing has to be edited.
  mkdir -p "$root/jdk"
  if [ -e "$jre" ] && [ ! -L "$jre" ]; then
    say "jre: $jre is a real folder, leaving it alone"
  else
    ln -sfn "$java_dir" "$jre"
    say "jre: $jre -> $java_dir"
  fi

  # 3. the client and the server, from Mojang only. fetch_client.py checks every file's SHA-1.
  local py="$root/.venv/bin/python"
  [ -x "$py" ] || die "no Python venv at $py: run tools/cloud_setup.sh first"
  if [ -f "$root/client26/classpath-$VERSION.txt" ] && [ -f "$root/server26/server.jar" ]; then
    say "files: client and server jar already there"
  else
    say "files: fetching $VERSION from Mojang (about 320 MB, some 50 s)"
    mkdir -p "$root/server26"
    local tools_dir
    tools_dir="$(cd "$(dirname "$0")" 2>/dev/null && pwd || true)"
    [ -f "$tools_dir/fetch_client.py" ] || die "fetch_client.py is not beside this script"
    "$py" "$tools_dir/fetch_client.py" "$VERSION" "$root/client26" --skip-music --server "$root/server26" </dev/null \
      || die "fetch_client.py could not fetch the client files"
  fi

  # 4. the test server's own files. tools/winmc.py writes them on Windows; here they are written
  #    straight out, the same values. Only written when absent: a machine already set up keeps its
  #    world and its password.
  "$py" - "$root" "$SERVER_PORT" "$RCON_PORT" <<'PYEOF' || die "the server's files could not be written"
import os
import secrets
import sys

root, port, rcon_port = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
server = os.path.join(root, "server26")
os.makedirs(server, exist_ok=True)
os.makedirs(os.path.join(root, "client26", "game", "resourcepacks"), exist_ok=True)

pw_file = os.path.join(server, ".rcon_pw")
if not os.path.exists(pw_file):
    with open(pw_file, "w") as fh:
        fh.write(secrets.token_hex(16))
with open(pw_file) as fh:
    password = fh.read().strip()
os.chmod(pw_file, 0o600)

# The same table as tools/winmc.py's SERVER_PROPERTIES. server-ip is the one rule left from the
# admin's computer: the test server listens on 127.0.0.1 only.
PROPERTIES = """\
allow-flight=true
broadcast-console-to-ops=true
broadcast-rcon-to-ops=false
difficulty=easy
enable-rcon=true
enable-status=true
force-gamemode=true
function-permission-level=2
gamemode=spectator
generate-structures=false
generator-settings={{"biome":"minecraft:the_void","layers":[{{"block":"minecraft:air","height":1}}]}}
level-name=art
level-type=minecraft:flat
max-chained-neighbor-updates=1000000
max-players=10
max-tick-time=-1
motd=c164 local test
online-mode=false
op-permission-level=4
pause-when-empty-seconds=-1
player-idle-timeout=0
rcon.password={password}
rcon.port={rcon_port}
server-ip=127.0.0.1
server-port={port}
simulation-distance=6
spawn-protection=0
sync-chunk-writes=false
view-distance=14
white-list=false
"""
props = os.path.join(server, "server.properties")
if not os.path.exists(props):
    with open(props, "w", encoding="utf-8") as fh:
        fh.write(PROPERTIES.format(password=password, port=port, rcon_port=rcon_port))
    print("written: " + props)
else:
    print("kept: " + props)

eula = os.path.join(server, "eula.txt")
if not os.path.exists(eula):
    with open(eula, "w") as fh:
        fh.write("eula=true\n")
    print("written: " + eula)
else:
    print("kept: " + eula)

# The client's options. tools/winmc.py's OPTIONS, with what the pictures depend on. A resource pack
# named c164art is expected under resourcepacks/; tools/makepack.py writes it.
OPTIONS = """\
version:5023
ao:true
biomeBlendRadius:2
chunkSectionFadeInTime:0.0
cutoutLeaves:true
enableVsync:false
entityDistanceScaling:1.0
entityShadows:true
fov:0.0
fovEffectScale:0.0
graphicsPreset:"custom"
fullscreen:false
gamma:0.5
guiScale:2
maxAnisotropyBit:2
textureFiltering:0
maxFps:60
improvedTransparency:false
inactivityFpsLimit:"minimized"
mipmapLevels:4
narrator:0
particles:0
renderClouds:"true"
cloudRange:128
renderDistance:14
simulationDistance:5
vignette:false
weatherRadius:10
autoJump:false
realmsNotifications:false
bobView:false
resourcePacks:["vanilla","file/c164art"]
incompatibleResourcePacks:[]
lang:en_us
chatVisibility:2
pauseOnLostFocus:false
tutorialStep:none
skipMultiplayerWarning:true
joinedFirstServer:true
onboardAccessibility:false
telemetryOptInExtra:false
musicToast:"never"
soundCategory_master:0.0
"""
options = os.path.join(root, "client26", "game", "options.txt")
if not os.path.exists(options):
    with open(options, "w", encoding="utf-8") as fh:
        fh.write(OPTIONS)
    print("written: " + options)
else:
    print("kept: " + options)
PYEOF
  say "server files: written where they were missing"

  # 5. a last look, the same questions --check-only asks
  main --check-only
  say "ready for the game. Start it with tools/mc.sh server-up, place a scene, then mc.sh client-up;"
  say "the whole round is in plan/roles/S1-cloud-notes.md, sections 5 to 10."
}

main "$@"
