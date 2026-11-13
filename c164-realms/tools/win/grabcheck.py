#!/usr/bin/env python3
"""Diagnose the game-window capture (why shoot.py reports an empty picture).

    grabcheck.py --out <dir> [--keys]

Finds the game window (client26/client.pid under MC_ROOT), keeps it in the background (winctl.settle),
then grabs it with several PrintWindow flag combinations and reports the extrema of each, saving every
result as <out>/grab-<name>.png. A uniformly black client area means that combination cannot read the
window's OpenGL content. Look at the saved pictures before believing the numbers: without
PW_CLIENTONLY the title bar is in the picture and is not black even when the game's area is.

--keys also tries the game's own screenshot: the F2 key is posted to the window's message queue
(nothing is typed on the desktop and the window stays where it is) and the screenshots folder is
watched for a new file, which is copied to <out>/key-<variant>.png.

The camera and the server are not touched, so this is safe to run while a shoot is not in progress.
"""
import ctypes
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # c164-realms/tools, where winctl lives

import winctl as W  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = os.environ.get("MC_ROOT", os.getcwd())
WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101
VK_F2, SCAN_F2 = 0x71, 0x3C


def press(hwnd, vk, scan):
    """Post one key press and release to the window's own message queue."""
    down = 1 | (scan << 16)
    W.user32.PostMessageW(hwnd, WM_KEYDOWN, vk, down)
    time.sleep(0.08)
    W.user32.PostMessageW(hwnd, WM_KEYUP, vk, down | (1 << 30) | (1 << 31))


def listing(folder):
    return set(os.listdir(folder)) if os.path.isdir(folder) else set()


def new_file(folder, before, wait):
    end = time.monotonic() + wait
    while time.monotonic() < end:
        fresh = sorted(listing(folder) - before)
        if fresh:
            return os.path.join(folder, fresh[-1])
        time.sleep(0.2)
    return None


def load(path, tries=10):
    """The picture in a file that the game may still be writing."""
    for _ in range(tries):
        try:
            with Image.open(path) as img:
                return img.convert("RGB")
        except (OSError, SyntaxError):
            time.sleep(0.3)
    return None


def keys(hwnd, out):
    shots = os.path.join(ROOT, "client26", "game", "screenshots")
    # scan: the key as a keyboard sends it; virtual: no scan code, for a window library that takes
    # hardware keys from elsewhere; enabled: as scan, with the window allowed to take input meanwhile.
    for name, scan, enable in (("scan", SCAN_F2, False), ("virtual", 0, False), ("enabled", SCAN_F2, True)):
        before = listing(shots)
        if enable:
            W.user32.EnableWindow(hwnd, True)
        try:
            press(hwnd, VK_F2, scan)
            path = new_file(shots, before, 6.0)
        finally:
            W.settle(hwnd)
        if not path:
            print(f"key {name:8s}: no screenshot appeared in {shots}")
            continue
        img = load(path)
        if img is None:
            print(f"key {name:8s}: {os.path.basename(path)} appeared but cannot be read")
            continue
        ex = img.getextrema()
        img.save(os.path.join(out, f"key-{name}.png"))
        print(f"key {name:8s}: {os.path.basename(path)} {img.size}, extrema={ex}, "
              f"uniform={ex in (((0, 0),) * 3, ((255, 255),) * 3)}")
        return True
    return False


def grab(hwnd, flags):
    width, height = W.client_size(hwnd)
    if width <= 0 or height <= 0:
        return None, None
    window_dc = W.user32.GetDC(hwnd)
    memory_dc = W.gdi32.CreateCompatibleDC(window_dc)
    bitmap = W.gdi32.CreateCompatibleBitmap(window_dc, width, height)
    before = W.gdi32.SelectObject(memory_dc, bitmap)
    try:
        ok = W.user32.PrintWindow(hwnd, memory_dc, flags)
        info = W.BITMAPINFOHEADER()
        info.biSize = ctypes.sizeof(W.BITMAPINFOHEADER)
        info.biWidth, info.biHeight = width, -height
        info.biPlanes, info.biBitCount, info.biCompression = 1, 32, 0
        rows = ctypes.create_string_buffer(width * height * 4)
        if W.gdi32.GetDIBits(memory_dc, bitmap, 0, height, rows, ctypes.byref(info), 0) != height:
            return ok, None
        return ok, Image.frombuffer("RGBA", (width, height), rows.raw, "raw", "BGRA", 0, 1).convert("RGB")
    finally:
        W.gdi32.SelectObject(memory_dc, before)
        W.gdi32.DeleteObject(bitmap)
        W.gdi32.DeleteDC(memory_dc)
        W.user32.ReleaseDC(hwnd, window_dc)


def main():
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "."
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(ROOT, "client26", "client.pid")) as fh:
        pid = int(fh.read().strip())
    windows = W.game_windows(pid)
    print(f"pid {pid}, windows {[W.client_size(h) for h in windows]}, in_front {[W.in_front(h) for h in windows]}")
    if not windows:
        raise SystemExit("no window")
    hwnd = windows[0]
    W.settle(hwnd)
    combos = {"full": W.PW_CLIENTONLY | W.PW_RENDERFULLCONTENT, "render": W.PW_RENDERFULLCONTENT,
              "client": W.PW_CLIENTONLY, "none": 0}
    for name, flags in combos.items():
        ok, img = grab(hwnd, flags)
        if img is None:
            print(f"{name:7s} flags={flags}: PrintWindow={ok}, no bitmap")
            continue
        ex = img.getextrema()
        px = img.getpixel((img.width // 2, img.height // 2))
        uniform = ex in (((0, 0),) * 3, ((255, 255),) * 3)
        img.save(os.path.join(out, f"grab-{name}.png"))
        print(f"{name:7s} flags={flags}: PrintWindow={ok}, extrema={ex}, centre={px}, uniform={uniform}")
    if "--keys" in sys.argv:
        keys(hwnd, out)


if __name__ == "__main__":
    main()
