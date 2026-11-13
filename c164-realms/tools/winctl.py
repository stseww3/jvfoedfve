"""Windows only: processes of our own, the game's window, a key pressed in it, free video memory.

Used by winmc.py and shoot.py when the client runs as an ordinary window on a desktop that
somebody else may be working on.
"""
import ctypes
import os
import subprocess
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

# Sizes are wanted in real pixels. Without this a scaled desktop reports them shrunk and hands
# out stretched pictures.
try:
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))      # per monitor, version 2
except (AttributeError, OSError):
    pass

WM_CLOSE, WM_KEYDOWN, WM_KEYUP = 0x0010, 0x0100, 0x0101
SW_SHOWNOACTIVATE, SW_MINIMIZE = 4, 6
HWND_BOTTOM = 1
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x0001, 0x0002, 0x0010
PW_CLIENTONLY, PW_RENDERFULLCONTENT = 0x1, 0x2
PROCESS_QUERY_LIMITED_INFORMATION, PROCESS_TERMINATE = 0x1000, 0x0001
STILL_ACTIVE = 259
# virtual key and scan code
KEYS = {"F1": (0x70, 0x3B), "F2": (0x71, 0x3C)}


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


_ENUM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [_ENUM, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.GetDC.argtypes = [wintypes.HWND]
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, ctypes.c_void_p,
                            ctypes.c_void_p, wintypes.UINT]
user32.IsIconic.argtypes = [wintypes.HWND]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, wintypes.UINT]
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                ctypes.POINTER(wintypes.DWORD)]
kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


# ---- processes -------------------------------------------------------------------------------------
def image(pid):
    """Full path of a running process's program, or None when there is no such process."""
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != STILL_ACTIVE:
            return None
        size = wintypes.DWORD(1024)
        name = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size)):
            return None
        return name.value
    finally:
        kernel32.CloseHandle(handle)


def ours(pid, root):
    """True when the process runs a program that lives under `root`. The machine is shared: nothing
    is ever stopped on the strength of a number in a file alone."""
    path = image(pid)
    if not path:
        return False
    root = os.path.normcase(os.path.abspath(root)) + os.sep
    return os.path.normcase(os.path.abspath(path)).startswith(root)


def stop(pid, root):
    """End one of our own processes."""
    if not ours(pid, root):
        return False
    handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not handle:
        return False
    try:
        return bool(kernel32.TerminateProcess(handle, 1))
    finally:
        kernel32.CloseHandle(handle)


def start(cmd, cwd, log, env=None):
    """Start a program that outlives the caller, without a console window; its output goes to `log`."""
    with open(log, "ab", buffering=0) as out:
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                env=env, close_fds=True,
                                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
    return proc.pid


# ---- the game's window -------------------------------------------------------------------------------
def client_size(hwnd):
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    return rect.right - rect.left, rect.bottom - rect.top


def game_windows(pid):
    """Visible top-level windows of one process, the largest first. A minimised window counts too
    (its drawing area reads as nothing while it is down)."""
    found = []

    def each(hwnd, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
            found.append(hwnd)
        return True

    user32.EnumWindows(_ENUM(each), 0)
    found.sort(key=lambda h: -client_size(h)[0] * client_size(h)[1])
    return found


def grab(hwnd):
    """What the window last drew, without bringing it to the front: (width, height, rows of
    blue-green-red-unused bytes from the top), or None when the system gave nothing."""
    width, height = client_size(hwnd)
    if width <= 0 or height <= 0:
        return None
    window_dc = user32.GetDC(hwnd)
    memory_dc = gdi32.CreateCompatibleDC(window_dc)
    bitmap = gdi32.CreateCompatibleBitmap(window_dc, width, height)
    before = gdi32.SelectObject(memory_dc, bitmap)
    try:
        if not user32.PrintWindow(hwnd, memory_dc, PW_CLIENTONLY | PW_RENDERFULLCONTENT):
            return None
        info = BITMAPINFOHEADER()
        info.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        info.biWidth, info.biHeight = width, -height           # negative: rows from the top
        info.biPlanes, info.biBitCount, info.biCompression = 1, 32, 0
        rows = ctypes.create_string_buffer(width * height * 4)
        if gdi32.GetDIBits(memory_dc, bitmap, 0, height, rows, ctypes.byref(info), 0) != height:
            return None
        return width, height, rows.raw
    finally:
        gdi32.SelectObject(memory_dc, before)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(hwnd, window_dc)


def step_back(hwnd):
    """Keep the window drawn but out of the way: no keyboard, no mouse, behind the other windows.

    A game window that holds the keyboard grabs the mouse as soon as a world is on screen. If it
    is in front, minimising hands the keyboard to whatever was in front before; then it is shown
    again without being activated. A minimised window would not draw at all.
    """
    if user32.GetForegroundWindow() == hwnd:
        user32.ShowWindowAsync(hwnd, SW_MINIMIZE)
        time.sleep(0.5)
    if user32.IsIconic(hwnd) or user32.GetForegroundWindow() != hwnd:
        user32.ShowWindowAsync(hwnd, SW_SHOWNOACTIVATE)
        time.sleep(0.3)
    user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
    return user32.GetForegroundWindow() != hwnd


def press(hwnd, key):
    """Press and release a key in the window by message; the window need not be in front."""
    vk, scan = KEYS[key]
    user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 1 | (scan << 16))
    time.sleep(0.06)
    user32.PostMessageW(hwnd, WM_KEYUP, vk, 1 | (scan << 16) | (0xC0 << 24))


def close(hwnd):
    user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)


# ---- the graphics card -------------------------------------------------------------------------------
def free_vram():
    """Free video memory in megabytes (first NVIDIA card), or None when it cannot be told."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total,memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=30,
                             creationflags=subprocess.CREATE_NO_WINDOW).stdout
        total, used = (int(v) for v in out.strip().splitlines()[0].split(","))
        return total - used
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None
