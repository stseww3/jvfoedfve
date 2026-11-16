"""Run one of the repository's Python scripts in the shared workspace, politely.

    python bin/job.py <part> [--heavy] [--wait 900] [--timeout 1500] -- <script> [args...]

<part> is a0 (the integration copy) or a folder under agents/ (lamps, stone-b, ...). The script path
is relative to that part's copy of c164-realms/build, and the script runs there with the workspace's
Python, e.g.

    python bin/job.py lamps -- preview.py pkg_lamps --out @out/preview
    python bin/job.py lamps --heavy -- render.py pkg_lamps --shots scenes/pkg_lamps/shots.json --out @out/rt/x

What it takes care of, because the machine is somebody's desktop and many parts share it:
  - the job runs below normal priority, so the owner's work and other programs come first;
  - thread pools are capped (bin/limits.json, "threads");
  - --heavy takes a heavy slot (offline rendering and anything else that fills the cores): as many
    such jobs run at a time in the whole workspace as bin/limits.json allows ("heavy_slots", default
    1), the others wait in line for --wait seconds and then give up (exit code 75);
  - in the arguments @out stands for the part's out/ folder and @root for the workspace;
  - the output goes to the console and to the part's logs/ folder;
  - temporary files go to the part's tmp/ folder and are removed when the job ends; compiled-code
    caches go to the part's cache/ folder, so nothing is written outside the workspace;
  - scripts that drive the test server or the game are refused unless the part is one of the render
    station's (bin/limits.json, "operators", default ["a0"]).
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCKS = os.path.join(ROOT, "locks")
SERVER_AND_GAME = {"winmc.py", "winctl.py", "shoot.py", "place.py", "gallery.py", "rcon.py", "mcbot.py",
                   "fetch_client.py", "inbox.py", "shuttle.py"}
BELOW_NORMAL = 0x00004000


def limits():
    try:
        with open(os.path.join(ROOT, "bin", "limits.json")) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def alive(pid):
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
    import ctypes
    from ctypes import wintypes
    k = ctypes.windll.kernel32
    k.OpenProcess.restype = wintypes.HANDLE
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    h = k.OpenProcess(0x1000, False, pid)
    if not h:
        return False
    code = wintypes.DWORD()
    ok = k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return bool(ok) and code.value == 259


def holder(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def take_slot(part, script, wait):
    """A heavy slot is a file that exists while its owner runs; a dead owner's file is cleared.
    There are as many slots as bin/limits.json says ("heavy_slots", default 1). Returns the slot's
    file, or None when none came free in time."""
    os.makedirs(LOCKS, exist_ok=True)
    told, t0 = False, time.time()
    while True:
        slots = max(1, int(limits().get("heavy_slots", 1)))
        busy = []
        for n in range(slots):
            path = os.path.join(LOCKS, f"heavy-{n}.lock")
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                h = holder(path)
                if h is None or not alive(int(h.get("pid", 0))):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                else:
                    busy.append(h)
                continue
            with os.fdopen(fd, "w") as fh:
                json.dump({"pid": os.getpid(), "part": part, "script": script,
                           "since": datetime.datetime.now().strftime("%H:%M:%S")}, fh)
            return path
        if len(busy) < slots:
            time.sleep(0.2)   # a stale file was cleared: try again at once
            continue
        if not told:
            who = "; ".join(f"{h.get('part')} ({h.get('script')}, since {h.get('since')})" for h in busy)
            print(f"[job] heavy slots are taken by {who}; waiting up to {wait} s", flush=True)
            told = True
        if time.time() - t0 > wait:
            print("[job] gave up waiting for a heavy slot; try again later", flush=True)
            return None
        time.sleep(2)


def release_slot(path):
    h = holder(path)
    if h and int(h.get("pid", 0)) == os.getpid():
        try:
            os.remove(path)
        except OSError:
            pass


def kill_tree(p):
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
    else:
        p.kill()


def commit_of(repo):
    git = os.path.join(ROOT, "git", "cmd", "git.exe")
    if not (os.path.exists(git) and os.path.isdir(os.path.join(repo, ".git"))):
        return "?"
    got = subprocess.run([git, "-C", repo, "log", "-1", "--format=%h %s"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    return got.stdout.strip() or "?"


def main():
    argv = sys.argv[1:]
    if "--" not in argv:
        sys.exit(__doc__)
    cut = argv.index("--")
    ap = argparse.ArgumentParser()
    ap.add_argument("part")
    ap.add_argument("--heavy", action="store_true")
    ap.add_argument("--wait", type=int, default=900)
    ap.add_argument("--timeout", type=int, default=1500)
    args = ap.parse_args(argv[:cut])
    cmd = argv[cut + 1:]
    if not cmd:
        sys.exit(__doc__)
    if not re.fullmatch(r"[a-z][a-z0-9_-]{1,31}", args.part):
        sys.exit("part must be a0 or a folder name under agents/: lower-case letters, digits, _ and -")
    home = ROOT if args.part == "a0" else os.path.join(ROOT, "agents", args.part)
    repo = os.path.join(home, "repo")
    build = os.path.join(repo, "c164-realms", "build")
    if not os.path.isdir(build):
        sys.exit(f"no copy of the code in {repo}: run bin/sync.py <branch> --to agents/{args.part} first")
    script = cmd[0]
    operators = limits().get("operators", ["a0"])
    if args.part not in operators and os.path.basename(script).lower() in SERVER_AND_GAME:
        sys.exit(f"{os.path.basename(script)} drives the test server or the game; only the render station "
                 f"({', '.join(operators)}) runs it. Ask for real-game pictures in the group.")
    if not os.path.exists(os.path.join(build, script)):
        sys.exit(f"no such script: {os.path.join(build, script)}")
    out = os.path.join(home, "out")
    logs = os.path.join(home, "logs")
    os.makedirs(out, exist_ok=True)
    os.makedirs(logs, exist_ok=True)
    rest = [a.replace("@out", out).replace("@root", ROOT) for a in cmd[1:]]

    threads = str(int(limits().get("threads", 6)))
    env = dict(os.environ)
    for name in ("NUMBA_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        env[name] = threads
    # Temporary files and compiled-code caches stay inside the workspace too.
    scratch = os.path.join(home, "tmp", f"job-{os.getpid()}")
    env.update(MC_ROOT=ROOT, MC_JAR=os.path.join(ROOT, "client26", "versions", "26.3", "26.3.jar"),
               PYTHONUTF8="1", PYTHONUNBUFFERED="1", C164_PART=args.part, C164_OUT=out,
               TEMP=scratch, TMP=scratch, TMPDIR=scratch, NUMBA_CACHE_DIR=os.path.join(home, "cache", "numba"))
    python = os.path.join(ROOT, "venv", "Scripts", "python.exe")
    if not os.path.exists(python):
        python = sys.executable

    slot = None
    if args.heavy:
        slot = take_slot(args.part, script, args.wait)
        if slot is None:
            sys.exit(75)
    code = 1
    try:
        os.makedirs(scratch, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        log_path = os.path.join(logs, f"job-{stamp}-{os.getpid()}.log")
        head = (f"[job] {args.part} at {commit_of(repo)} | {script} {' '.join(rest)} | threads {threads}"
                f"{' | heavy' if args.heavy else ''}")
        t0 = time.time()
        with open(log_path, "wb") as log:
            log.write((head + "\n").encode("utf-8"))
            print(head, flush=True)
            p = subprocess.Popen([python, script] + rest, cwd=build, env=env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 creationflags=BELOW_NORMAL if os.name == "nt" else 0)
            timer = threading.Timer(args.timeout, kill_tree, [p])
            timer.daemon = True
            timer.start()
            try:
                for line in p.stdout:
                    log.write(line)
                    sys.stdout.buffer.write(line)
                    sys.stdout.buffer.flush()
                code = p.wait()
            finally:
                timer.cancel()
            tail = f"[job] exit {code} after {time.time() - t0:.0f} s; log {os.path.relpath(log_path, ROOT)}"
            if time.time() - t0 >= args.timeout:
                tail += f" (stopped at the {args.timeout} s limit)"
            log.write((tail + "\n").encode("utf-8"))
            print(tail, flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        if slot:
            release_slot(slot)
    sys.exit(code)


if __name__ == "__main__":
    main()
