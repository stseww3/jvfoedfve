#!/usr/bin/env python3
"""Diagnose the game-window capture (why shoot.py reports an empty picture).

    grabcheck.py --out <dir>

Finds the game window (client26/client.pid under MC_ROOT), keeps it in the background (winctl.settle),
then grabs it with several PrintWindow flag combinations and reports the extrema of each, saving every
result as <out>/grab-<name>.png. A uniformly black frame means that combination cannot read the
window's OpenGL content; a real frame proves which one works. The camera and the server are not
touched, so this is safe to run while a shoot is not in progress.
"""
import ctypes
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # c164-realms/tools, where winctl lives

import winctl as W  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = os.environ.get("MC_ROOT", os.getcwd())


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


if __name__ == "__main__":
    main()
