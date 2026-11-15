"""At most a few heavy jobs at once on the one machine the whole team shares (COMMON.md section 2).

Whoever runs one of the heavy entry points (check.py, selfshots.py, delivery.py, boardshots.py,
build/render.py) calls take() once, after dropping its own priority. The call takes a slot and keeps
it until the process ends: a job that has a slot runs; one that finds every slot taken waits, a
second at a time, and says so once on stderr.

  * C164_SLOT already set in the environment: a parent process holds it (delivery.py runs check.py in
    itself, selfshots.py draws inside the same process). Nothing to do -- a child must not wait for a
    second slot, and must not take one that its parent already has.
  * no fcntl (Windows): nothing to do. The shared machine is the Linux one.
  * otherwise: try /tmp/c164-slots/slot0, slot1, ... up to C164_SLOTS (default 3) with
    fcntl.flock(LOCK_EX | LOCK_NB). The first one that locks is ours; the open file object is kept in
    this module for the life of the process, so the lock goes when the process does, even if it is
    killed.

A refusal to make the directory or to lock is not an error: the job runs anyway rather than failing
for want of a queue (a full /tmp must not stop the work).
"""
import os
import sys

SLOTS = int(os.environ.get("C164_SLOTS", "3") or 3)
FOLDER = os.environ.get("C164_SLOT_DIR", "/tmp/c164-slots")
_held = []                      # the open file the lock lives on, kept until the process ends


def take():
    """Take one slot of the machine, or wait for one. Returns True when this process holds a slot."""
    if os.environ.get("C164_SLOT"):
        return True
    try:
        import fcntl
    except ImportError:
        return False
    try:
        os.makedirs(FOLDER, exist_ok=True)
        try:
            os.chmod(FOLDER, 0o1777)
        except OSError:
            pass
    except OSError:
        return False
    said = False
    while True:
        for i in range(SLOTS):
            path = os.path.join(FOLDER, f"slot{i}")
            try:
                fh = open(path, "a+")
            except OSError:
                continue
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                fh.close()
                continue
            _held.append(fh)
            os.environ["C164_SLOT"] = path
            return True
        if not said:
            print("waiting for a free slot (shared machine)", file=sys.stderr, flush=True)
            said = True
        import time
        time.sleep(1.0)
