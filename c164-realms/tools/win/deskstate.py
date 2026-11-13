#!/usr/bin/env python3
"""Windows only: can the picture client's window be photographed right now?

    python bin/job.py <part> -- ../tools/win/deskstate.py

Pictures are taken from the game's window through the desktop compositor (winctl.grab). This
prints what the desktop is doing and changes nothing: whether the console display is on, how long
ago somebody last touched the keyboard or the mouse, whether the desktop is locked, whether the
compositor is running. Exit code 0: the display is on and the desktop is the ordinary one;
2: it is not (a grab would come back black); 3: could not tell.
"""
import ctypes
import os
import sys
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WM_POWERBROADCAST, PBT_POWERSETTINGCHANGE = 0x0218, 0x8013
HWND_MESSAGE = wintypes.HWND(-3)
PM_REMOVE = 1
SM_REMOTESESSION = 0x1000
DESKTOP_READOBJECTS, UOI_NAME = 0x0001, 2
DISPLAY = {0: "off", 1: "on", 2: "dimmed"}
LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class GUID(ctypes.Structure):
    _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]


# GUID_CONSOLE_DISPLAY_STATE {6FE69556-704A-47A0-8F24-C28D936FDA47}
CONSOLE_DISPLAY_STATE = GUID(0x6FE69556, 0x704A, 0x47A0,
                             (ctypes.c_ubyte * 8)(0x8F, 0x24, 0xC2, 0x8D, 0x93, 0x6F, 0xDA, 0x47))


class POWERBROADCAST_SETTING(ctypes.Structure):
    _fields_ = [("setting", GUID), ("length", wintypes.DWORD), ("data", wintypes.DWORD)]


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]


class RATIO(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("n", ctypes.c_uint32), ("d", ctypes.c_uint32)]


class DWM_TIMING_INFO(ctypes.Structure):
    """dwmapi.h, packed to one byte. Only the two counters near the top are read."""
    _pack_ = 1
    _fields_ = ([("cbSize", ctypes.c_uint32), ("rateRefresh", RATIO), ("qpcRefreshPeriod", ctypes.c_uint64),
                 ("rateCompose", RATIO), ("qpcVBlank", ctypes.c_uint64), ("cRefresh", ctypes.c_uint64),
                 ("cDXRefresh", ctypes.c_uint32), ("qpcCompose", ctypes.c_uint64), ("cFrame", ctypes.c_uint64)]
                + [("rest", ctypes.c_ubyte * 228)])


user32.DefWindowProcW.restype = LRESULT
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.RegisterClassW.restype = wintypes.ATOM
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
user32.CreateWindowExW.restype = wintypes.HWND
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND,
                                   wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.RegisterPowerSettingNotification.restype = wintypes.HANDLE
user32.RegisterPowerSettingNotification.argtypes = [wintypes.HANDLE, ctypes.POINTER(GUID), wintypes.DWORD]
user32.UnregisterPowerSettingNotification.argtypes = [wintypes.HANDLE]
user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT,
                                wintypes.UINT]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.GetLastInputInfo.argtypes = [ctypes.POINTER(LASTINPUTINFO)]
user32.OpenInputDesktop.restype = wintypes.HANDLE
user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
user32.GetUserObjectInformationW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
                                             ctypes.POINTER(wintypes.DWORD)]
user32.CloseDesktop.argtypes = [wintypes.HANDLE]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetTickCount.restype = wintypes.DWORD


