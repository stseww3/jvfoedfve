"""Run one of the repository's Python scripts in the shared workspace, politely.

    python bin/job.py <part> [--heavy] [--wait 900] [--timeout 1500] -- <script> [args...]

<part> is a0 (the integration copy) or a part's folder under agents/ (a1, a2, ...). The script path
is relative to that part's copy of c164-realms/build, and the script runs there with the workspace's
Python, e.g.

    python bin/job.py a1 -- preview.py obs_a1 --out @out/preview
    python bin/job.py a1 --heavy -- render.py obs_a1 --shots scenes/obs_a1/shots.json --out @out/board

What it takes care of, because the machine is somebody's desktop and several parts share it:
  - the job runs below normal priority, so the owner's work and other programs come first;
  - thread pools are capped (bin/limits.json, "threads");
  - --heavy takes the one heavy slot (offline rendering and anything else that fills the cores):
    one such job runs at a time in the whole workspace, the others wait in line for --wait seconds
    and then give up;
  - in the arguments @out stands for the part's out/ folder and @root for the workspace;
  - the output goes to the console and to the part's logs/ folder;
  - scripts that drive the test server or the game are refused unless the part is a0.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK = os.path.join(ROOT, "locks", "heavy.lock")
SERVER_AND_GAME = {"winmc.py", "winctl.py", "shoot.py", "place.py", "gallery.py", "rcon.py", "mcbot.py",
                   "fetch_client.py", "inbox.py"}
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


def holder():
    try:
        with open(LOCK) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def take_slot(part, script, wait):
    """The heavy slot is a file that exists while its owner runs; a dead owner's file is cleared."""
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    told, t0 = False, time.time()
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            h = holder()
            if h is None or not alive(int(h.get("pid", 0))):
                try:
                    os.remove(LOCK)
                except OSError:
                    pass
                time.sleep(0.2)
                continue
            if not told:
                print(f"[job] heavy slot is taken by {h.get('part')} ({h.get('script')}, since {h.get('since')}); "
                      f"waiting up to {wait} s", flush=True)
                told = True
            if time.time() - t0 > wait:
                print("[job] gave up waiting for the heavy slot; try again later", flush=True)
                return False
            time.sleep(2)
            continue
        with os.fdopen(fd, "w") as fh:
            json.dump({"pid": os.getpid(), "part": part, "script": script,
                       "since": datetime.datetime.now().strftime("%H:%M:%S")}, fh)
        return True


def release_slot():
    h = holder()
    if h and int(h.get("pid", 0)) == os.getpid():
        try:
            os.remove(LOCK)
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
    if not re.fullmatch(r"a\d{1,2}", args.part):
        sys.exit("part must be a0, a1, a2, ...")
    home = ROOT if args.part == "a0" else os.path.join(ROOT, "agents", args.part)
    repo = os.path.join(home, "repo")
    build = os.path.join(repo, "c164-realms", "build")
    if not os.path.isdir(build):
        sys.exit(f"no copy of the code in {repo}: run bin/sync.py <branch> --to agents/{args.part} first")
    script = cmd[0]
    if args.part != "a0" and os.path.basename(script).lower() in SERVER_AND_GAME:
        sys.exit(f"{os.path.basename(script)} drives the test server or the game; only a0 runs it. Ask A0 in the group.")
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
    env.update(MC_ROOT=ROOT, MC_JAR=os.path.join(ROOT, "client26", "versions", "26.3", "26.3.jar"),
               PYTHONUTF8="1", PYTHONUNBUFFERED="1", C164_PART=args.part, C164_OUT=out)
    python = os.path.join(ROOT, "venv", "Scripts", "python.exe")
    if not os.path.exists(python):
        python = sys.executable

    if args.heavy and not take_slot(args.part, script, args.wait):
        sys.exit(75)
    code = 1
    try:
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
        if args.heavy:
            release_slot()
    sys.exit(code)


if __name__ == "__main__":
    main()
