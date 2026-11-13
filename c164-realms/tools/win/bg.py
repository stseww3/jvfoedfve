"""Run a command in the background: output to logs/<name>.log, exit code to logs/<name>.rc.

    python bg.py <name> <command> [args...]

The caller returns at once. logs/<name>.pid holds the process id while the command runs.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LOGS = os.path.join(ROOT, "logs")


def child(name, cmd):
    rc = 127
    with open(os.path.join(LOGS, name + ".log"), "ab", buffering=0) as log:
        try:
            p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, cwd=ROOT)
            with open(os.path.join(LOGS, name + ".pid"), "w") as fh:
                fh.write(str(p.pid))
            rc = p.wait()
        except Exception as exc:
            log.write(f"bg: {exc!r}\n".encode())
    with open(os.path.join(LOGS, name + ".rc"), "w") as fh:
        fh.write(str(rc))


def main():
    if sys.argv[1] == "--child":
        child(sys.argv[2], sys.argv[3:])
        return
    name, cmd = sys.argv[1], sys.argv[2:]
    os.makedirs(LOGS, exist_ok=True)
    for ext in (".rc", ".log", ".pid"):
        try:
            os.remove(os.path.join(LOGS, name + ext))
        except FileNotFoundError:
            pass
    flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "--child", name] + cmd, creationflags=flags,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     close_fds=True, cwd=ROOT)
    print(f"started {name}")


if __name__ == "__main__":
    main()