def display_state(wait=3.0):
    """0 off, 1 on, 2 dimmed; None when the system did not say. Asked through a window that is
    never shown (message-only): the system answers a registration with the present state."""
    seen = []

    def proc(hwnd, msg, wparam, lparam):
        if msg == WM_POWERBROADCAST and wparam == PBT_POWERSETTINGCHANGE and lparam:
            setting = ctypes.cast(ctypes.c_void_p(lparam), ctypes.POINTER(POWERBROADCAST_SETTING)).contents
            if bytes(setting.setting) == bytes(CONSOLE_DISPLAY_STATE) and setting.length >= 4:
                seen.append(setting.data)
            return 1
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    keep = WNDPROC(proc)
    instance = kernel32.GetModuleHandleW(None)
    name = f"c164-deskstate-{os.getpid()}"
    cls = WNDCLASSW()
    cls.lpfnWndProc, cls.hInstance, cls.lpszClassName = keep, instance, name
    if not user32.RegisterClassW(ctypes.byref(cls)):
        return None
    hwnd = user32.CreateWindowExW(0, name, name, 0, 0, 0, 0, 0, HWND_MESSAGE, None, instance, None)
    try:
        if not hwnd:
            return None
        handle = user32.RegisterPowerSettingNotification(hwnd, ctypes.byref(CONSOLE_DISPLAY_STATE), 0)
        if not handle:
            return None
        msg = wintypes.MSG()
        end = time.monotonic() + wait
        while not seen and time.monotonic() < end:
            while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                user32.DispatchMessageW(ctypes.byref(msg))
            time.sleep(0.02)
        user32.UnregisterPowerSettingNotification(handle)
        return seen[-1] if seen else None
    finally:
        if hwnd:
            user32.DestroyWindow(hwnd)
        user32.UnregisterClassW(name, instance)


def idle_seconds():
    """Seconds since the keyboard or the mouse was last touched; None when it cannot be told."""
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if not user32.GetLastInputInfo(ctypes.byref(info)):
        return None
    return ((kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0


def input_desktop():
    """Name of the desktop that has the keyboard: "Default" in ordinary use; None when it may not
    be opened, which is the case while the machine is locked."""
    handle = user32.OpenInputDesktop(0, False, DESKTOP_READOBJECTS)
    if not handle:
        return None
    try:
        name = ctypes.create_unicode_buffer(256)
        needed = wintypes.DWORD()
        if not user32.GetUserObjectInformationW(handle, UOI_NAME, name, ctypes.sizeof(name), ctypes.byref(needed)):
            return None
        return name.value
    finally:
        user32.CloseDesktop(handle)


def compositor(span=0.5):
    """(screen refreshes, frames composed) counted by the compositor over `span` seconds, or None."""
    try:
        dwm = ctypes.WinDLL("dwmapi")
    except OSError:
        return None
    dwm.DwmGetCompositionTimingInfo.argtypes = [wintypes.HWND, ctypes.POINTER(DWM_TIMING_INFO)]
    dwm.DwmGetCompositionTimingInfo.restype = ctypes.c_long

    def read():
        info = DWM_TIMING_INFO()
        info.cbSize = ctypes.sizeof(info)
        return (info.cRefresh, info.cFrame) if dwm.DwmGetCompositionTimingInfo(None, ctypes.byref(info)) == 0 else None

    first = read()
    time.sleep(span)
    second = read()
    if first is None or second is None:
        return None
    return second[0] - first[0], second[1] - first[1]


def report():
    """Everything in one dictionary; "ok" says whether a grab can be expected to show the game."""
    state = display_state()
    desk = input_desktop()
    remote = bool(user32.GetSystemMetrics(SM_REMOTESESSION))
    if state is None:
        ok = None
    else:
        ok = state in (1, 2) and desk == "Default" and not remote
    return {"display": DISPLAY.get(state, "unknown"), "idle_seconds": idle_seconds(), "input_desktop": desk,
            "remote_session": remote, "compositor": compositor(), "ok": ok}


def main():
    got = report()
    idle = got["idle_seconds"]
    print(f"console display: {got['display']}")
    print("last keyboard or mouse input: " + (f"{idle:.0f} s ago" if idle is not None else "cannot tell"))
    print("desktop with the keyboard: " + (got["input_desktop"] or "not ours to open (locked?)"))
    print(f"remote session: {'yes' if got['remote_session'] else 'no'}")
    comp = got["compositor"]
    print("compositor over 0.5 s: " + (f"{comp[0]} refreshes, {comp[1]} frames" if comp else "cannot tell"))
    if got["ok"] is None:
        print("-> cannot tell whether the window can be photographed")
        sys.exit(3)
    print("-> the window can be photographed" if got["ok"] else
          "-> the window cannot be photographed now (a grab would come back black)")
    sys.exit(0 if got["ok"] else 2)


if __name__ == "__main__":
    main()
