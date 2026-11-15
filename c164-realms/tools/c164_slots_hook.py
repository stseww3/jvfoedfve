"""Keep the whole team's heavy jobs inside a few slots on this one shared machine.

The director's order of 11-16: a worktree that has not merged the assembly has no tools/_slots.py
of its own, so its render.py did not queue at all and eighteen processes fought over four cores.

This file is installed into the shared virtualenv by tools/cloud_setup.sh and run at interpreter
startup (a .pth file in the same folder imports it), so it applies to every job whatever worktree
the job runs in. It does what tools/_slots.py does, from the outside:

  * a job whose script is render.py, selfshots.py, delivery.py or boardshots.py drops its priority
    and takes one of C164_SLOTS files (default 3) under /tmp/c164-slots, waiting a second at a time;
  * check.py gets slots of its own (C164_SLOTS of them): it runs in seconds and stands on every
    card's delivery path, so it must not queue behind a batch of pictures;
  * C164_SLOT set in the environment means a parent already holds one -- a child takes nothing and
    waits for nothing.

Every step is wrapped: any trouble at all and the job simply runs. A queue must never stop work,
and nothing here draws or changes a picture.
"""
import os
import sys

HEAVY = ("render.py", "selfshots.py", "delivery.py", "boardshots.py")
LIGHT = ("check.py",)
SLOTS = int(os.environ.get("C164_SLOTS", "3") or 3)
FOLDER = os.environ.get("C164_SLOT_DIR", "/tmp/c164-slots")
_held = []                      # the open files the locks live on, kept until the process ends


def _script():
    """The Python script this process was started on, by name, or None."""
    try:
        with open("/proc/self/cmdline", "rb") as fh:
            parts = [p.decode("utf-8", "replace") for p in fh.read().split(b"\0") if p]
    except OSError:
        return None
    for part in parts[1:]:
        if part.endswith(".py"):
            return os.path.basename(part)
    return None


def _take(prefix):
    """Take one of the files prefix0..prefix<n-1> with flock, waiting a second at a time."""
    try:
        import fcntl
    except ImportError:
        return False                  # Windows: there is no flock, and the shared machine is Linux
    try:
        os.makedirs(FOLDER, exist_ok=True)
        try:
            os.chmod(FOLDER, 0o1777)
        except OSError:
            pass
    except OSError:
        return False
    said = False
    import time
    while True:
        for i in range(SLOTS):
            path = os.path.join(FOLDER, "%s%d" % (prefix, i))
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
            return True
        if not said:
            try:
                sys.stderr.write("waiting for a free slot (shared machine)\n")
                sys.stderr.flush()
            except Exception:
                pass
            said = True
        time.sleep(1.0)


def _light_args():
    """Jobs that carry a heavy script's name but only shuffle files: no slot, no waiting.

    selfshots.py --take copies pictures into renders/ and checks their SHA-256; it draws nothing
    (c273 measured it stuck fifteen minutes behind an empty-looking queue while the same --take run
    through python -c finished in two seconds).
    """
    try:
        with open("/proc/self/cmdline", "rb") as fh:
            parts = [p.decode("utf-8", "replace") for p in fh.read().split(b"\0") if p]
    except OSError:
        return False
    return _script() == "selfshots.py" and "--take" in parts


def _boot():
    if os.environ.get("C164_SLOT"):
        return                        # a parent already holds one: a child must not wait for a second
    name = _script()
    if name is None:
        return
    if name in HEAVY:
        if _light_args():
            return                    # --take only copies files in: no slot to wait for
        try:
            os.nice(10)
        except (AttributeError, OSError):
            pass
        if _take("slot"):
            os.environ["C164_SLOT"] = os.path.join(FOLDER, "slot")
    elif name in LIGHT:
        if _take("check"):
            os.environ["C164_SLOT"] = os.path.join(FOLDER, "check")


try:
    _boot()
except Exception:
    pass
