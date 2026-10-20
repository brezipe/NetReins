"""Win32 pomůcky: spolehlivé zobrazení okna v popředí a jediná instance aplikace."""

from __future__ import annotations

import ctypes
import logging
import threading
import tkinter as tk
from ctypes import wintypes

log = logging.getLogger(__name__)

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetParent.restype = wintypes.HWND
user32.GetParent.argtypes = [wintypes.HWND]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.IsIconic.argtypes = [wintypes.HWND]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateEventW.restype = wintypes.HANDLE
kernel32.CreateEventW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.OpenEventW.restype = wintypes.HANDLE
kernel32.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.SetEvent.argtypes = [wintypes.HANDLE]
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

SW_RESTORE = 9
ERROR_ALREADY_EXISTS = 183
EVENT_MODIFY_STATE = 0x0002

MUTEX_NAME = "Local\\NetReins.Instance"
SHOW_EVENT_NAME = "Local\\NetReins.Show"


def bring_to_front(root: tk.Tk) -> None:
    """Zobrazí okno a dostane ho do popředí i přes ochranu Windows proti
    „kradení fokusu“ (typicky po potvrzení UAC okno zůstane vzadu)."""
    root.deiconify()
    root.lift()
    try:
        hwnd = user32.GetParent(root.winfo_id())
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        fg = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg, None) if fg else 0
        my_thread = kernel32.GetCurrentThreadId()
        # připojení ke vstupní frontě aktuálního popředí smí SetForegroundWindow
        attached = bool(fg_thread and fg_thread != my_thread
                        and user32.AttachThreadInput(my_thread, fg_thread, True))
        try:
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
        finally:
            if attached:
                user32.AttachThreadInput(my_thread, fg_thread, False)
    except Exception:
        log.debug("bring_to_front: Win32 volání selhalo", exc_info=True)
    # pojistka: krátce „vždy navrchu“, pak zpět
    root.attributes("-topmost", True)
    root.after(300, lambda: root.attributes("-topmost", False))
    root.focus_force()


class SingleInstance:
    """Pojmenovaný mutex hlídá jedinou instanci. Druhé spuštění jen nastaví
    pojmenovanou událost a skončí; první instance na ni čeká a ukáže okno."""

    def __init__(self):
        self._mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        self.already_running = ctypes.get_last_error() == ERROR_ALREADY_EXISTS
        self._event = None
        self._stop = threading.Event()

    def signal_existing(self) -> bool:
        """Požádá běžící instanci o zobrazení okna."""
        ev = kernel32.OpenEventW(EVENT_MODIFY_STATE, False, SHOW_EVENT_NAME)
        if not ev:
            return False
        try:
            return bool(kernel32.SetEvent(ev))
        finally:
            kernel32.CloseHandle(ev)

    def listen(self, on_show) -> None:
        """Ve vlákně čeká na požadavek z dalšího spuštění a volá on_show()
        (z cizího vlákna – on_show musí být thread-safe)."""
        self._event = kernel32.CreateEventW(None, False, False, SHOW_EVENT_NAME)
        if not self._event:
            return

        def run():
            while not self._stop.is_set():
                if kernel32.WaitForSingleObject(self._event, 500) == 0:  # WAIT_OBJECT_0
                    on_show()

        threading.Thread(target=run, name="single-instance", daemon=True).start()

    def close(self) -> None:
        self._stop.set()
        for h in (self._event, self._mutex):
            if h:
                kernel32.CloseHandle(h)
        self._event = self._mutex = None
