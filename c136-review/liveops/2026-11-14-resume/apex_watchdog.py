# -*- coding: utf-8 -*-
# apex_watchdog.py - keep the c116 SOCKS proxy (and optionally the engine) alive on d3.
#
# Why this exists: on 2026-11-14 the proxy (tun_apex_socks5.py) died silently around 03:57.
# With the proxy gone, all 40 bots could no longer reach the game server (socket close 1006 /
# 4406), the squad stopped entering games at 03:57, and the whole team sat dead until ~07:25
# with nobody watching. Token minting was fine the entire time (donors run direct), so the
# single point of failure was the proxy process. This watchdog polls the proxy and restarts
# it the moment it stops accepting connections, so a repeat cannot go unnoticed for hours.
#
# Design choices:
#   - Proxy is restarted automatically (cheap, safe, costs no Cloudflare budget).
#   - The engine is restarted ONLY when the opt-in flag file tsb-engine-guard.flag exists,
#     because restarting the engine re-mints ~40 tokens and the admin may stop it on purpose.
#   - Paths are derived from this file's own location (…/workspaces/<here> -> …/workspaces/c116)
#     and the python to launch the proxy is sys.executable, so there is nothing to hardcode and
#     no path-encoding pitfalls.
#   - A TCP singleton lock (127.0.0.1:19955) prevents two watchdogs running at once.
#   - Delete apex_watchdog.run (in c116) to stop the watchdog cleanly within one poll.
#
# Run detached on d3 with the same python that runs the proxy:
#   <python> apex_watchdog.py        (launch hidden / detached)

import datetime
import os
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACES = os.path.dirname(HERE)
C116 = os.path.join(WORKSPACES, "c116")
PROXY_SCRIPT = os.path.join(C116, "tun_apex_socks5.py")
PY = sys.executable
LOG = os.path.join(C116, "apex_watchdog.log")
RUNFLAG = os.path.join(C116, "apex_watchdog.run")
HEARTBEAT = os.path.join(C116, "apex_watchdog.heartbeat")
ENGINE_GUARD_FLAG = os.path.join(C116, "tsb-engine-guard.flag")
ENGINE_EXE = os.path.join(C116, "node_apex.exe")
ENGINE_SCRIPT = "tsb-apex-squad.mjs"

PROXY_PORT = 10821          # first of the 10821-10860 pool; proxy binds all of them
SINGLETON_PORT = 19955     # arbitrary unused loopback port used as a one-instance lock
POLL_SEC = 20
PROXY_RESTART_GRACE_SEC = 6

DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP (Windows)


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "[%s] %s" % (ts, msg)
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def tcp_open(port, timeout=2.0):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except Exception:
        return False


def acquire_singleton():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", SINGLETON_PORT))
        s.listen(1)
        return s
    except OSError:
        s.close()
        return None


def image_running(image):
    # Returns True if a process with this image name is running. On any error we return True
    # so the watchdog never restarts the engine just because the check itself failed.
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq %s" % image, "/NH"],
            capture_output=True, text=True, timeout=10,
        )
        return image.lower() in (out.stdout or "").lower()
    except Exception:
        return True


def start_proxy():
    out = open(os.path.join(C116, "tun_apex.out.log"), "a", encoding="utf-8", errors="ignore")
    err = open(os.path.join(C116, "tun_apex.err.log"), "a", encoding="utf-8", errors="ignore")
    subprocess.Popen(
        [PY, PROXY_SCRIPT], cwd=C116,
        stdout=out, stderr=err, stdin=subprocess.DEVNULL,
        creationflags=DETACHED, close_fds=True,
    )


def start_engine():
    subprocess.Popen(
        [ENGINE_EXE, ENGINE_SCRIPT], cwd=C116,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
        creationflags=DETACHED, close_fds=True,
    )


def main():
    lock = acquire_singleton()
    if lock is None:
        log("another watchdog already holds the singleton lock on :%d -> exiting" % SINGLETON_PORT)
        return
    try:
        with open(RUNFLAG, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass
    log("watchdog started pid=%d  c116=%s  python=%s" % (os.getpid(), C116, PY))

    proxy_restarts = 0
    engine_restarts = 0
    while True:
        try:
            if not os.path.exists(RUNFLAG):
                log("run flag removed -> watchdog stopping")
                break
            try:
                with open(HEARTBEAT, "w", encoding="utf-8") as f:
                    f.write(datetime.datetime.now().isoformat())
            except Exception:
                pass

            if not tcp_open(PROXY_PORT):
                proxy_restarts += 1
                log("proxy DOWN (:%d not accepting) -> restart #%d" % (PROXY_PORT, proxy_restarts))
                start_proxy()
                time.sleep(PROXY_RESTART_GRACE_SEC)
                log("proxy after restart: up=%s" % tcp_open(PROXY_PORT))

            if os.path.exists(ENGINE_GUARD_FLAG) and not image_running("node_apex.exe"):
                engine_restarts += 1
                log("engine guard ON and node_apex.exe not running -> restart engine #%d" % engine_restarts)
                start_engine()
                time.sleep(PROXY_RESTART_GRACE_SEC)
        except Exception as e:
            log("loop error: %r" % e)
        time.sleep(POLL_SEC)


if __name__ == "__main__":
    main()
