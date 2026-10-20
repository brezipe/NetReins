"""Ikona v oznamovací oblasti (system tray) pomocí pystray.

pystray běží ve vlastním vlákně. Kliknutí v menu proto jen vloží příkaz do
fronty a GUI si ho vyzvedne ve svém vlákně (tkinter není thread-safe).
"""

from __future__ import annotations

import logging
import queue
import threading

import theme
from i18n import t

log = logging.getLogger(__name__)

SHOW = "show"
ABOUT = "about"
CLEAR_ALL = "clear_all"
QUIT = "quit"

try:
    import pystray
    from PIL import Image
except ImportError:  # bez pystray program funguje dál, jen bez ikony v trayi
    pystray = None


class Tray:
    def __init__(self, commands: queue.Queue):
        self.commands = commands
        self._icon = None
        self._thread: threading.Thread | None = None

    @property
    def available(self) -> bool:
        return self._icon is not None

    def start(self) -> None:
        if pystray is None:
            log.warning("pystray není nainstalován – ikona v oznamovací oblasti nebude")
            return
        try:
            image = Image.open(theme.resource_path("icon.png"))
        except OSError:
            image = Image.new("RGBA", (64, 64), theme.ACCENT)

        def cmd(name):
            return lambda _icon, _item: self.commands.put(name)

        def text(key):  # text se vyhodnotí při zobrazení -> sleduje zvolený jazyk
            return lambda _item: t(key)

        menu = pystray.Menu(
            pystray.MenuItem(text("tray_open"), cmd(SHOW), default=True),  # default = levý klik
            pystray.MenuItem(text("tray_about"), cmd(ABOUT)),
            pystray.MenuItem(text("tray_clear_all"), cmd(CLEAR_ALL)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(text("tray_quit"), cmd(QUIT)),
        )
        self._icon = pystray.Icon("NetReins", image, "NetReins", menu)
        self._thread = threading.Thread(target=self._icon.run, name="tray", daemon=True)
        self._thread.start()

    def set_tooltip(self, text: str) -> None:
        if self._icon is not None and self._icon.title != text:
            self._icon.title = text[:127]  # Windows: max. 128 znaků

    def refresh_menu(self) -> None:
        if self._icon is not None:
            try:
                self._icon.update_menu()
            except Exception:
                log.debug("update_menu selhalo", exc_info=True)

    def notify(self, message: str, title: str = "NetReins") -> None:
        if self._icon is not None:
            try:
                self._icon.notify(message, title)
            except Exception:
                log.debug("notifikace selhala", exc_info=True)

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None
        if self._thread is not None:
            self._thread.join(timeout=2)
