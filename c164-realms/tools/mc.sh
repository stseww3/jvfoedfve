#!/usr/bin/env bash
# Start and stop the local test server and the picture client, each in its own tmux session.
#
#   mc.sh up        server, then client; returns when the camera player has joined
#   mc.sh down      client, then server
#   mc.sh restart   down + up (needed after biome or timeline files change)
#   mc.sh status
#
# Environment: MC_ROOT (default /agent/realms-study), MC_WORLD (level-name, default art),
#              MC_SERVER_HEAP (default 1500M), MC_CLIENT_HEAP (default 2G, see run_client.sh).
set -euo pipefail

ROOT="${MC_ROOT:-/agent/realms-study}"
SERVER="$ROOT/server26"
JAVA="${JAVA:-$ROOT/jdk/jdk-25.0.5+8-jre/bin/java}"
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PY:-$ROOT/.venv/bin/python}"
S_SES="c164-mc-server"
C_SES="c164-mc-client"
CAM="${MC_CAM:-C164Cam}"
TMUX_CONF=/exec-daemon/tmux.portal.conf
[ -f "$TMUX_CONF" ] && T=(tmux -f "$TMUX_CONF") || T=(tmux)

rcon() { "$PY" "$HERE/rcon.py" --pw-file "$SERVER/.rcon_pw" "$@"; }
has() { "${T[@]}" has-session -t "=$1" 2>/dev/null; }

REAL_ROOT="$(readlink -f "$ROOT")"

# Pids of our own java processes matching a command line pattern. The machine is shared: other
# people run java, game servers and the tmux server itself here, and a bare pattern match could
# hit those. Ours run a java binary that lives under $ROOT, or at least were started in there.
mine() {
  local pid exe cwd
  for pid in $(pgrep -f "$1" || true); do
    exe="$(readlink "/proc/$pid/exe" 2>/dev/null || true)"
    cwd="$(readlink "/proc/$pid/cwd" 2>/dev/null || true)"
    case "$exe" in
      "$REAL_ROOT"/*) echo "$pid" ;;
      */java) case "$cwd" in "$REAL_ROOT"|"$REAL_ROOT"/*) echo "$pid" ;; esac ;;
    esac
  done
}

# If the machine runs out of memory, ours should be the ones to go, not someone else's job.
yield_memory() {
  local pid
  for pid in $(mine "$1"); do
    echo 600 > "/proc/$pid/oom_score_adj" 2>/dev/null || true
  done
}

server_up() {
  if has "$S_SES"; then echo "server session already there"; else
    "${T[@]}" new-session -d -s "$S_SES" -c "$SERVER" \
      "nice -n 10 '$JAVA' -Xms512M -Xmx${MC_SERVER_HEAP:-1500M} -jar server.jar nogui 2>&1 | tee console.log"
  fi
  for _ in $(seq 1 200); do
    yield_memory "server.jar nogui"
    if rcon "list" >/dev/null 2>&1; then echo "server is up"; return 0; fi
    sleep 2
  done
  echo "server did not come up; see $SERVER/console.log" >&2; return 1
}

client_up() {
  if has "$C_SES"; then echo "client session already there"; else
    "${T[@]}" new-session -d -s "$C_SES" -c "$ROOT" \
      "'$HERE/run_client.sh' '$CAM' 2>&1 | tee '$ROOT/client26/client.log'"
  fi
  for _ in $(seq 1 240); do
    yield_memory "net.minecraft.client.main.Main.*--username $CAM"
    if rcon "list" 2>/dev/null | grep -q "$CAM"; then echo "$CAM is online"; return 0; fi
    sleep 2
  done
  echo "$CAM did not join; see $ROOT/client26/client.log" >&2; return 1
}

client_down() {
  if has "$C_SES"; then
    local pid
    for pid in $(mine "net.minecraft.client.main.Main.*--username $CAM"); do
      kill "$pid" 2>/dev/null || true
    done
    sleep 2
    "${T[@]}" kill-session -t "=$C_SES" 2>/dev/null || true
    echo "client stopped"
  fi
}

server_down() {
  if has "$S_SES"; then
    rcon "save-all flush" "stop" >/dev/null 2>&1 || true
    for _ in $(seq 1 30); do has "$S_SES" || break; sleep 1; done
    "${T[@]}" kill-session -t "=$S_SES" 2>/dev/null || true
    echo "server stopped"
  fi
}

case "${1:-status}" in
  up) server_up; client_up ;;
  down) client_down; server_down ;;
  restart) client_down; server_down; server_up; client_up ;;
  server-up) server_up ;;
  server-down) server_down ;;
  client-up) client_up ;;
  client-down) client_down ;;
  status)
    has "$S_SES" && echo "server session: yes" || echo "server session: no"
    has "$C_SES" && echo "client session: yes" || echo "client session: no"
    rcon "list" 2>/dev/null || echo "rcon: no answer"
    ;;
  *) echo "usage: mc.sh up|down|restart|status|server-up|server-down|client-up|client-down" >&2; exit 2 ;;
esac
